# Disable autopep8 for this file:

# fmt: off

import json

import pytest

import yaml

from ceph.deployment.service_spec import ServiceSpec, NFSServiceSpec, RGWSpec, \
    IscsiServiceSpec, AlertManagerSpec, HostPlacementSpec, CustomContainerSpec, \
    HA_RGWSpec

from orchestrator import DaemonDescription, OrchestratorError


@pytest.mark.parametrize(
    "spec_json",
    json.loads("""[
{
  "placement": {
    "count": 1
  },
  "service_type": "alertmanager"
},
{
  "placement": {
    "host_pattern": "*"
  },
  "service_type": "crash"
},
{
  "placement": {
    "count": 1
  },
  "service_type": "grafana"
},
{
  "placement": {
    "count": 2
  },
  "service_type": "mgr"
},
{
  "placement": {
    "count": 5
  },
  "service_type": "mon"
},
{
  "placement": {
    "host_pattern": "*"
  },
  "service_type": "node-exporter"
},
{
  "placement": {
    "count": 1
  },
  "service_type": "prometheus"
},
{
  "placement": {
    "hosts": [
      {
        "hostname": "ceph-001",
        "network": "",
        "name": ""
      }
    ]
  },
  "service_type": "rgw",
  "service_id": "default-rgw-realm.eu-central-1.1",
  "rgw_realm": "default-rgw-realm",
  "rgw_zone": "eu-central-1",
  "subcluster": "1"
},
{
  "service_type": "osd",
  "service_id": "osd_spec_default",
  "placement": {
    "host_pattern": "*"
  },
  "data_devices": {
    "model": "MC-55-44-XZ"
  },
  "db_devices": {
    "model": "SSD-123-foo"
  },
  "wal_devices": {
    "model": "NVME-QQQQ-987"
  }
}
]
""")
)
def test_spec_octopus(spec_json):
    # https://tracker.ceph.com/issues/44934
    # Those are real user data from early octopus.
    # Please do not modify those JSON values.

    spec = ServiceSpec.from_json(spec_json)
    # just some verification that we can sill read old octopus specs
    def convert_to_old_style_json(j):
        j_c = dict(j.copy())
        j_c.pop('service_name', None)
        if 'spec' in j_c:
            spec = j_c.pop('spec')
            j_c.update(spec)
        if 'placement' in j_c:
            if 'hosts' in j_c['placement']:
                j_c['placement']['hosts'] = [
                    {
                        'hostname': HostPlacementSpec.parse(h).hostname,
                        'network': HostPlacementSpec.parse(h).network,
                        'name': HostPlacementSpec.parse(h).name
                    }
                    for h in j_c['placement']['hosts']
                ]
        j_c.pop('objectstore', None)
        j_c.pop('filter_logic', None)
        return j_c
    assert spec_json == convert_to_old_style_json(spec.to_json())


@pytest.mark.parametrize(
    "dd_json",
    json.loads("""[
    {
        "hostname": "ceph-001",
        "container_id": "d94d7969094d",
        "container_image_id": "0881eb8f169f5556a292b4e2c01d683172b12830a62a9225a98a8e206bb734f0",
        "container_image_name": "docker.io/prom/alertmanager:latest",
        "daemon_id": "ceph-001",
        "daemon_type": "alertmanager",
        "version": "0.20.0",
        "status": 1,
        "status_desc": "running",
        "last_refresh": "2020-04-03T15:31:48.725856",
        "created": "2020-04-02T19:23:08.829543",
        "started": "2020-04-03T07:29:16.932838",
        "is_active": false
    },
    {
        "hostname": "ceph-001",
        "container_id": "c4b036202241",
        "container_image_id": "204a01f9b0b6710dd0c0af7f37ce7139c47ff0f0105d778d7104c69282dfbbf1",
        "container_image_name": "docker.io/ceph/ceph:v15",
        "daemon_id": "ceph-001",
        "daemon_type": "crash",
        "version": "15.2.0",
        "status": 1,
        "status_desc": "running",
        "last_refresh": "2020-04-03T15:31:48.725903",
        "created": "2020-04-02T19:23:11.390694",
        "started": "2020-04-03T07:29:16.910897",
        "is_active": false
    },
    {
        "hostname": "ceph-001",
        "container_id": "5b7b94b48f31",
        "container_image_id": "87a51ecf0b1c9a7b187b21c1b071425dafea0d765a96d5bc371c791169b3d7f4",
        "container_image_name": "docker.io/ceph/ceph-grafana:latest",
        "daemon_id": "ceph-001",
        "daemon_type": "grafana",
        "version": "6.6.2",
        "status": 1,
        "status_desc": "running",
        "last_refresh": "2020-04-03T15:31:48.725950",
        "created": "2020-04-02T19:23:52.025088",
        "started": "2020-04-03T07:29:16.847972",
        "is_active": false
    },
    {
        "hostname": "ceph-001",
        "container_id": "9ca007280456",
        "container_image_id": "204a01f9b0b6710dd0c0af7f37ce7139c47ff0f0105d778d7104c69282dfbbf1",
        "container_image_name": "docker.io/ceph/ceph:v15",
        "daemon_id": "ceph-001.gkjwqp",
        "daemon_type": "mgr",
        "version": "15.2.0",
        "status": 1,
        "status_desc": "running",
        "last_refresh": "2020-04-03T15:31:48.725807",
        "created": "2020-04-02T19:22:18.648584",
        "started": "2020-04-03T07:29:16.856153",
        "is_active": false
    },
    {
        "hostname": "ceph-001",
        "container_id": "3d1ba9a2b697",
        "container_image_id": "204a01f9b0b6710dd0c0af7f37ce7139c47ff0f0105d778d7104c69282dfbbf1",
        "container_image_name": "docker.io/ceph/ceph:v15",
        "daemon_id": "ceph-001",
        "daemon_type": "mon",
        "version": "15.2.0",
        "status": 1,
        "status_desc": "running",
        "last_refresh": "2020-04-03T15:31:48.725715",
        "created": "2020-04-02T19:22:13.863300",
        "started": "2020-04-03T07:29:17.206024",
        "is_active": false
    },
    {
        "hostname": "ceph-001",
        "container_id": "36d026c68ba1",
        "container_image_id": "e5a616e4b9cf68dfcad7782b78e118be4310022e874d52da85c55923fb615f87",
        "container_image_name": "docker.io/prom/node-exporter:latest",
        "daemon_id": "ceph-001",
        "daemon_type": "node-exporter",
        "version": "0.18.1",
        "status": 1,
        "status_desc": "running",
        "last_refresh": "2020-04-03T15:31:48.725996",
        "created": "2020-04-02T19:23:53.880197",
        "started": "2020-04-03T07:29:16.880044",
        "is_active": false
    },
    {
        "hostname": "ceph-001",
        "container_id": "faf76193cbfe",
        "container_image_id": "204a01f9b0b6710dd0c0af7f37ce7139c47ff0f0105d778d7104c69282dfbbf1",
        "container_image_name": "docker.io/ceph/ceph:v15",
        "daemon_id": "0",
        "daemon_type": "osd",
        "version": "15.2.0",
        "status": 1,
        "status_desc": "running",
        "last_refresh": "2020-04-03T15:31:48.726088",
        "created": "2020-04-02T20:35:02.991435",
        "started": "2020-04-03T07:29:19.373956",
        "is_active": false
    },
    {
        "hostname": "ceph-001",
        "container_id": "f82505bae0f1",
        "container_image_id": "204a01f9b0b6710dd0c0af7f37ce7139c47ff0f0105d778d7104c69282dfbbf1",
        "container_image_name": "docker.io/ceph/ceph:v15",
        "daemon_id": "1",
        "daemon_type": "osd",
        "version": "15.2.0",
        "status": 1,
        "status_desc": "running",
        "last_refresh": "2020-04-03T15:31:48.726134",
        "created": "2020-04-02T20:35:17.142272",
        "started": "2020-04-03T07:29:19.374002",
        "is_active": false
    },
    {
        "hostname": "ceph-001",
        "container_id": "2708d84cd484",
        "container_image_id": "358a0d2395fe711bb8258e8fb4b2d7865c0a9a6463969bcd1452ee8869ea6653",
        "container_image_name": "docker.io/prom/prometheus:latest",
        "daemon_id": "ceph-001",
        "daemon_type": "prometheus",
        "version": "2.17.1",
        "status": 1,
        "status_desc": "running",
        "last_refresh": "2020-04-03T15:31:48.726042",
        "created": "2020-04-02T19:24:10.281163",
        "started": "2020-04-03T07:29:16.926292",
        "is_active": false
    },
    {
        "hostname": "ceph-001",
        "daemon_id": "default-rgw-realm.eu-central-1.1.ceph-001.ytywjo",
        "daemon_type": "rgw",
        "status": 1,
        "status_desc": "starting",
        "is_active": false
    }
]""")
)
def test_dd_octopus(dd_json):
    # https://tracker.ceph.com/issues/44934
    # Those are real user data from early octopus.
    # Please do not modify those JSON values.

    # Convert datetime properties to old style.
    # 2020-04-03T07:29:16.926292Z -> 2020-04-03T07:29:16.926292
    def convert_to_old_style_json(j):
        for k in ['last_refresh', 'created', 'started', 'last_deployed',
                  'last_configured']:
            if k in j:
                j[k] = j[k].rstrip('Z')
        return j

    assert dd_json == convert_to_old_style_json(
        DaemonDescription.from_json(dd_json).to_json())


@pytest.mark.parametrize("spec,dd,valid",
[   # noqa: E128
    # https://tracker.ceph.com/issues/44934
    (
        RGWSpec(
            rgw_realm="default-rgw-realm",
            rgw_zone="eu-central-1",
            subcluster='1',
        ),
        DaemonDescription(
            daemon_type='rgw',
            daemon_id="default-rgw-realm.eu-central-1.1.ceph-001.ytywjo",
            hostname="ceph-001",
        ),
        True
    ),
    (
        # no subcluster
        RGWSpec(
            rgw_realm="default-rgw-realm",
            rgw_zone="eu-central-1",
        ),
        DaemonDescription(
            daemon_type='rgw',
            daemon_id="default-rgw-realm.eu-central-1.ceph-001.ytywjo",
            hostname="ceph-001",
        ),
        True
    ),
    (
        # with tld
        RGWSpec(
            rgw_realm="default-rgw-realm",
            rgw_zone="eu-central-1",
            subcluster='1',
        ),
        DaemonDescription(
            daemon_type='rgw',
            daemon_id="default-rgw-realm.eu-central-1.1.host.domain.tld.ytywjo",
            hostname="host.domain.tld",
        ),
        True
    ),
    (
        # explicit naming
        RGWSpec(
            rgw_realm="realm",
            rgw_zone="zone",
        ),
        DaemonDescription(
            daemon_type='rgw',
            daemon_id="realm.zone.a",
            hostname="smithi028",
        ),
        True
    ),
    (
        # without host
        RGWSpec(
            service_type='rgw',
            rgw_realm="default-rgw-realm",
            rgw_zone="eu-central-1",
            subcluster='1',
        ),
        DaemonDescription(
            daemon_type='rgw',
            daemon_id="default-rgw-realm.eu-central-1.1.hostname.ytywjo",
            hostname=None,
        ),
        False
    ),
    (
        # zone contains hostname
        # https://tracker.ceph.com/issues/45294
        RGWSpec(
            rgw_realm="default.rgw.realm",
            rgw_zone="ceph.001",
            subcluster='1',
        ),
        DaemonDescription(
            daemon_type='rgw',
            daemon_id="default.rgw.realm.ceph.001.1.ceph.001.ytywjo",
            hostname="ceph.001",
        ),
        True
    ),

    # https://tracker.ceph.com/issues/45293
    (
        ServiceSpec(
            service_type='mds',
            service_id="a",
        ),
        DaemonDescription(
            daemon_type='mds',
            daemon_id="a.host1.abc123",
            hostname="host1",
        ),
        True
    ),
    (
        # '.' char in service_id
        ServiceSpec(
            service_type='mds',
            service_id="a.b.c",
        ),
        DaemonDescription(
            daemon_type='mds',
            daemon_id="a.b.c.host1.abc123",
            hostname="host1",
        ),
        True
    ),

    # https://tracker.ceph.com/issues/45617
    (
        # daemon_id does not contain hostname
        ServiceSpec(
            service_type='mds',
            service_id="a",
        ),
        DaemonDescription(
            daemon_type='mds',
            daemon_id="a",
            hostname="host1",
        ),
        True
    ),
    (
        # daemon_id only contains hostname
        ServiceSpec(
            service_type='mds',
            service_id="host1",
        ),
        DaemonDescription(
            daemon_type='mds',
            daemon_id="host1",
            hostname="host1",
        ),
        True
    ),

    # https://tracker.ceph.com/issues/45399
    (
        # daemon_id only contains hostname
        ServiceSpec(
            service_type='mds',
            service_id="a",
        ),
        DaemonDescription(
            daemon_type='mds',
            daemon_id="a.host1.abc123",
            hostname="host1.site",
        ),
        True
    ),
    (
        NFSServiceSpec(
            service_id="a",
        ),
        DaemonDescription(
            daemon_type='nfs',
            daemon_id="a.host1",
            hostname="host1.site",
        ),
        True
    ),

    # https://tracker.ceph.com/issues/45293
    (
        NFSServiceSpec(
            service_id="a",
        ),
        DaemonDescription(
            daemon_type='nfs',
            daemon_id="a.host1",
            hostname="host1",
        ),
        True
    ),
    (
        # service_id contains a '.' char
        NFSServiceSpec(
            service_id="a.b.c",
        ),
        DaemonDescription(
            daemon_type='nfs',
            daemon_id="a.b.c.host1",
            hostname="host1",
        ),
        True
    ),
    (
        # trailing chars after hostname
        NFSServiceSpec(
            service_id="a.b.c",
        ),
        DaemonDescription(
            daemon_type='nfs',
            daemon_id="a.b.c.host1.abc123",
            hostname="host1",
        ),
        True
    ),
    (
        # chars after hostname without '.'
        NFSServiceSpec(
            service_id="a",
        ),
        DaemonDescription(
            daemon_type='nfs',
            daemon_id="a.host1abc123",
            hostname="host1",
        ),
        False
    ),
    (
        # chars before hostname without '.'
        NFSServiceSpec(
            service_id="a",
        ),
        DaemonDescription(
            daemon_type='nfs',
            daemon_id="ahost1.abc123",
            hostname="host1",
        ),
        False
    ),

    # https://tracker.ceph.com/issues/45293
    (
        IscsiServiceSpec(
            service_type='iscsi',
            service_id="a",
        ),
        DaemonDescription(
            daemon_type='iscsi',
            daemon_id="a.host1.abc123",
            hostname="host1",
        ),
        True
    ),
    (
        # '.' char in service_id
        IscsiServiceSpec(
            service_type='iscsi',
            service_id="a.b.c",
        ),
        DaemonDescription(
            daemon_type='iscsi',
            daemon_id="a.b.c.host1.abc123",
            hostname="host1",
        ),
        True
    ),
    (
        # fixed daemon id for teuthology.
        IscsiServiceSpec(
            service_type='iscsi',
            service_id='iscsi',
        ),
        DaemonDescription(
            daemon_type='iscsi',
            daemon_id="iscsi.a",
            hostname="host1",
        ),
        True
    ),

    (
        CustomContainerSpec(
            service_type='container',
            service_id='hello-world',
            image='docker.io/library/hello-world:latest',
        ),
        DaemonDescription(
            daemon_type='container',
            daemon_id='hello-world.mgr0',
            hostname='mgr0',
        ),
        True
    ),

    (
        # daemon_id only contains hostname
        ServiceSpec(
            service_type='cephadm-exporter',
        ),
        DaemonDescription(
            daemon_type='cephadm-exporter',
            daemon_id="testhost",
            hostname="testhost",
        ),
        True
    ),
])
def test_daemon_description_service_name(spec: ServiceSpec,
                                         dd: DaemonDescription,
                                         valid: bool):
    if valid:
        assert spec.service_name() == dd.service_name()
    else:
        with pytest.raises(OrchestratorError):
            dd.service_name()


def test_alertmanager_spec_1():
    spec = AlertManagerSpec()
    assert spec.service_type == 'alertmanager'
    assert isinstance(spec.user_data, dict)
    assert len(spec.user_data.keys()) == 0


def test_alertmanager_spec_2():
    spec = AlertManagerSpec(user_data={'default_webhook_urls': ['foo']})
    assert isinstance(spec.user_data, dict)
    assert 'default_webhook_urls' in spec.user_data.keys()


def test_custom_container_spec():
    spec = CustomContainerSpec(service_id='hello-world',
                               image='docker.io/library/hello-world:latest',
                               entrypoint='/usr/bin/bash',
                               uid=1000,
                               gid=2000,
                               volume_mounts={'foo': '/foo'},
                               args=['--foo'],
                               envs=['FOO=0815'],
                               bind_mounts=[
                                   [
                                       'type=bind',
                                       'source=lib/modules',
                                       'destination=/lib/modules',
                                       'ro=true'
                                   ]
                               ],
                               ports=[8080, 8443],
                               dirs=['foo', 'bar'],
                               files={
                                   'foo.conf': 'foo\nbar',
                                   'bar.conf': ['foo', 'bar']
                               })
    assert spec.service_type == 'container'
    assert spec.entrypoint == '/usr/bin/bash'
    assert spec.uid == 1000
    assert spec.gid == 2000
    assert spec.volume_mounts == {'foo': '/foo'}
    assert spec.args == ['--foo']
    assert spec.envs == ['FOO=0815']
    assert spec.bind_mounts == [
        [
            'type=bind',
            'source=lib/modules',
            'destination=/lib/modules',
            'ro=true'
        ]
    ]
    assert spec.ports == [8080, 8443]
    assert spec.dirs == ['foo', 'bar']
    assert spec.files == {
        'foo.conf': 'foo\nbar',
        'bar.conf': ['foo', 'bar']
    }


def test_custom_container_spec_config_json():
    spec = CustomContainerSpec(service_id='foo', image='foo', dirs=None)
    config_json = spec.config_json()
    for key in ['entrypoint', 'uid', 'gid', 'bind_mounts', 'dirs']:
        assert key not in config_json

def test_HA_RGW_spec():
    yaml_str = """service_type: ha-rgw
service_id: haproxy_for_rgw
placement:
  hosts:
    - host1
    - host2
    - host3
spec:
  virtual_ip_interface: eth0
  virtual_ip_address: 192.168.20.1/24
  frontend_port: 8080
  ha_proxy_port: 1967
  ha_proxy_stats_enabled: true
  ha_proxy_stats_user: admin
  ha_proxy_stats_password: admin
  ha_proxy_enable_prometheus_exporter: true
  ha_proxy_monitor_uri: /haproxy_health
  keepalived_password: admin
"""
    yaml_file = yaml.safe_load(yaml_str)
    spec = ServiceSpec.from_json(yaml_file)
    assert spec.service_type == "ha-rgw"
    assert spec.service_id == "haproxy_for_rgw"
    assert spec.virtual_ip_interface == "eth0"
    assert spec.virtual_ip_address == "192.168.20.1/24"
    assert spec.frontend_port == 8080
    assert spec.ha_proxy_port == 1967
    assert spec.ha_proxy_stats_enabled == True
    assert spec.ha_proxy_stats_user == "admin"
    assert spec.ha_proxy_stats_password == "admin"
    assert spec.ha_proxy_enable_prometheus_exporter == True
    assert spec.ha_proxy_monitor_uri == "/haproxy_health"
    assert spec.keepalived_password == "admin"
