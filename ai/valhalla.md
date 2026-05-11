# Valhalla — implementation reference

This is the implementation handoff doc for the `valhalla` role. Original
requirements (and free-form design notes) live in
[../working_doc.md](../working_doc.md). This file describes what was actually
built.

## Status

| sub-task | status |
|---|---|
| 1. Inventory + host_vars + Makefile + site.yml play | done |
| 2. Role skeleton | done |
| 3. Builder tasks (deps, src checkout, build, planet) | done |
| 4. Build-tiles loop script + systemd unit + graph push | done |
| 5. Service tasks (deps, prime_server, build, two systemd units) | done |
| 6. apply-graph.sh + dispatcher + sudoers + authorized_key | done |
| 7. Web app build/deploy | done |
| 8. Frontend nginx (API site, web app site, rate limits, X-Client-Id map) | done |
| 9. Deploy scripts + restricted SSH users | done |
| 10. icinga2agent registration | **pending** |
| Vagrant testing | scaffolded (two-VM setup landed, end-to-end run still pending) |

## Architecture overview

Two physical hosts, one role applied conditionally per group.

```
                   Internet (port 443)
                          │
                          ▼
┌──────────────── valhalla1.openstreetmap.de (162.55.2.221) ──────────────┐
│                                                                          │
│  nginx                                                                   │
│   ├─ valhalla1.openstreetmap.de  →  HTTP API                             │
│   │   upstream: 127.0.0.1:8000 + 127.0.0.1:8001                          │
│   │             (passive health checks + proxy_next_upstream)            │
│   ├─ valhalla.openstreetmap.de   →  static SPA (web-app vite build)      │
│   └─ rate-limit zones:                                                   │
│         - per-IP routing  1 r/s  (zone valhalla_per_ip)                  │
│         - per-IP /tile   10 r/s  (zone valhalla_tile_per_ip)             │
│         - global server 500 r/s  (zone valhalla_global)                  │
│       X-Client-Id classification map → access log only (no gating)       │
│                                                                          │
│  valhalla-8000.service │ valhalla-8001.service                           │
│   - both run side-by-side                                                │
│   - CPUQuota = vcpus * 50%  (each capped at half host CPU)               │
│   - --mjolnir-tile-extract /srv/valhalla/graph-{port}.tar                │
│   - drain_seconds=28 in valhalla.json                                    │
│                                                                          │
│  System accounts:                                                        │
│   - valhalla        (runtime; owns /srv/valhalla, /src/valhalla)         │
│   - valhalla-graph  (receives graph push from valhalla2)                 │
│   - valhalla-deploy (receives GHA deploy triggers)                       │
└────────────┬─────────────────────────────────────┬───────────────────────┘
             │ ssh as valhalla-graph              │ ssh as valhalla-deploy
             │ (forced cmd dispatcher:             │ (forced cmd: deploy-builder-runner.sh,
             │  rsync→rrsync; bare→apply-graph.sh) │  from= valhalla1's IP)
             ▼                                    ▼
┌──────────────── valhalla2.openstreetmap.de (162.55.103.19) ─────────────┐
│                                                                          │
│  valhalla-build-tiles.service                                            │
│   - endless loop: admins (once) → timezones (every iter)                 │
│     → valhalla_build_tiles --end build                                   │
│     → valhalla_build_elevation --from-tiles                              │
│     → valhalla_build_tiles --start_stage enhance                         │
│     → valhalla_build_extract → zstd → rsync(3× retry) → ssh trigger      │
│     → pyosmium-up-to-date → touch sentinel; loop                         │
│                                                                          │
│  System accounts:                                                        │
│   - valhalla        (runtime; same as above)                             │
│   - valhalla-deploy (receives builder rebuild triggers)                  │
└──────────────────────────────────────────────────────────────────────────┘
```

## Inventory

```ini
[valhalla_service]
valhalla1

[valhalla_builder]
valhalla2

[icinga2agent]
... + valhalla1 + valhalla2
```

Site.yml play targets both groups:

```yaml
- hosts: valhalla_service,valhalla_builder
  become: yes
  tags: valhalla
  roles:
    - role: valhalla
```

Makefile entries:

| target | scope | when to use |
|---|---|---|
| `make valhalla` | both hosts | full deploy. Required for first-time deploys (cross-host SSH key wiring needs both). |
| `make valhalla_service` | valhalla1 only | tweaks that don't touch SSH key wiring. |
| `make valhalla_builder` | valhalla2 only | tweaks that don't touch SSH key wiring. |

Partial-target runs *do* work for SSH key tasks now (we use `delegate_to` + `slurp` to read pubkeys from disk on the other host), but `make valhalla` is still the safe default.

## Variable layout

Variables are split across three levels so that each var lives at the
narrowest scope where it's actually used:

`roles/valhalla/defaults/main.yml` — shared across both groups (or
referenced cross-host via `hostvars[...]`):

```yaml
valhalla__user: valhalla
valhalla__basedir: /srv/valhalla
valhalla__srcdir: /src/valhalla

valhalla__git_repo: https://github.com/valhalla/valhalla.git
valhalla__git_version: master            # override per-host or via -e

valhalla__sentinel_max_age_hours: 16     # monitoring threshold (both sentinels)

valhalla__graph_user: valhalla-graph
valhalla__graph_user_home: /srv/valhalla-graph
valhalla__deploy_user: valhalla-deploy
valhalla__deploy_user_home: /srv/valhalla-deploy

valhalla__public_ipv4: "{{ ansible_default_ipv4.address }}"
```

`group_vars/valhalla_service.yml` — service-host-only (api/web nginx,
runtime ports, web app, GHA deploy authz, ACME cert declarations):

```yaml
valhalla__api_hostname: valhalla1.openstreetmap.de
valhalla__web_hostname: valhalla.openstreetmap.de
valhalla__service_ports: [8000, 8001]    # blue/green ports

valhalla__webapp_repo: https://github.com/valhalla/web-app.git
valhalla__webroot: /var/www/valhalla
valhalla__client_ids: [public-web-app]   # X-Client-Id values for log map

valhalla__apply_sentinel_path: "{{ valhalla__basedir }}/last_apply_complete"
valhalla__prime_server_srcdir: /src/prime_server

valhalla__deploy_pubkeys:                # populate from private/vars/
  service: ""
  builder: ""
  web: ""

valhalla__acme_certificates: [...]       # nginx cert declarations
```

`group_vars/valhalla_builder.yml` — builder-host-only (planet source,
all build paths, build-loop knob):

```yaml
valhalla__graph_push_target: valhalla1.openstreetmap.de   # vagrant overrides

valhalla__planet_url: https://planet.osm.org/pbf/planet-latest.osm.pbf

valhalla__config_path: "{{ valhalla__basedir }}/valhalla.json"
valhalla__data_dir:    "{{ valhalla__basedir }}/data"
valhalla__planet_path: "{{ valhalla__data_dir }}/planet.pbf"
valhalla__admins_path: "{{ valhalla__data_dir }}/admins.sqlite"
valhalla__timezones_path: "{{ valhalla__data_dir }}/timezones.sqlite"
valhalla__elevation_dir:  "{{ valhalla__data_dir }}/elevation"
valhalla__tiles_dir:      "{{ valhalla__data_dir }}/valhalla_tiles"
valhalla__tarball_path:   "{{ valhalla__data_dir }}/tiles.tar.zst"

valhalla__default_speeds_url: https://raw.githubusercontent.com/.../default_speeds.json
valhalla__default_speeds_path: "{{ valhalla__data_dir }}/default_speeds.json"

valhalla__build_loop_sleep_seconds: 0    # vagrant overrides to 300
valhalla__sentinel_path: "{{ valhalla__basedir }}/last_iteration_complete"

valhalla__acme_certificates: [...]       # munin cert only on the builder
```

`host_vars/valhalla1.yml` and `host_vars/valhalla2.yml` set
`valhalla__public_ipv4` (used as a `from=` SSH key restriction on the
peer's authorized_keys). For vagrant testing,
`host_vars/valhalla-{service,builder}.yml` additionally override
`valhalla__graph_push_target`, `valhalla__planet_url`, and
`valhalla__build_loop_sleep_seconds` to point at the private-network
peer and a small Geofabrik extract.

## System accounts

| account | host | shell | created in | purpose |
|---|---|---|---|---|
| `valhalla` | both | `/bin/false` | common.yml | runs valhalla services + build-tiles loop. owns `/srv/valhalla`, `/src/valhalla`. |
| `valhalla-graph` | valhalla1 | `/bin/bash` | service.yml | receives graph tarballs from valhalla2. forced-command SSH dispatcher. |
| `valhalla-deploy` | valhalla1 | `/bin/bash` | deploy_service.yml | receives GHA deploy triggers (3 forced-command keys). |
| `valhalla-deploy` | valhalla2 | `/bin/bash` | deploy_builder.yml | receives builder rebuild triggers from valhalla1. |

`valhalla-graph` is a member of the `valhalla` supplementary group so files it
writes in `/srv/valhalla` (mode `2775` sgid) are readable by the valhalla
service user.

## SSH trust paths

Three keypairs in total, all generated on disk by the ansible `user` module
and never regenerated unless deleted manually:

| keypair | generated on | private at | pubkey at | authorized on |
|---|---|---|---|---|
| graph push | valhalla2 (`valhalla` user) | `/srv/valhalla/.ssh/id_valhalla_graph` | `… .pub` | valhalla1's `valhalla-graph` (forced cmd: graph-receiver.sh) |
| builder deploy | valhalla1 (`valhalla-deploy` user) | `/srv/valhalla-deploy/.ssh/id_valhalla_builder_deploy` | `… .pub` | valhalla2's `valhalla-deploy` (forced cmd: deploy-builder-runner.sh, `from=` valhalla1's IP) |
| GHA deploys (×3) | external | GHA secrets | `valhalla__deploy_pubkeys` | valhalla1's `valhalla-deploy` (forced cmds: deploy-service.sh / deploy-builder.sh / deploy-web.sh) |

Cross-host pubkey wiring uses `slurp` + `delegate_to` instead of in-play
`set_fact`/`hostvars`. That makes partial-target reruns (`-l valhalla_builder`
alone) work, as long as the other host has the pubkey on disk from a previous
full run.

## Filesystem layout (service host)

```
/srv/valhalla/                          valhalla:valhalla 2775
├── scripts/                            valhalla:valhalla 0755
│   ├── apply-graph.sh                  # rolling tile-extract swap
│   ├── graph-receiver.sh               # SSH forced-command dispatcher
│   ├── deploy-service.sh               # GHA → rebuild valhalla locally
│   ├── deploy-builder.sh               # GHA → SSH-jump trigger to valhalla2
│   └── deploy-web.sh                   # GHA → rebuild + sync web app
├── valhalla-8000.json                  # per-port runtime config
├── valhalla-8001.json
├── graph-8000.tar                      # tile-extract; written by apply-graph
├── graph-8001.tar                      # (hardlink of graph-8000.tar)
├── mvt-cache-8000/                     # /tile cache for the 8000 instance
├── mvt-cache-8001/
├── web-app/                            # vite source
└── last_apply_complete                 # apply-graph sentinel (mtime)

/srv/valhalla-graph/                    valhalla-graph:valhalla-graph 0755
├── .ssh/authorized_keys                # forced cmd → graph-receiver.sh
└── tiles.tar.zst                       # rsync drop from valhalla2

/srv/valhalla-deploy/                   valhalla-deploy:valhalla-deploy
├── .ssh/id_valhalla_builder_deploy{,.pub}
└── .ssh/authorized_keys                # 3 forced-command keys (GHA)

/var/www/valhalla/                      valhalla:www-data
└── (vite build output)

/etc/sudoers.d/valhalla-graph           # systemctl stop/start valhalla-{ports}
/etc/sudoers.d/valhalla-deploy          # build/install/restart commands

/etc/nginx/conf.d/valhalla.conf         # upstream + maps + log fmt + zones
/etc/nginx/sites-available/valhalla1.openstreetmap.de
/etc/nginx/sites-available/valhalla.openstreetmap.de
```

## Filesystem layout (builder host)

```
/srv/valhalla/                          valhalla:valhalla 2775
├── scripts/
│   ├── build-tiles-loop.sh             # endless graph build loop
│   └── deploy-builder-runner.sh        # GHA-triggered rebuild
├── valhalla.json                       # builder-side config
├── data/
│   ├── planet.pbf
│   ├── admins.sqlite
│   ├── timezones.sqlite
│   ├── elevation/
│   ├── valhalla_tiles/                 # build output
│   ├── tiles.tar.zst                   # last successful tarball
│   └── default_speeds.json
├── .ssh/id_valhalla_graph{,.pub}       # for graph push to valhalla1
└── last_iteration_complete             # build sentinel (mtime)

/srv/valhalla-deploy/.ssh/authorized_keys  # 1 key, from= valhalla1
/etc/sudoers.d/valhalla-deploy
```

## systemd units

| unit | host | what |
|---|---|---|
| `valhalla-build-tiles.service` | valhalla2 | runs `scripts/build-tiles-loop.sh`. `Restart=always`, `RestartSec=60`, `StartLimitBurst=3 / StartLimitIntervalSec=600` so persistent fast failures pin it as `failed` for monitoring. |
| `valhalla-8000.service` | valhalla1 | runs `valhalla_service /srv/valhalla/valhalla-8000.json`. `CPUQuota = vcpus * 50%`. |
| `valhalla-8001.service` | valhalla1 | same, port 8001. |

## nginx (service host only)

- Global config in `/etc/nginx/conf.d/valhalla.conf`:
  - `upstream valhalla { server 127.0.0.1:8000 max_fails=1 fail_timeout=10s; ... }`
  - `map $http_x_client_id $client_class { default unknown; "public-web-app" "public-web-app"; }`
  - `log_format valhalla_log '$ip_anonymized [$time_local] $request_method $uri $status $body_bytes_sent rqt=$request_time urt=$upstream_response_time client=$client_class'`
  - Three `limit_req_zone`s.
- Two sites:
  - `valhalla1.openstreetmap.de` — proxies to upstream, with `proxy_next_upstream error timeout http_502 http_503` so a stopped-for-restart instance fails over transparently. `/tile` uses the higher per-IP zone; `/status` is unrestricted and log-suppressed.
  - `valhalla.openstreetmap.de` — static files from `/var/www/valhalla` with vite-style SPA fallback.
- Letsencrypt is automatic via the existing `valhalla__acme_certificates` (handled by `roles/common/tasks/acme_cert_client.yml`).
- `notify: reload nginx` everywhere — zero-downtime config rolls.

## Deploy flows

**Graph push (continuous, autonomous).** Runs in the build-tiles loop on
valhalla2:
1. Build tiles → `valhalla_build_extract` (writes uncompressed tar to `mjolnir.tile_extract`) → `zstd -T0 -3` to `tiles.tar.zst` via `.partial` + atomic mv.
2. `rsync --partial --inplace` (over SSH as `valhalla-graph`) to `valhalla-graph@valhalla1:tiles.tar.zst`. 3 attempts within the same iteration, 30s backoff between — `--partial`/`--inplace` mean a re-attempt resumes against the same source bytes after a transient network failure.
3. Bare ssh to `valhalla-graph@valhalla1` → forced-command dispatcher → `apply-graph.sh`.
4. apply-graph: `zstd -d` to `graph-{first-port}.tar.partial`, atomic `mv` to `.tar`, hardlink for the other port, then sequential `systemctl stop`/`start` per port with `/status` healthcheck (1s polling, 60s budget). Both instances always run; nginx fails over via passive health checks during the brief unavailability of one.

**Code deploys (GHA-triggered, 3 flavors).** Each flavor is its own pubkey in
`valhalla__deploy_pubkeys`, each pinned to one forced-command script:

```
GHA → ssh valhalla-deploy@valhalla1 (forced: deploy-service.sh)
        → pull/build/install + rolling restart on valhalla1

GHA → ssh valhalla-deploy@valhalla1 (forced: deploy-builder.sh)
        → ssh valhalla-deploy@valhalla2 (from= valhalla1, forced: deploy-builder-runner.sh)
        → pull/build/install on valhalla2 (NO restart — next loop iteration picks up new binary)

GHA → ssh valhalla-deploy@valhalla1 (forced: deploy-web.sh)
        → auto-elevate to valhalla, pull/build vite/sync to webroot
```

Sudoers grants `valhalla-deploy` NOPASSWD `sudo -u valhalla` (broad — for build phase) plus pinned root commands (`make install`, `ldconfig`, `systemctl restart valhalla-{ports}`, `systemctl reload nginx`).

## Monitoring signals (already in place; sub-task 10 wires the alerts)

| signal | host | path / threshold |
|---|---|---|
| sentinel mtime: build | valhalla2 | `valhalla__sentinel_path` (= `/srv/valhalla/last_iteration_complete`) |
| sentinel mtime: apply | valhalla1 | `valhalla__apply_sentinel_path` (= `/srv/valhalla/last_apply_complete`) |
| systemd unit state | both | `valhalla-{8000,8001,build-tiles}.service` |
| HTTP healthcheck | external | `https://valhalla1.openstreetmap.de/status` |

Threshold for "stale": `valhalla__sentinel_max_age_hours: 16`.

## Logging

| script | tag | view with |
|---|---|---|
| build-tiles loop | `valhalla-build-tiles` | `journalctl -t valhalla-build-tiles -f` |
| apply-graph | `valhalla-apply-graph` | `journalctl -t valhalla-apply-graph -f` |
| deploy-web | `valhalla-deploy-web` | `journalctl -t valhalla-deploy-web -f` |
| deploy-service | `valhalla-deploy-service` | `journalctl -t valhalla-deploy-service -f` |
| deploy-builder runner | `valhalla-deploy-builder` | `journalctl -t valhalla-deploy-builder -f` |
| graph-receiver dispatcher | `valhalla-graph-receiver` | `journalctl -t valhalla-graph-receiver -f` (warn-level only — rejection log) |

Build-tiles uses three priorities (`daemon.info`, `daemon.warning`, `daemon.err`) — filter with `journalctl … -p err` etc.

## Vagrant testing

Two-VM setup that mirrors the production cross-host wiring. Both VMs share
a libvirt `private_network` so the IPs the ansible controller uses are the
same ones the VMs use to reach each other (graph push, deploy trigger).

```
vagrant up valhalla-service valhalla-builder
make vagrant-valhalla
```

`make vagrant-valhalla` runs `init_vagrant_inventory.sh valhalla-service
valhalla-builder` first (so re-created VMs pick up the current SSH
identity files) and then `ansible-playbook -i vagrant.ini -l
valhalla_service,valhalla_builder site.yml`.

Resources: building valhalla + boost-dev + prime_server is heavy.
[../Vagrantfile](../Vagrantfile) defaults each valhalla VM to 6 GiB RAM
and 4 vCPUs; override with `VAGRANT_VALHALLA_MEMORY` and
`VAGRANT_VALHALLA_CPUS` if your host can afford more or less.

### What the vagrant overrides change

[../host_vars/valhalla-service.yml](../host_vars/valhalla-service.yml) and
[../host_vars/valhalla-builder.yml](../host_vars/valhalla-builder.yml)
override:

- `valhalla__public_ipv4` → the libvirt private IP. Drives the `from=`
  restriction on valhalla-builder's authorized_keys; using the actual
  source IP (rather than the production public IP) keeps the restriction
  honest end-to-end.
- `valhalla__api_hostname` / `valhalla__web_hostname` → the service VM's
  private IP. The builder SSHes us at this address for graph push and
  apply-graph trigger; nginx server_name lines up with what `curl
  https://192.168.123.10/` from the host will send.
- `valhalla__planet_url` → Geofabrik Liechtenstein extract (~2 MB)
  instead of the ~80 GB global planet. Exercises the same
  `valhalla_build_tiles` + admins + timezones + elevation pipeline.

### Things to know before testing

- **Letsencrypt**: the acme renewal task only runs on the `[acme]` group;
  vagrant.ini has a `dummy` placeholder so site.yml's `- hosts: acme` is
  a no-op. Nginx serves the snake-oil placeholder cert from
  `roles/common/tasks/acme_cert_client.yml` — browser warnings are
  expected; `curl -k` from the host works.
- **GHA deploy keys**: `valhalla__deploy_pubkeys` defaults are empty
  strings, so no GHA-trigger authorized_keys get written and the
  GHA-side flow isn't reachable from vagrant. To exercise the script
  logic, ssh into the VM and invoke
  `/srv/valhalla/scripts/deploy-*.sh` manually.
- **Elevation**: `valhalla_build_elevation --from-tiles` is bounded by
  graph extent, so on Liechtenstein only a handful of SRTM tiles are
  fetched.
- **Single-VM standalone testing**: if you need to test only the
  service-side or only the builder-side without spinning both VMs, the
  cross-host SSH-key tasks (`slurp` + `delegate_to`) will fail because
  the peer host isn't reachable. `--skip-tags` won't help here — those
  tasks aren't tagged. Either spin both VMs, or temporarily comment out
  the `apply_graph.yml` slurp on the service play / `deploy_builder.yml`
  slurp on the builder play.
- **`community.postgresql` collection**: `ansible-playbook
  --syntax-check site.yml` fails on the unrelated postgresql role until
  `ansible-galaxy install -r requirements.yml -f` has been run.

### Curl from the host

```sh
curl -k https://192.168.123.10/status
curl -k 'https://192.168.123.10/route' \
    --data '{"locations":[...],"costing":"auto"}'
```

The legacy single-VM workflow (`./init_vagrant_inventory.sh trixie` +
`make vagrant`) still works for testing other roles — see [../README](../README).

## Known gotchas / non-obvious decisions

- **Both blue and green run continuously.** Each capped at half host vCPUs via systemd `CPUQuota`. apply-graph stops/swaps/starts each in turn. This is in lieu of a "currently active port" state file.
- **`drain_seconds=28`** in valhalla.json means `systemctl stop` blocks ~29s. The script doesn't need extra wait logic.
- **`set -euo pipefail`** in build-tiles-loop.sh — pathological failures abort. systemd restarts. Sentinel mtime is the monitoring signal; brief restart cycling is the secondary signal (StartLimitBurst).
- **Tarball is built in two steps**: `valhalla_build_extract` writes the uncompressed tar to `mjolnir.tile_extract` (path from CONFIG, currently the valhalla default — needs an explicit `--mjolnir-tile-extract` in `valhalla_build_config` to match `${TARBALL%.zst}` if the default ever changes), then a separate `zstd -T0 -3 -f` produces `tiles.tar.zst` via the `.partial` + atomic-mv pattern. `-T0 -3` is fast compression, not max — tile data is binary and already compressible, so `-19` isn't worth the CPU.
- **rrsync as `/usr/bin/rrsync`** — Debian 13 ships it in the rsync package at that path. If a vagrant test box has a different path (older Debian had it gzipped under `/usr/share/doc/`), graph push will fail at the rrsync step.
- **cmake flag duplication**: deploy-service.sh / deploy-builder-runner.sh hardcode the same `-DENABLE_*=...` flags as service.yml / builder.yml. Drift risk if you tune in one place. Refactoring into a defaults list is a good follow-up but not done.
- **No ufw rule restricting valhalla2's SSH to valhalla1's IP.** Admins can still SSH valhalla2 directly. The intended-but-not-implemented bastion model would route admin SSH through valhalla1 via `ProxyJump`. Without a static admin source IP (or a VPN), full lockdown isn't practical.

## Pending: sub-task 10 — icinga2agent

Files / patterns to follow: see `roles/osrm/tasks/main.yml` "munin statistics"
section for plugin structure, and the existing icinga2agent group in
`hosts.ini`.

Checks to add:
- `check_systemd valhalla-{8000,8001}` on valhalla1.
- `check_systemd valhalla-build-tiles` on valhalla2.
- `check_file_age` against build sentinel (`/srv/valhalla/last_iteration_complete` on valhalla2) with `valhalla__sentinel_max_age_hours = 16`.
- `check_file_age` against apply sentinel (`/srv/valhalla/last_apply_complete` on valhalla1) with the same threshold.
- `check_http https://valhalla1.openstreetmap.de/status` (external).
- `check_http https://valhalla.openstreetmap.de/` (external — web app).

Optional munin plugins for graphs (request count, latency) — modeled on
`roles/osrm/templates/munin_*.j2`. Not on the day-1 critical path.

## Quick "did everything land" check

```sh
ls roles/valhalla/{tasks,templates,defaults,meta,handlers}
# tasks: main.yml common.yml builder.yml service.yml web.yml frontend.yml
#        tiles_loop.yml apply_graph.yml deploy_service.yml deploy_builder.yml
# templates: build-tiles-loop.sh.j2 apply-graph.sh.j2 graph-receiver.sh.j2
#            valhalla-graph.sudoers.j2 deploy-service.sh.j2 deploy-builder.sh.j2
#            deploy-builder-runner.sh.j2 valhalla-deploy-{service,builder}.sudoers.j2
#            deploy-web.sh.j2 nginx-valhalla.conf.j2 nginx-api.j2 nginx-web.j2
# defaults: main.yml
# meta: main.yml
# handlers: (empty — uses the nginx role's handlers via meta deps)

git status
# should show roles/valhalla/ as the bulk of new content,
# plus host_vars/valhalla{1,2}.yml, hosts.ini, site.yml, Makefile
```
