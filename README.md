# Nautobot and Ansible workshop — lab repository

The lab repository for the Network to Code workshop *From Intent to Execution: Nautobot and Ansible, Better Together*.

Everything the labs run lives here: the playbooks, the inventories, the Jinja2 templates, the GraphQL query, the Nautobot Job, the ContainerLab topology and the AWX deployment files. AWX syncs its project from this repository, and Nautobot imports its Job from it.

The step-by-step lab instructions are in the companion repository, [`nautobot-ansible-workshop-guide`](https://github.com/networktocode/nautobot-ansible-workshop-guide). Start there if you are taking the workshop.

## The idea

The workshop starts from a setup that works but is disconnected from the source of truth: a hand-maintained inventory, variables in `group_vars`, and an AWX survey where an operator retypes facts Nautobot already holds. Each lab replaces one piece of that with Nautobot.

| Lab | What changes | Files involved |
| --- | --- | --- |
| 0 — Cold open | Nothing yet: a static inventory and a six-field survey | `inventory/static.ini`, `inventory/group_vars/leaf.yml`, `playbooks/configure_base.yml`, `templates/base.j2` |
| 1 — Inventory | Nautobot becomes the inventory; a Dynamic Group decides the targets | `inventory/nautobot.yml`, `playbooks/target_dynamic_group.yml` |
| 2 — Intent | Config Contexts replace `group_vars`; one GraphQL query drives a full config and a diff | `graphql/device_intent.gql`, `templates/full_config.j2`, `playbooks/render_intent.yml`, `playbooks/diff_intent.yml` |
| 3 — Write-back | Devices report state back to Nautobot; a Nautobot button launches AWX | `playbooks/write_back.yml`, `jobs/launch_awx.py` |
| 4 — Approval | A change in Nautobot triggers an AWX workflow behind an approval gate | `playbooks/turnup_diff.yml`, `playbooks/turnup_apply.yml` |

`playbooks/configure_base.yml` does not change across the labs. Only where its inventory and variables come from changes, which is the point.

## Layout

```
nautobot-ansible-workshop/
├── ansible.cfg
├── requirements-host.txt         # Python lockfile for the Ansible control host
├── collections/
│   └── requirements.yml          # Ansible collections, exact versions
├── inventory/
│   ├── static.ini                # Lab 0: hand-maintained
│   ├── nautobot.yml              # Lab 1 onward: Nautobot dynamic inventory
│   └── group_vars/
│       ├── all.yml               # connection settings for every device
│       └── leaf.yml              # Lab 0 variables, replaced in Lab 2
├── playbooks/
│   ├── configure_base.yml        # base config: NTP, DNS, SNMP, syslog
│   ├── target_dynamic_group.yml  # run against a Nautobot Dynamic Group
│   ├── render_intent.yml         # render a full config from GraphQL
│   ├── diff_intent.yml           # compare intent with the running config
│   ├── write_back.yml            # write device state back to Nautobot
│   ├── turnup_diff.yml           # Lab 4 workflow, preview step
│   ├── turnup_apply.yml          # Lab 4 workflow, apply step
│   ├── seed_nautobot.yml         # create every Nautobot object the labs use
│   ├── seed_awx.yml              # create every AWX object the labs use
│   └── reset_lab.yml             # reset lab state to the start of a lab
├── templates/
│   ├── base.j2                   # Labs 0–1
│   └── full_config.j2            # Lab 2 onward
├── graphql/
│   └── device_intent.gql
├── jobs/
│   └── launch_awx.py             # Nautobot Job behind Lab 3's button
├── clab/
│   └── workshop.clab.yml         # two Arista cEOS nodes
├── awx/
│   ├── kustomization.yaml        # awx-operator 2.19.1
│   └── awx.yml                   # the AWX instance, every image pinned
└── ee/
    └── execution-environment.yml # the AWX execution environment
```

Two layout details matter:

- **`group_vars/` sits beside the inventory, not at the repository root.** Ansible looks for `group_vars/` next to the inventory file or the playbook. At the root it is silently ignored, which looks exactly like "my variables are not applying".
- **`inventory/nautobot.yml` is executable on purpose.** AWX's inventory-file picker only lists `.ini` files, files named `inventory` or `hosts`, and executable files. The workshop switches inventories at the AWX Inventory level instead, but the mode is kept so the file stays selectable.

## Versions

Everything is pinned to the versions the workshop was tested with.

| Component | Version |
| --- | --- |
| Nautobot | 3.2.3 |
| AWX / awx-operator | 24.6.1 / 2.19.1 |
| Kubernetes (minikube) | v1.35.1 |
| ContainerLab | 0.79.0 |
| Arista cEOS | 4.33.10M |
| ansible-core | 2.18.19 (Python 3.12) |
| Ansible collections | see `collections/requirements.yml` |

## Running it yourself

In the workshop, every attendee gets a virtual machine with all of this already running and seeded. To build the same environment on your own Ubuntu 24.04 machine, these are the pieces and the order they go in. Plan for at least 16 GB of RAM and 4 vCPUs: AWX alone takes 8 GB.

### Addresses

The labs use fixed addresses, and the seed playbooks write them into Nautobot and AWX. The same service has a different address depending on who is asking:

| Service | From the host | From an AWX job | From Nautobot |
| --- | --- | --- | --- |
| Nautobot | `http://localhost:8001` | `http://192.168.49.1:8001` | — |
| AWX | `http://localhost:8013` | — | `http://192.168.49.1:8013` |
| `leaf1` / `leaf2` | `172.20.20.11` / `172.20.20.12` | same | — |

`192.168.49.1` is the host's address on minikube's network, which is why minikube must be started on that subnet.

### 1. Ansible on the host

```bash
python3 -m venv /opt/ansible && /opt/ansible/bin/pip install -r requirements-host.txt
```

```bash
/opt/ansible/bin/ansible-galaxy collection install -r collections/requirements.yml && /opt/ansible/bin/ansible-galaxy collection install awx.awx:24.6.1
```

`awx.awx` is only needed on the host, by `seed_awx.yml`. Keep `setuptools` at the version in the lockfile: newer releases remove a module the `awx` CLI still imports.

### 2. The devices

cEOS is distributed by Arista as a filesystem tarball and needs a free arista.com account. Import it with `docker import`, not `docker load`. On x86_64 the file is `cEOS64-lab-4.33.10M.tar.xz`; on ARM it is `cEOSarm-lab-4.33.10M.tar.xz`.

```bash
docker import cEOS64-lab-4.33.10M.tar.xz ceos:4.33.10M
```

```bash
sudo containerlab deploy -t clab/workshop.clab.yml
```

The management addresses are pinned in the topology, so `leaf1` is always `.11` and `leaf2` always `.12`. Both nodes log in with `admin` / `admin`.

### 3. Nautobot

Install Nautobot 3.2.3 any way you like, as long as it answers on port 8001 and has a superuser `admin` / `admin` with the API token `0123456789abcdef0123456789abcdef01234567`. AWX jobs reach it at `192.168.49.1:8001`, so it must listen on more than loopback. Nautobot also needs outbound internet access, because it imports its Job from this repository on GitHub.

### 4. AWX

Start minikube on the subnet the addresses above depend on:

```bash
minikube start --driver=docker --profile=awx --subnet=192.168.49.0/24 --kubernetes-version=v1.35.1 --memory=8192 --cpus=no-limit --addons=metrics-server
```

Install the operator, set the admin password before creating the instance, then create it:

```bash
kubectl apply -k awx/
```

```bash
kubectl -n awx create secret generic awx-admin-password --from-literal=password=admin
```

```bash
kubectl apply -f awx/awx.yml
```

When the AWX pods are running, publish AWX on port 8013. Bind it to `0.0.0.0`: Nautobot reaches AWX at `192.168.49.1:8013`, and a loopback-only forward refuses that.

```bash
kubectl -n awx port-forward --address 0.0.0.0 svc/awx-service 8013:80
```

### 5. The execution environment

The stock AWX execution environment ships an Ansible too old for these collections, so the labs use a custom one, loaded straight into minikube:

```bash
cd ee && /opt/ansible/bin/ansible-builder build --tag workshop-ee:1.0.0 --container-runtime docker
```

```bash
minikube -p awx image load workshop-ee:1.0.0
```

### 6. Seed Nautobot and AWX

```bash
/opt/ansible/bin/ansible-playbook playbooks/seed_nautobot.yml
```

```bash
/opt/ansible/bin/ansible-playbook playbooks/seed_awx.yml
```

Both are safe to re-run. `seed_awx.yml` also writes the AWX connection details that Nautobot's worker needs for Lab 3, and restarts Nautobot to pick them up. It supports two layouts through `NAUTOBOT_DEPLOYMENT`: `compose` (the default, for [nautobot-docker-compose](https://github.com/nautobot/nautobot-docker-compose)) and `native` (Nautobot running as systemd services under `/opt/nautobot`). With the compose layout, the `nautobot` and `celery_worker` services need `extra_hosts: ["host.docker.internal:host-gateway"]` so they can reach AWX.

For the lab commands in the guide, export the Nautobot connection details in your shell:

```bash
export NAUTOBOT_URL="http://localhost:8001" NAUTOBOT_TOKEN="0123456789abcdef0123456789abcdef01234567"
```

## Troubleshooting

- **`Unable to parse … as an inventory source` and no hosts.** Read the line that mentions the `auto plugin`, not the last line. It names the real problem: usually `NAUTOBOT_URL` / `NAUTOBOT_TOKEN` not set, or a typo in `inventory/nautobot.yml`. If there is no `auto plugin` line at all, you are not in the repository directory.
- **`Too many authentication failures` from a device.** SSH offers every key in your agent before the password, and each attempt counts. The repository already turns key lookup off for paramiko (`look_for_keys = False` in `ansible.cfg`) and selects paramiko in the inventory. If it persists, retype the password, then try again with `SSH_AUTH_SOCK=` in front of the command.
- **An AWX job cannot reach Nautobot or the devices.** Check from inside the cluster: `kubectl -n awx run nettest --rm -it --restart=Never --image=busybox -- ping -c3 172.20.20.11`. Nautobot must be reachable at `192.168.49.1:8001` from there.
- **A Dynamic Group change does not show up.** Nautobot stores group membership. Run **Refresh Members** on the group after changing its filter.

## Not for production

This environment trades security for a smooth workshop. Do not carry these choices into a real deployment:

- Static, shared credentials everywhere (`admin` / `admin`) and a fixed API token
- HTTP rather than HTTPS, and no TLS on webhooks
- No RBAC beyond the default administrator
- SSH host key checking turned off (`host_key_checking = False`)
- A single user with administrative rights in Nautobot and AWX
