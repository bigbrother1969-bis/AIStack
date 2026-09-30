from aistack.runtime.inventory_gap import discovered_containers_from_network_observation


def test_containers_from_every_host_are_collected():
    observation = {
        "network_docker": {
            "cidr": "192.168.1.0/24",
            "hosts": [
                {
                    "host": "192.168.1.53",
                    "containers": [
                        {"Names": "vaultwarden", "ID": "abc123"},
                        {"Names": "vikunja", "ID": "def456"},
                    ],
                },
                {
                    "host": "192.168.1.60",
                    "containers": [{"Names": "pihole", "ID": "ghi789"}],
                },
            ],
        }
    }

    containers = discovered_containers_from_network_observation(observation)

    assert containers == {
        "vaultwarden": "192.168.1.53",
        "vikunja": "192.168.1.53",
        "pihole": "192.168.1.60",
    }


def test_names_falls_back_to_name_then_id():
    observation = {
        "network_docker": {
            "hosts": [
                {
                    "host": "192.168.1.53",
                    "containers": [
                        {"Names": "", "Name": "fallback-name", "ID": "abc"},
                        {"Names": "", "Name": "", "ID": "fallback-id"},
                    ],
                }
            ]
        }
    }

    containers = discovered_containers_from_network_observation(observation)

    assert containers == {"fallback-name": "192.168.1.53", "fallback-id": "192.168.1.53"}


def test_a_container_with_no_identity_at_all_is_skipped():
    observation = {
        "network_docker": {
            "hosts": [{"host": "192.168.1.53", "containers": [{"Names": ""}]}]
        }
    }

    assert discovered_containers_from_network_observation(observation) == {}


def test_a_host_entry_with_no_host_contributes_nothing():
    observation = {
        "network_docker": {
            "hosts": [{"containers": [{"Names": "orphan"}]}]
        }
    }

    assert discovered_containers_from_network_observation(observation) == {}


def test_an_observation_with_no_hosts_at_all_is_empty():
    assert discovered_containers_from_network_observation({}) == {}
    assert discovered_containers_from_network_observation({"network_docker": {}}) == {}
