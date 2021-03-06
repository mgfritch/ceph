// -*- mode:C++; tab-width:8; c-basic-offset:2; indent-tabs-mode:t -*-
// vim: ts=8 sw=2 smarttab
/*
 * Ceph - scalable distributed file system
 *
 * Copyright (C) 2016 Red Hat Inc.
 *
 * This is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License version 2.1, as published by the Free Software
 * Foundation.  See file COPYING.
 *
 */


#include <memory>
#include <functional>

#include "osd/scheduler/mClockScheduler.h"
#include "common/dout.h"

namespace dmc = crimson::dmclock;
using namespace std::placeholders;

#define dout_context cct
#define dout_subsys ceph_subsys_osd
#undef dout_prefix
#define dout_prefix *_dout << "mClockScheduler: "


namespace ceph::osd::scheduler {

mClockScheduler::mClockScheduler(CephContext *cct,
  uint32_t num_shards,
  bool is_rotational)
  : cct(cct),
    num_shards(num_shards),
    is_rotational(is_rotational),
    scheduler(
      std::bind(&mClockScheduler::ClientRegistry::get_info,
                &client_registry,
                _1),
      dmc::AtLimit::Wait,
      cct->_conf.get_val<double>("osd_mclock_scheduler_anticipation_timeout"))
{
  cct->_conf.add_observer(this);
  ceph_assert(num_shards > 0);
  set_max_osd_capacity();
  set_osd_mclock_cost_per_io();
  set_mclock_profile();
  enable_mclock_profile_settings();
  client_registry.update_from_config(cct->_conf);
}

void mClockScheduler::ClientRegistry::update_from_config(const ConfigProxy &conf)
{
  default_external_client_info.update(
    conf.get_val<uint64_t>("osd_mclock_scheduler_client_res"),
    conf.get_val<uint64_t>("osd_mclock_scheduler_client_wgt"),
    conf.get_val<uint64_t>("osd_mclock_scheduler_client_lim"));

  internal_client_infos[
    static_cast<size_t>(op_scheduler_class::background_recovery)].update(
    conf.get_val<uint64_t>("osd_mclock_scheduler_background_recovery_res"),
    conf.get_val<uint64_t>("osd_mclock_scheduler_background_recovery_wgt"),
    conf.get_val<uint64_t>("osd_mclock_scheduler_background_recovery_lim"));

  internal_client_infos[
    static_cast<size_t>(op_scheduler_class::background_best_effort)].update(
    conf.get_val<uint64_t>("osd_mclock_scheduler_background_best_effort_res"),
    conf.get_val<uint64_t>("osd_mclock_scheduler_background_best_effort_wgt"),
    conf.get_val<uint64_t>("osd_mclock_scheduler_background_best_effort_lim"));
}

const dmc::ClientInfo *mClockScheduler::ClientRegistry::get_external_client(
  const client_profile_id_t &client) const
{
  auto ret = external_client_infos.find(client);
  if (ret == external_client_infos.end())
    return &default_external_client_info;
  else
    return &(ret->second);
}

const dmc::ClientInfo *mClockScheduler::ClientRegistry::get_info(
  const scheduler_id_t &id) const {
  switch (id.class_id) {
  case op_scheduler_class::immediate:
    ceph_assert(0 == "Cannot schedule immediate");
    return (dmc::ClientInfo*)nullptr;
  case op_scheduler_class::client:
    return get_external_client(id.client_profile_id);
  default:
    ceph_assert(static_cast<size_t>(id.class_id) < internal_client_infos.size());
    return &internal_client_infos[static_cast<size_t>(id.class_id)];
  }
}

void mClockScheduler::set_max_osd_capacity()
{
  if (cct->_conf.get_val<double>("osd_mclock_max_capacity_iops")) {
    max_osd_capacity =
      cct->_conf.get_val<double>("osd_mclock_max_capacity_iops");
  } else {
    if (is_rotational) {
      max_osd_capacity =
        cct->_conf.get_val<double>("osd_mclock_max_capacity_iops_hdd");
    } else {
      max_osd_capacity =
        cct->_conf.get_val<double>("osd_mclock_max_capacity_iops_ssd");
    }
  }
  // Set max osd bandwidth across all shards (at 4KiB blocksize)
  max_osd_bandwidth = max_osd_capacity * 4 * 1024;
  // Set per op-shard iops limit
  max_osd_capacity /= num_shards;
}

void mClockScheduler::set_osd_mclock_cost_per_io()
{
  if (cct->_conf.get_val<uint64_t>("osd_mclock_cost_per_io_msec")) {
    osd_mclock_cost_per_io_msec =
      cct->_conf.get_val<uint64_t>("osd_mclock_cost_per_io_msec");
  } else {
    if (is_rotational) {
      osd_mclock_cost_per_io_msec =
        cct->_conf.get_val<uint64_t>("osd_mclock_cost_per_io_msec_hdd");
    } else {
      osd_mclock_cost_per_io_msec =
        cct->_conf.get_val<uint64_t>("osd_mclock_cost_per_io_msec_ssd");
    }
  }
}

void mClockScheduler::set_mclock_profile()
{
  mclock_profile = cct->_conf.get_val<std::string>("osd_mclock_profile");
}

std::string mClockScheduler::get_mclock_profile()
{
  return mclock_profile;
}

void mClockScheduler::set_balanced_profile_allocations()
{
  // Client Allocation:
  //   reservation: 40% | weight: 1 | limit: 100% |
  // Background Recovery Allocation:
  //   reservation: 40% | weight: 1 | limit: 150% |
  // Background Best Effort Allocation:
  //   reservation: 20% | weight: 2 | limit: max |

  // Client
  uint64_t client_res = static_cast<uint64_t>(
    std::round(0.40 * max_osd_capacity));
  uint64_t client_lim = static_cast<uint64_t>(
    std::round(max_osd_capacity));
  uint64_t client_wgt = default_min;

  // Background Recovery
  uint64_t rec_res = static_cast<uint64_t>(
    std::round(0.40 * max_osd_capacity));
  uint64_t rec_lim = static_cast<uint64_t>(
    std::round(1.5 * max_osd_capacity));
  uint64_t rec_wgt = default_min;

  // Background Best Effort
  uint64_t best_effort_res = static_cast<uint64_t>(
    std::round(0.20 * max_osd_capacity));
  uint64_t best_effort_lim = default_max;
  uint64_t best_effort_wgt = 2;

  // Set the allocations for the mclock clients
  client_allocs[
    static_cast<size_t>(op_scheduler_class::client)].update(
      client_res,
      client_wgt,
      client_lim);
  client_allocs[
    static_cast<size_t>(op_scheduler_class::background_recovery)].update(
      rec_res,
      rec_wgt,
      rec_lim);
  client_allocs[
    static_cast<size_t>(op_scheduler_class::background_best_effort)].update(
      best_effort_res,
      best_effort_wgt,
      best_effort_lim);
}

void mClockScheduler::set_high_recovery_ops_profile_allocations()
{
  // Client Allocation:
  //   reservation: 30% | weight: 1 | limit: 80% |
  // Background Recovery Allocation:
  //   reservation: 60% | weight: 2 | limit: 200% |
  // Background Best Effort Allocation:
  //   reservation: 1 | weight: 2 | limit: max |

  // Client
  uint64_t client_res = static_cast<uint64_t>(
    std::round(0.30 * max_osd_capacity));
  uint64_t client_lim = static_cast<uint64_t>(
    std::round(0.80 * max_osd_capacity));
  uint64_t client_wgt = default_min;

  // Background Recovery
  uint64_t rec_res = static_cast<uint64_t>(
    std::round(0.60 * max_osd_capacity));
  uint64_t rec_lim = static_cast<uint64_t>(
    std::round(2.0 * max_osd_capacity));
  uint64_t rec_wgt = 2;

  // Background Best Effort
  uint64_t best_effort_res = default_min;
  uint64_t best_effort_lim = default_max;
  uint64_t best_effort_wgt = 2;

  // Set the allocations for the mclock clients
  client_allocs[
    static_cast<size_t>(op_scheduler_class::client)].update(
      client_res,
      client_wgt,
      client_lim);
  client_allocs[
    static_cast<size_t>(op_scheduler_class::background_recovery)].update(
      rec_res,
      rec_wgt,
      rec_lim);
  client_allocs[
    static_cast<size_t>(op_scheduler_class::background_best_effort)].update(
      best_effort_res,
      best_effort_wgt,
      best_effort_lim);
}

void mClockScheduler::set_high_client_ops_profile_allocations()
{
  // Client Allocation:
  //   reservation: 50% | weight: 2 | limit: max |
  // Background Recovery Allocation:
  //   reservation: 25% | weight: 1 | limit: 100% |
  // Background Best Effort Allocation:
  //   reservation: 25% | weight: 2 | limit: max |

  // Client
  uint64_t client_res = static_cast<uint64_t>(
    std::round(0.50 * max_osd_capacity));
  uint64_t client_wgt = 2;
  uint64_t client_lim = default_max;

  // Background Recovery
  uint64_t rec_res = static_cast<uint64_t>(
    std::round(0.25 * max_osd_capacity));
  uint64_t rec_lim = static_cast<uint64_t>(
    std::round(max_osd_capacity));
  uint64_t rec_wgt = default_min;

  // Background Best Effort
  uint64_t best_effort_res = static_cast<uint64_t>(
    std::round(0.25 * max_osd_capacity));
  uint64_t best_effort_lim = default_max;
  uint64_t best_effort_wgt = 2;

  // Set the allocations for the mclock clients
  client_allocs[
    static_cast<size_t>(op_scheduler_class::client)].update(
      client_res,
      client_wgt,
      client_lim);
  client_allocs[
    static_cast<size_t>(op_scheduler_class::background_recovery)].update(
      rec_res,
      rec_wgt,
      rec_lim);
  client_allocs[
    static_cast<size_t>(op_scheduler_class::background_best_effort)].update(
      best_effort_res,
      best_effort_wgt,
      best_effort_lim);
}

void mClockScheduler::enable_mclock_profile_settings()
{
  // Nothing to do for "custom" profile
  if (mclock_profile == "custom") {
    return;
  }

  // Set mclock and ceph config options for the chosen profile
  if (mclock_profile == "balanced") {
    set_balanced_profile_allocations();
  } else if (mclock_profile == "high_recovery_ops") {
    set_high_recovery_ops_profile_allocations();
  } else if (mclock_profile == "high_client_ops") {
    set_high_client_ops_profile_allocations();
  } else {
    ceph_assert("Invalid choice of mclock profile" == 0);
    return;
  }

  // Set the mclock config parameters
  set_profile_config();
  // Set recovery specific Ceph options
  set_global_recovery_options();
}

void mClockScheduler::set_profile_config()
{
  ClientAllocs client = client_allocs[
    static_cast<size_t>(op_scheduler_class::client)];
  ClientAllocs rec = client_allocs[
    static_cast<size_t>(op_scheduler_class::background_recovery)];
  ClientAllocs best_effort = client_allocs[
    static_cast<size_t>(op_scheduler_class::background_best_effort)];

  // Set external client params
  cct->_conf.set_val("osd_mclock_scheduler_client_res",
    std::to_string(client.res));
  cct->_conf.set_val("osd_mclock_scheduler_client_wgt",
    std::to_string(client.wgt));
  cct->_conf.set_val("osd_mclock_scheduler_client_lim",
    std::to_string(client.lim));

  // Set background recovery client params
  cct->_conf.set_val("osd_mclock_scheduler_background_recovery_res",
    std::to_string(rec.res));
  cct->_conf.set_val("osd_mclock_scheduler_background_recovery_wgt",
    std::to_string(rec.wgt));
  cct->_conf.set_val("osd_mclock_scheduler_background_recovery_lim",
    std::to_string(rec.lim));

  // Set background best effort client params
  cct->_conf.set_val("osd_mclock_scheduler_background_best_effort_res",
    std::to_string(best_effort.res));
  cct->_conf.set_val("osd_mclock_scheduler_background_best_effort_wgt",
    std::to_string(best_effort.wgt));
  cct->_conf.set_val("osd_mclock_scheduler_background_best_effort_lim",
    std::to_string(best_effort.lim));
}

void mClockScheduler::set_global_recovery_options()
{
  // Set high value for recovery max active and max backfill
  int rec_max_active = 1000;
  int max_backfills = 1000;
  cct->_conf.set_val("osd_recovery_max_active", std::to_string(rec_max_active));
  cct->_conf.set_val("osd_max_backfills", std::to_string(max_backfills));

  // Disable recovery sleep
  cct->_conf.set_val("osd_recovery_sleep", std::to_string(0));
  cct->_conf.set_val("osd_recovery_sleep_hdd", std::to_string(0));
  cct->_conf.set_val("osd_recovery_sleep_ssd", std::to_string(0));
  cct->_conf.set_val("osd_recovery_sleep_hybrid", std::to_string(0));

  // Apply the changes
  cct->_conf.apply_changes(nullptr);
}

int mClockScheduler::calc_scaled_cost(int cost)
{
  // Calculate scaled cost in msecs based on item cost
  int scaled_cost = std::floor((cost / max_osd_bandwidth) * 1000);

  // Scale the cost down by an additional cost factor if specified
  // to account for different device characteristics (hdd, ssd).
  // This option can be used to further tune the performance further
  // if necessary (disabled by default).
  if (osd_mclock_cost_per_io_msec > 0) {
    scaled_cost *= osd_mclock_cost_per_io_msec / 1000.0;
  }

  return std::max(scaled_cost, 1);
}

void mClockScheduler::dump(ceph::Formatter &f) const
{
}

void mClockScheduler::enqueue(OpSchedulerItem&& item)
{
  auto id = get_scheduler_id(item);

  // TODO: move this check into OpSchedulerItem, handle backwards compat
  if (op_scheduler_class::immediate == id.class_id) {
    immediate.push_front(std::move(item));
  } else {
    int cost = calc_scaled_cost(item.get_cost());
    // Add item to scheduler queue
    scheduler.add_request(
      std::move(item),
      id,
      cost);
  }
}

void mClockScheduler::enqueue_front(OpSchedulerItem&& item)
{
  immediate.push_back(std::move(item));
  // TODO: item may not be immediate, update mclock machinery to permit
  // putting the item back in the queue
}

WorkItem mClockScheduler::dequeue()
{
  if (!immediate.empty()) {
    WorkItem work_item{std::move(immediate.back())};
    immediate.pop_back();
    return work_item;
  } else {
    mclock_queue_t::PullReq result = scheduler.pull_request();
    if (result.is_future()) {
      return result.getTime();
    } else if (result.is_none()) {
      ceph_assert(
	0 == "Impossible, must have checked empty() first");
      return {};
    } else {
      ceph_assert(result.is_retn());

      auto &retn = result.get_retn();
      return std::move(*retn.request);
    }
  }
}

const char** mClockScheduler::get_tracked_conf_keys() const
{
  static const char* KEYS[] = {
    "osd_mclock_scheduler_client_res",
    "osd_mclock_scheduler_client_wgt",
    "osd_mclock_scheduler_client_lim",
    "osd_mclock_scheduler_background_recovery_res",
    "osd_mclock_scheduler_background_recovery_wgt",
    "osd_mclock_scheduler_background_recovery_lim",
    "osd_mclock_scheduler_background_best_effort_res",
    "osd_mclock_scheduler_background_best_effort_wgt",
    "osd_mclock_scheduler_background_best_effort_lim",
    "osd_mclock_cost_per_io_msec",
    "osd_mclock_cost_per_io_msec_hdd",
    "osd_mclock_cost_per_io_msec_ssd",
    "osd_mclock_max_capacity_iops",
    "osd_mclock_max_capacity_iops_hdd",
    "osd_mclock_max_capacity_iops_ssd",
    "osd_mclock_profile",
    NULL
  };
  return KEYS;
}

void mClockScheduler::handle_conf_change(
  const ConfigProxy& conf,
  const std::set<std::string> &changed)
{
  if (changed.count("osd_mclock_cost_per_io_msec") ||
      changed.count("osd_mclock_cost_per_io_msec_hdd") ||
      changed.count("osd_mclock_cost_per_io_msec_ssd")) {
    set_osd_mclock_cost_per_io();
  }
  if (changed.count("osd_mclock_max_capacity_iops") ||
      changed.count("osd_mclock_max_capacity_iops_hdd") ||
      changed.count("osd_mclock_max_capacity_iops_ssd")) {
    set_max_osd_capacity();
    if (mclock_profile != "custom") {
      enable_mclock_profile_settings();
      client_registry.update_from_config(conf);
    }
  }
  if (changed.count("osd_mclock_profile")) {
    set_mclock_profile();
    if (mclock_profile != "custom") {
      enable_mclock_profile_settings();
      client_registry.update_from_config(conf);
    }
  }
  if (changed.count("osd_mclock_scheduler_client_res") ||
      changed.count("osd_mclock_scheduler_client_wgt") ||
      changed.count("osd_mclock_scheduler_client_lim") ||
      changed.count("osd_mclock_scheduler_background_recovery_res") ||
      changed.count("osd_mclock_scheduler_background_recovery_wgt") ||
      changed.count("osd_mclock_scheduler_background_recovery_lim")) {
    if (mclock_profile == "custom") {
      client_registry.update_from_config(conf);
    }
  }
}

mClockScheduler::~mClockScheduler()
{
  cct->_conf.remove_observer(this);
}

}
