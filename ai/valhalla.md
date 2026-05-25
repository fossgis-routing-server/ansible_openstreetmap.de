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
| 3. Builder tasks (deps, src checkout, build) | done |
| 4. Build-tiles loop script + systemd unit + graph push | done |
| 5. Service tasks (deps, prime_server, build, two systemd units) | done |
| 6. apply-graph.sh + sudoers + authorized_key | done |
| 7. Web app build/deploy | done |
| 8. Frontend nginx (API site, web app site, rate limits, X-Client-Id map) | done |
| 9. Deploy scripts driven by the build-tiles loop on v2 | done |
| 10. Munin plugins (count, latency, consumers, tile_size) | done |
| 11. icinga2agent registration | done |
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
│   - valhalla_service ...json <vcpus>   (worker threads = full host)      │
│   - no CPUQuota — kernel fair-shares when both hot; one burst-uses       │
│     the whole host when the other is stopped mid-apply-graph             │
│   - --mjolnir-tile-extract /srv/valhalla/graph-{port}.tar                │
│   - drain_seconds=28 in valhalla.json                                    │
│                                                                          │
│  System accounts:                                                        │
│   - valhalla        (runtime-only; runs valhalla_service. owns           │
│                      /srv/valhalla itself (sgid bucket) + mvt-cache-*;   │
│                      ZERO sudoers, can't write the install prefix)       │
│   - valhalla-deploy (build + orchestrator target; shell; owns /src/*,    │
│                      /srv/valhalla/{local,scripts,web-app},              │
│                      /var/www/valhalla; in 'valhalla' group;             │
│                      receives graph drops + runs the rebuild scripts)   │
└────────────▲─────────────────────────────────────────────────────────────┘
             │ ssh as valhalla-deploy (plain, no key_options)
             │   - rsync tiles.tar.zst → ~/tiles.tar.zst
             │   - run apply-graph.sh / deploy-valhalla.sh / deploy-web.sh
             │
┌──────────────── valhalla2.openstreetmap.de (162.55.103.19) ─────────────┐
│                                                                          │
│  valhalla-build-tiles.service  (User=valhalla-deploy)                    │
│   - build-tiles-loop.sh (wrapper: while true; do iteration.sh; done)     │
│   - build-tiles-iteration.sh (one iteration's work; re-read each loop)   │
│     → deploy-valhalla.sh builder        (SHA-gated v2 rebuild)           │
│     → ssh v1: deploy-valhalla.sh service (SHA-gated v1 rebuild)          │
│     → ssh v1: deploy-web.sh             (HEAD-gated web-app rebuild)     │
│     → bootstrap planet.pbf if missing → pyosmium-up-to-date              │
│     → admins (once) → timezones (every iter)                             │
│     → valhalla_build_tiles --end build                                   │
│     → valhalla_build_elevation --from-tiles                              │
│     → valhalla_build_tiles --start enhance                               │
│     → valhalla_build_extract → zstd → rsync(3× retry) → ssh apply-graph  │
│     → touch sentinel; loop                                               │
│                                                                          │
│  System accounts:                                                        │
│   - valhalla        (idle; owner of /srv/valhalla itself for sgid)       │
│   - valhalla-deploy (build + orchestrator; owns /src/*, install prefix,  │
│                      /srv/valhalla/data; holds id_valhalla_deploy SSH key) │
└──────────────────────────────────────────────────────────────────────────┘
```

## Inventory

```ini
[valhalla_service]
valhalla1

[valhalla_builder]
valhalla2

# Parent group for vars both halves share — and that monitoring.yml
# can resolve without loading the role. See group_vars/valhalla/.
[valhalla:children]
valhalla_service
valhalla_builder

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

Variables are split across four levels so that each var lives at the
narrowest scope where it's actually used:

`group_vars/valhalla/vars.yml` (parent group `[valhalla:children]`,
loaded for both halves AND for monitoring.yml plays that target
icinga2agent without including the role):

```yaml
valhalla__basedir: /srv/valhalla
valhalla__sentinel_max_age_hours: 16     # icinga file_age threshold (both sentinels)
```

`group_vars/valhalla/vault.yml` (same group, but encrypted with
`ansible-vault` — see "Secrets" below). Holds
`valhalla__download_password`, `valhalla__prometheus_scraper_ip`,
`valhalla__letsencrypt_email`, and the admin `users:` list.

`roles/valhalla/defaults/main.yml` — shared across both groups (or
referenced cross-host via `hostvars[...]`), only needed where the role
itself runs:

```yaml
valhalla__user: valhalla
valhalla__srcdir: /src/valhalla

valhalla__git_repo: https://github.com/valhalla/valhalla.git
valhalla__git_version: master            # override per-host or via -e

valhalla__prefix: "{{ valhalla__basedir }}/local"   # user-writable install tree (no /usr/local, no sudo)

valhalla__deploy_user: valhalla-deploy   # build/deploy/orchestrator identity on both hosts
valhalla__deploy_user_home: /srv/valhalla-deploy
valhalla__build_user: "{{ valhalla__deploy_user }}"   # semantic alias used by build-related tasks
```

`group_vars/valhalla_service.yml` — service-host-only (api/web nginx,
runtime ports, web app, ACME cert declarations):

```yaml
valhalla__api_hostname: valhalla1.openstreetmap.de
valhalla__web_hostname: valhalla.openstreetmap.de
valhalla__service_ports: [8000, 8001]    # blue/green ports

valhalla__webapp_repo: https://github.com/valhalla/web-app.git
valhalla__webroot: /var/www/valhalla
valhalla__client_ids: [public-web-app]   # X-Client-Id values for log map

valhalla__apply_sentinel_path: "{{ valhalla__basedir }}/last_apply_complete"
valhalla__prime_server_srcdir: /src/prime_server

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

For vagrant testing, `host_vars/valhalla-builder.yml` overrides
`valhalla__graph_push_target`, `valhalla__planet_url`, and
`valhalla__build_loop_sleep_seconds` to point at the private-network
peer and a small Geofabrik extract.

## System accounts

| account | host | shell | created in | purpose |
|---|---|---|---|---|
| `valhalla` | both | `/bin/false` | common.yml | **runtime-only**: runs `valhalla_service` (v1 only). On v2 has no running service — exists as the owner of `/srv/valhalla` itself (the sgid bucket) and `/srv/valhalla/mvt-cache-*` on v1. zero sudoers anywhere. |
| `valhalla-deploy` | both | `/bin/bash` | common.yml | **deploy / build / data identity**. Owns `/src/valhalla`, `/src/prime_server`, `/srv/valhalla/{local,data,scripts}`, `/srv/valhalla/web-app`, `/var/www/valhalla`. On v2 runs the build-tiles loop (User= in systemd) and holds the orchestrator SSH key in `~/.ssh`. On v1 receives the orchestrator SSH login and runs apply-graph.sh / deploy-valhalla.sh / deploy-web.sh. member of `valhalla` group so v1's runtime can read what it writes. sudoers (v1 only): `systemctl` (per-port) + `nginx reload`. |

`valhalla-deploy` is a member of the `valhalla` supplementary group so files
it writes in `/srv/valhalla` (mode `2775` sgid) are readable by the v1
runtime user. The build dirs it owns (`/src/valhalla`, `/srv/valhalla/local`)
use mode `02755` — sgid with group=valhalla — so install artifacts inherit
group=valhalla and are read-only to that group, blocking self-rewrite from
a service-side RCE.

## SSH trust paths

One keypair, generated on disk by the ansible `user` module and never
regenerated unless deleted manually:

| keypair | generated on | private at | pubkey at | authorized on |
|---|---|---|---|---|
| orchestrator | valhalla2 (`valhalla-deploy` user) | `/srv/valhalla-deploy/.ssh/id_valhalla_deploy` | `… .pub` | valhalla1's `valhalla-deploy` (plain — no `key_options`) |

Cross-host pubkey wiring uses `slurp` + `delegate_to` instead of in-play
`set_fact`/`hostvars`. That makes partial-target reruns (`-l valhalla_service`
alone) work, as long as the builder has the pubkey on disk from a previous
full run.

## Filesystem layout (service host)

```
/srv/valhalla/                          valhalla:valhalla 2775
├── scripts/                            valhalla:valhalla 0755
│   ├── apply-graph.sh                  # rolling tile-extract swap
│   ├── deploy-valhalla.sh              # SHA-gated valhalla pull+rebuild
│   └── deploy-web.sh                   # HEAD-gated web-app pull+rebuild
├── local/                              # user-writable install prefix
│   ├── bin/valhalla_service            # → systemd units' ExecStart
│   ├── lib/libvalhalla*.so             # → LD_LIBRARY_PATH
│   └── include/, share/, ...
├── valhalla-8000.json                  # per-port runtime config
├── valhalla-8001.json
├── graph-8000.tar                      # tile-extract; written by apply-graph
├── graph-8001.tar                      # (hardlink of graph-8000.tar)
├── mvt-cache-8000/                     # /tile cache for the 8000 instance
├── mvt-cache-8001/
├── web-app/                            # vite source
└── last_apply_complete                 # apply-graph sentinel (mtime)

/srv/valhalla-deploy/                   valhalla-deploy:valhalla 0755
├── .ssh/authorized_keys                # one key, no key_options
└── tiles.tar.zst                       # rsync drop from valhalla2

/var/www/valhalla/                      valhalla:www-data
└── (vite build output)

/etc/sudoers.d/valhalla-deploy          # (valhalla) NOPASSWD: ALL  + systemctl stop/start/restart valhalla-{ports} + nginx reload

/etc/nginx/conf.d/valhalla.conf         # upstream + maps + log fmt + zones
/etc/nginx/sites-available/valhalla1.openstreetmap.de
/etc/nginx/sites-available/valhalla.openstreetmap.de
```

## Filesystem layout (builder host)

```
/srv/valhalla/                          valhalla:valhalla 2775
├── scripts/                            valhalla:valhalla 0755
│   ├── build-tiles-loop.sh             # tiny wrapper: while-loop calling iteration.sh
│   ├── build-tiles-iteration.sh        # one iteration's work — edits auto-deploy next iter
│   └── deploy-valhalla.sh              # shared SHA-gated rebuild (builder profile here)
├── local/                              valhalla-deploy:valhalla 02755
│   ├── bin/valhalla_build_tiles, valhalla_build_extract, ...
│   ├── lib/libvalhalla*.so
│   └── include/, share/, ...
├── valhalla.json                       valhalla-deploy:valhalla
├── data/                               valhalla-deploy:valhalla
│   ├── planet.pbf
│   ├── admins.sqlite
│   ├── timezones.sqlite
│   ├── elevation/
│   ├── valhalla_tiles/                 # build output
│   ├── tiles.tar.zst                   # last successful tarball
│   └── default_speeds.json
└── last_iteration_complete             # build sentinel (mtime)

/srv/valhalla-deploy/                   valhalla-deploy:valhalla-deploy
└── .ssh/id_valhalla_deploy{,.pub}      # orchestrator key (v2 → v1)

# no /etc/sudoers.d/ files — neither valhalla nor valhalla-deploy has any
# sudoers entries on v2 (the loop owns everything it touches)
```

## systemd units

| unit | host | what |
|---|---|---|
| `valhalla-build-tiles.service` | valhalla2 | runs `scripts/build-tiles-loop.sh`. `Restart=always`, `RestartSec=60`, `StartLimitBurst=3 / StartLimitIntervalSec=600` so persistent fast failures pin it as `failed` for monitoring. **Started at end of main.yml, NOT in tiles_loop.yml's install** — see "First-deploy ordering" below. |

### First-deploy ordering invariant

The build-tiles unit's first iteration SSHes to valhalla1 as
`valhalla-deploy` (orchestrator key). That key is authorised on
valhalla1 by [deploy.yml](../roles/valhalla/tasks/deploy.yml), which
runs AFTER [tiles_loop.yml](../roles/valhalla/tasks/tiles_loop.yml) in
[main.yml](../roles/valhalla/tasks/main.yml). So if the build-tiles
unit were started inside tiles_loop.yml (`state: started` on install),
the first 3 iterations would fire before the key is authorised → all
fail with `Permission denied (publickey)` → systemd burns through
`StartLimitBurst=3` → the unit pins itself `failed` and refuses
further starts until a manual `systemctl reset-failed`.

Fix lives at the bottom of main.yml: two tasks, gated to the builder
group, that run after deploy.yml + everything else:

1. `command: systemctl reset-failed valhalla-build-tiles` —
   `changed_when: false`, idempotent (no-op on healthy units), covers
   the transition case for hosts that already hit the pre-fix wedge.
2. `systemd_service: name=valhalla-build-tiles state=started` —
   starts it now that the key is in place.

If you add another orchestrator step that runs on the builder and
needs the service-side trust path already wired (e.g. a one-shot
provisioning push), it must go AFTER this pair too — or split off
deploy.yml's `authorized_key` task into a meta dep / handler so it
fires earlier in dependency order.
| `valhalla-8000.service` | valhalla1 | runs `valhalla_service /srv/valhalla/valhalla-8000.json <vcpus>`. Worker threads = full host vcpus, no CPUQuota — see "no CPU cap" gotcha. |
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
- Letsencrypt is **self-hosted** on valhalla1, NOT via the org's
  robinson-centralised distribution. See [TLS](#tls-self-hosted) below.
- `notify: reload nginx` everywhere — zero-downtime config rolls.

## TLS (self-hosted)

valhalla1 runs its own certbot instead of receiving certs from
robinson via the org's standard distribution mechanism. The reason
isn't architectural — it's that we don't have access to deploy
robinson, so the existing flow (robinson runs certbot, SSHes back
into each consumer's `acmeclnt` account, pushes PEM+key) can't be
bootstrapped.

**The org's flow (which we DON'T use):**
[roles/nginx/templates/nginx_site_macros.jinja:40](../roles/nginx/templates/nginx_site_macros.jinja#L40) bakes a 301 redirect into every site rendered through the shared
`server()` macro:

```
rewrite ^/\.well-known/acme-challenge/(.*)$ http://{{ hostvars[groups.acme.0].acme__fqdn }}/.well-known/acme-challenge/$1 permanent;
```

That redirect is intentional: it funnels every host's ACME http-01
challenges to robinson, so robinson can run a single certbot for the
whole fleet and push the renewed certs back via the `acmeclnt`
SSH-+-`update_key` channel.

**Our divergence:**

1. [roles/valhalla/templates/nginx-api.conf.j2](../roles/valhalla/templates/nginx-api.conf.j2) and [nginx-web.conf.j2](../roles/valhalla/templates/nginx-web.conf.j2) hand-roll their HTTP `server { listen 80; }` block instead of using the macro's `http='forward'` shorthand. The hand-rolled block serves `/.well-known/acme-challenge/*` from `/var/www/letsencrypt` and 301s everything else to HTTPS. The HTTPS server block still uses the macro (`http='no', https='valhalla-{api,web}'`).

2. [roles/valhalla/tasks/tls.yml](../roles/valhalla/tasks/tls.yml) runs after [frontend.yml](../roles/valhalla/tasks/frontend.yml) and (a) installs certbot, (b) creates `/var/www/letsencrypt`, (c) drops a one-line deploy-hook at `/etc/letsencrypt/renewal-hooks/deploy/reload-nginx` (just `systemctl reload nginx`), (d) runs `certbot certonly --webroot ...` once per entry in `valhalla__acme_certificates`, (e) **symlinks** `/srv/acme-daemon/certs/<name>.{pem,key}` to `/etc/letsencrypt/live/<name>/{fullchain,privkey}.pem`, replacing the snake-oil regular files from common, (f) ensures `certbot.timer` is enabled.

3. `tls.yml` calls `meta: flush_handlers` at its top so the nginx reload queued by frontend.yml fires BEFORE certbot runs — otherwise certbot would validate against pre-frontend nginx config on first deploy.

4. valhalla2 isn't touched by tls.yml (gated to `valhalla_service` in [main.yml](../roles/valhalla/tasks/main.yml)). Whatever certs it declares in its `valhalla__acme_certificates` stay on the snake-oil placeholders dropped by common's `acme_cert_client.yml`. In practice this means whichever monitoring/admin endpoints valhalla2 exposes internally do so with snake-oil certs — no public TLS expected on v2.

**Why symlinks instead of copying:** certbot rotates files under
`/etc/letsencrypt/archive/<name>/<file><N>.pem` on each renewal and
updates the symlinks under `/etc/letsencrypt/live/<name>/` to point at
the latest. Our outer symlink in `/srv/acme-daemon/certs/` then
auto-tracks the rotation — nothing needs to be copied, only nginx
needs a reload to re-open the cert. Hence the deploy-hook is just
`systemctl reload nginx`, no file-shuffling.

**First-deploy ordering:**

| step | what happens |
|---|---|
| common (via meta dep on apt etc.) | `acmeclnt` user + `/srv/acme-daemon/{bin,certs,renew-hooks}/` set up; snake-oil PEM/key dropped as regular files at `certs/{valhalla-api,valhalla-web,...}.{pem,key}` (`force: no`) |
| nginx role (via meta dep) | nginx package installed, started with debian default config |
| frontend.yml | valhalla nginx sites rendered (custom HTTP block + macro HTTPS block); `notify: reload nginx` queued |
| tls.yml: flush_handlers | nginx reloaded → new sites live, `/.well-known/acme-challenge/` served from webroot, snake-oil cert still in use for HTTPS |
| tls.yml: certbot certonly | issues real cert into `/etc/letsencrypt/live/<name>/` |
| tls.yml: symlink tasks | snake-oil regular files at `/srv/acme-daemon/certs/<name>.{pem,key}` replaced (`force: yes`) with symlinks to the live/ tree; `notify: reload nginx` queued |
| end of play | nginx reloaded → real cert in effect |

**Cert paths on disk:**

```
/srv/acme-daemon/certs/<name>.pem   ── symlink ──>  /etc/letsencrypt/live/<name>/fullchain.pem
                                                    └── symlink (certbot-managed) ──> /etc/letsencrypt/archive/<name>/fullchain<N>.pem
/srv/acme-daemon/certs/<name>.key   ── symlink ──>  /etc/letsencrypt/live/<name>/privkey.pem
                                                    └── symlink (certbot-managed) ──> /etc/letsencrypt/archive/<name>/privkey<N>.pem
```

nginx master process opens these as root — `archive/` is `root:root 700`
by default, so worker (`www-data`) doesn't need read access there.
nginx's shared `enable_ssl()` macro still references the
`/srv/acme-daemon/certs/<name>.{pem,key}` paths it always has; the
symlinks make it ACME-mechanism-agnostic.

**Renewal:** debian's certbot package ships
`/lib/systemd/system/certbot.timer` (twice daily). `tls.yml` ensures
it's enabled. On each run, `certbot renew` checks all lineages,
renews any expiring within 30 days, rotates the live/ targets, then
fires our deploy-hook (`systemctl reload nginx`). The
`/srv/acme-daemon/certs/` symlinks transparently follow the rotation.
**No ansible run needed for renewals.**

**Vault**: `valhalla__letsencrypt_email` lives in
[group_vars/valhalla/vault.yml](../group_vars/valhalla/vault.yml) — Let's
Encrypt registration contact for cert-expiry warnings + account recovery.
Not on the public cert.

## Deploy flows

The build-tiles loop on valhalla2 is the single orchestrator. Each
iteration does, in order:

1. **v2 valhalla rebuild (SHA-gated).** Local call to
   `/srv/valhalla/scripts/deploy-valhalla.sh builder`. The script does
   `git fetch --tags origin`; if `valhalla__git_version` names a remote
   branch, checkout + `pull --ff-only` + submodule update; if HEAD
   moved, `rm -rf build`, cmake (with the builder-profile flag set),
   `make`, `make install` — all as the build user (= valhalla on v2),
   no sudo. Tag/SHA pins skip the rebuild — ansible's initial checkout
   pinned the working tree there.
2. **v1 valhalla rebuild.** Same script over SSH:
   `ssh valhalla-deploy@v1 /srv/valhalla/scripts/deploy-valhalla.sh
   service`. The `service` arg picks the service-profile cmake flags
   (`-DENABLE_SERVICES=ON`, `-DENABLE_HTTP=ON`, `-DCMAKE_PREFIX_PATH`
   for prime_server). Skipping the `systemctl restart` is deliberate —
   step 7's rolling stop/start picks up the new binary.
3. **v1 web-app rebuild.** `ssh valhalla-deploy@v1
   /srv/valhalla/scripts/deploy-web.sh`. Always tracks master; HEAD-gated.
4. **Planet refresh**: bootstrap-download `planet.pbf` if it doesn't
   exist yet (`wget --continue` + `.partial` + atomic-mv; first run on
   a fresh host is ~20 min for the full planet, resumable across
   systemd restarts), then `pyosmium-up-to-date` to apply the
   replication change-files (best-effort — failure logs a warning,
   continues with the current planet, retries next iteration). Runs
   BEFORE the tile build so the fresh OSM diff lands in this
   iteration's graph, not the next one.
5. **Build tiles** (admins-once → timezones → `valhalla_build_tiles`
   --end build → `valhalla_build_elevation --from-tiles` →
   `valhalla_build_tiles --start enhance` → `valhalla_build_extract` →
   `zstd -T0 -3` to `tiles.tar.zst` via `.partial` + atomic mv).
6. **rsync the tarball** to `valhalla-deploy@v1:tiles.tar.zst` (3
   attempts, 30s backoff; `--partial --inplace` resume the same bytes
   after a transient failure).
7. **`ssh valhalla-deploy@v1 /srv/valhalla/scripts/apply-graph.sh`** —
   `zstd -d` to `graph-{first-port}.tar.partial`, atomic `mv`, hardlink
   for the other port, then sequential `systemctl stop`/`start` per
   port with `/status` healthcheck (2s polling, 60s budget). Both
   instances always run; nginx fails over via passive health checks
   during the brief unavailability of one. Touch sentinel; loop.

There is no GHA channel and no forced-command jail. **`valhalla-deploy` owns
everything that gets built or written**: `/src/valhalla`, `/src/prime_server`,
`/srv/valhalla/{local,data,scripts}`, `/srv/valhalla/web-app`, `/var/www/valhalla`.
This is true on both hosts — same identity, same dirs, same script. The
build-tiles unit on v2 runs as `User=valhalla-deploy`; the orchestrator
SSH key lives in `valhalla-deploy`'s `$HOME=/srv/valhalla-deploy/.ssh/`;
the v1 SSH login lands as valhalla-deploy directly. The `valhalla` user
is strictly the network-facing runtime: it runs `valhalla_service` on v1
and nothing else on v2 (where it just owns `/srv/valhalla` itself as the
sgid bucket for shared-group readability). `valhalla` has **zero**
sudoers entries on either host AND can only READ the install prefix —
a `valhalla_service` RCE can't overwrite its own binary. `valhalla-deploy`'s
sudoers (v1 only) shrinks to the two inherent-to-root operations
`systemctl stop/start/restart valhalla-{ports}` and `systemctl reload nginx`,
both needed by apply-graph.sh's rolling swap; on v2 `valhalla-deploy` has
no sudoers at all (it owns everything it touches). Runtime binary discovery:
the systemd units set `Environment=LD_LIBRARY_PATH={{ valhalla__prefix }}/lib`
and use absolute `ExecStart=…/local/bin/valhalla_service`; the v2 build-tiles
unit also prepends `…/local/bin` to PATH so the loop can invoke
`valhalla_build_tiles` et al. by bare name.

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
| deploy-valhalla | `valhalla-deploy-valhalla` | `journalctl -t valhalla-deploy-valhalla -f` |
| deploy-web | `valhalla-deploy-web` | `journalctl -t valhalla-deploy-web -f` |

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

- `valhalla__graph_push_target` → the service VM's libvirt private IP.
  The builder SSHes here as `valhalla-deploy` for graph push and the
  orchestrator-driven rebuild + apply-graph triggers. Production keeps
  this at `valhalla1.openstreetmap.de` in group_vars.
- `valhalla__planet_url` → Geofabrik Liechtenstein extract (~2 MB)
  instead of the ~80 GB global planet. Exercises the same
  `valhalla_build_tiles` + admins + timezones + elevation pipeline.
  The first iteration of the build-tiles loop downloads it via
  `wget --continue` — no ansible stall.
- `valhalla__build_loop_sleep_seconds` → 300s sleep between iterations
  (vs 0 in prod). Liechtenstein iterations finish in under a minute,
  so without the sleep the loop hammers the test VM continuously.

### Things to know before testing

- **Letsencrypt**: vagrant turns the self-hosted certbot flow OFF via
  `valhalla__letsencrypt_in_use: false` in
  [host_vars/valhalla-service.yml](../host_vars/valhalla-service.yml).
  The VM has no public DNS and port 80 isn't reachable to Let's
  Encrypt's validator, so certbot would fail. nginx falls back to the
  snake-oil cert dropped by `roles/common/tasks/acme_cert_client.yml`
  — browser warnings are expected; `curl -k` from the host works.
- **Manual deploy script invocation**: the orchestrator drives
  `deploy-valhalla.sh` + `deploy-web.sh` + `apply-graph.sh` from each
  iteration. To exercise just the script logic without waiting for an
  iteration, ssh into the service VM and run them manually as
  `valhalla-deploy`.
- **Elevation**: `valhalla_build_elevation --from-tiles` is bounded by
  graph extent, so on Liechtenstein only a handful of SRTM tiles are
  fetched.
- **Single-VM standalone testing**: if you need to test only the
  service-side or only the builder-side without spinning both VMs, the
  cross-host SSH-key task (`slurp` + `delegate_to` in `deploy.yml`)
  will fail because the peer host isn't reachable. `--skip-tags`
  won't help here. Either spin both VMs, or temporarily comment out
  the `deploy.yml` slurp on the service play.
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

## Migrating an existing prod host onto the orchestrator role

Fresh hosts and vagrant boxes don't need any of this — `bootstrap.yml` +
`make valhalla` handle everything. The role isn't running anywhere in
production yet, so this section is forward-looking; treat the commands as
a sketch to refine when we actually deploy. The shape: existing prod
under the older role (GHA-deploy keys, root-installed valhalla under
`/usr/local`, `valhalla` user owning the build tree, `valhalla-graph`
account) needs ownership flips + retired-account cleanup **before**
re-running `make valhalla`, otherwise the role's git tasks abort with
`fatal: detected dubious ownership in repository`.

Both hosts (build tree now belongs to `valhalla-deploy` everywhere):

```sh
sudo chown -R valhalla-deploy:valhalla \
    /src/valhalla /src/prime_server \
    /srv/valhalla/{local,data,scripts}
sudo rm -f /usr/local/bin/valhalla_* /usr/local/lib/libvalhalla*
sudo ldconfig
```

v1-specific:

```sh
sudo chown -R valhalla-deploy:valhalla \
    /srv/valhalla/web-app /var/www/valhalla
sudo userdel -r valhalla-graph              # retired (GHA-deploy era)
sudo rm -f /etc/sudoers.d/valhalla-graph
```

v2-specific:

```sh
# The orchestrator SSH key moves from valhalla's $HOME to valhalla-deploy's.
# Ansible will regenerate it under the new path on next run; remove the old:
sudo rm -rf /srv/valhalla/.ssh
sudo rm -f /etc/sudoers.d/valhalla-build-tiles   # no longer needed
# The build-tiles unit needs to re-exec under the new User=valhalla-deploy.
# A `systemctl daemon-reload` happens automatically, but a restart is needed
# for the unit to actually run as the new identity — see the gotcha below
# about not auto-restarting mid-iteration.
```

After those, `make valhalla` runs idempotently from both hosts and
converges to the new layout. `sudo systemctl restart valhalla-build-tiles`
on v2 when you actually want the new identity / new orchestrator behavior
to kick in.

bootstrap.yml is entirely separate from any of this. It only manages
admin user accounts (via `roles/common/tasks/accounts.yml`) plus apt
upgrades — orthogonal to the valhalla role's system accounts.

## Known gotchas / non-obvious decisions

- **Both blue and green run continuously, no CPU cap.** Each instance's `valhalla_service` is told its worker-thread count = full host vcpus, and the systemd unit sets no `CPUQuota`. When both are busy the kernel scheduler fair-shares CPU between them (~50% each); during an apply-graph rolling stop/start the surviving instance can burst to the whole host, absorbing the doubled load without queueing. This is in lieu of a "currently active port" state file. Memory cost of the extra worker threads vs. half-vcpus is small (~1-2 MB stack per thread, doubles the per-instance thread budget).
- **`drain_seconds=28`** in valhalla.json means `systemctl stop` blocks ~29s. The script doesn't need extra wait logic.
- **`set -euo pipefail`** in build-tiles-iteration.sh — any pathological failure aborts the iteration; the wrapper's `set -e` propagates it; systemd sees the failure and restarts. Sentinel mtime is the monitoring signal; brief restart cycling is the secondary signal (StartLimitBurst).
- **Tarball is built in two steps**: `valhalla_build_extract` writes the uncompressed tar to `mjolnir.tile_extract` (`valhalla__extract_path`, pinned via `--mjolnir-tile-extract` in [builder.yml](../roles/valhalla/tasks/builder.yml) — without the explicit pin valhalla defaults to `/data/...` which `valhalla-deploy` can't write to, and `valhalla_build_extract` fails with `PermissionError`), then a separate `zstd -T0 -3 -f` produces `tiles.tar.zst` via the `.partial` + atomic-mv pattern. `-T0 -3` is fast compression, not max — tile data is binary and already compressible, so `-19` isn't worth the CPU.
- **`git:` tasks are `update: no` deliberately.** Both [service.yml](../roles/valhalla/tasks/service.yml) and [builder.yml](../roles/valhalla/tasks/builder.yml)'s git checkouts of valhalla (and service.yml's prime_server) use `update: no` with NO `force`. Ansible's git module with `force: yes` doesn't clean `.git/modules/<submodule>/` directories, so a partial submodule-fetch failure on one run leaves the repo wedged for all subsequent runs (`fatal: upload-pack: not our ref …`). With `update: no` the git task only fires on a fresh host, and all subsequent in-repo updates flow through `deploy-valhalla.sh`'s `git fetch + pull + submodule update`. Wedge recovery is `sudo rm -rf {{ valhalla__srcdir }}` then re-run ansible — operator-facing docs in [doc/valhalla.md "Submodule fetch fails"](../doc/valhalla.md#submodule-fetch-fails-upload-pack-not-our-ref-).
- **deploy-valhalla.sh is the sole source of truth for valhalla cmake/build/install.** No duplication: both ansible's initial-deploy tasks ([service.yml](../roles/valhalla/tasks/service.yml) + [builder.yml](../roles/valhalla/tasks/builder.yml)) and the build-tiles iteration on v2 invoke the script with the appropriate `builder`/`service` profile arg. The script SHA-gates internally via `{{ valhalla__prefix }}/.valhalla_installed_sha` (the SHA the installed binary was built from): on every invocation, compare `git rev-parse HEAD` against the marker, rebuild on mismatch, no-op exit otherwise. Handles fresh deploys, branch advances, tag/SHA-pin changes, and ansible-driven branch swaps uniformly.
- **Build-tiles uses a wrapper + iteration split so iteration edits deploy automatically.** Two scripts on v2: `build-tiles-loop.sh` is a 4-line wrapper (`while true; do build-tiles-iteration.sh; done`) that the systemd unit ExecStarts — long-lived bash process. `build-tiles-iteration.sh` does all the actual work (git, builds, tile build, rsync, apply-graph trigger, sentinel touch) and is spawned fresh each iteration, so bash re-reads it from disk every time. Net effect: edits to `build-tiles-iteration.sh` take effect on the NEXT iteration with no operator action. Edits to the (tiny, stable) `build-tiles-loop.sh` wrapper or to the systemd unit still need `sudo systemctl restart valhalla-build-tiles`, but those edits are rare. The template task deliberately doesn't notify a handler because a real-planet iteration runs for many hours and auto-restarting would throw that progress away.
- **MVT cache grows unbounded.** `valhalla_service`'s `/tile` action writes rendered vector tiles to `/srv/valhalla/mvt-cache-{port}/`, and the config sets no upper bound — under sustained tile traffic these dirs can hit many GB. Safe to wipe in place (cache is rebuildable on demand). Troubleshooting + cleanup commands in [doc/valhalla.md "Disk filling up on valhalla1"](../doc/valhalla.md#disk-filling-up-on-valhalla1-mvt-cache). Capping it via a valhalla-side flag (if one exists in the installed version) or a periodic systemd timer is a worthwhile follow-up.
- **No ufw rule restricting valhalla2's SSH to valhalla1's IP.** Admins can SSH valhalla2 directly using their normal `bootstrap.yml`-deployed keys. The intended-but-not-implemented bastion model would route admin SSH through valhalla1 via `ProxyJump`. Without a static admin source IP (or a VPN), full lockdown isn't practical — and the build-loop orchestrator is the one channel that's strictly cross-host, so it's the only thing the role's SSH wiring needs to guarantee.
- **Build-loop orchestrates rebuilds.** Step 0a/0b/0c of each iteration runs git-fetch + SHA-gated rebuild for valhalla on v2, valhalla on v1, and the web-app on v1. Branches (per `valhalla__git_version`) get `pull`ed; tags/SHAs stay frozen at whatever ansible originally checked out. Web-app always tracks master. Skipping rebuilds when HEAD hasn't moved keeps no-op iterations cheap.
- **valhalla installs to a user-writable prefix, and build identity is split from runtime identity on both hosts.** `cmake -DCMAKE_INSTALL_PREFIX={{ valhalla__prefix }}` everywhere, so `make install` runs as `valhalla-deploy` with no `sudo` and no `ldconfig` (the libs aren't in the system loader path). The runtime `valhalla` user has zero sudoers anywhere and only READ access to the prefix — a `valhalla_service` RCE on v1 can't replace its own binary, and the v2 build-tiles unit has no internet-facing surface to compromise in the first place. The role uses the same identity (`valhalla-deploy`) on both hosts for symmetry — same script, same user, same dirs. Migration steps for hosts coming from the older shape live in "Migrating an existing prod host" above.

## Munin plugins (sub-task 10)

> **Currently disabled.** The munin meta dep + the
> `include_tasks: munin.yml` line in `tasks/main.yml` + the `name: munin`
> entries in `group_vars/valhalla_{service,builder}.yml`
> `valhalla__acme_certificates` are all commented out. To re-enable, flip
> all three. The plugin templates and `tasks/munin.yml` are kept in the
> tree intentionally so re-enabling is a comment-toggle, not a re-write.

Installed via [roles/valhalla/tasks/munin.yml](../roles/valhalla/tasks/munin.yml), one
template per plugin under `roles/valhalla/templates/munin_*.{sh,py}.j2`. All
plugins land in `/etc/munin/plugins/valhalla_*` and share
`/etc/munin/plugin-conf.d/valhalla` which sets `group adm` so the
service-side plugins can read `/var/log/nginx/valhalla-api.log`.

| plugin | host | source | output |
|---|---|---|---|
| `valhalla_count` | service | nginx access log | DERIVE — req/s per endpoint (route, isochrone, matrix, tile, status, other) |
| `valhalla_latency` | service | nginx access log `rqt=` field | GAUGE — mean / p50 / p99 / max seconds over the last 5 min (`U` below 50 samples) |
| `valhalla_consumers` | service | nginx access log `client=` field | DERIVE — req/s per `valhalla__client_ids` entry (X-Client-Id classification), plus `unknown` bucket |
| `valhalla_tile_size` | builder | `stat -c %s` on planet + tarball | GAUGE — bytes for `planet.pbf` (input) and `tiles.tar.zst` (output) |

Test in vagrant: `vagrant ssh <vm> -- -T 'sudo munin-run valhalla_<plugin>'`.
`config` and bare-arg both work (config returns the graph definition, no-arg
returns the values munin would scrape).

The `valhalla_tiles/` directory deliberately isn't graphed because
`valhalla_build_extract` moves its contents into the tarball every iteration
and leaves the dir near-empty.

## Prometheus monitoring (sub-task 11)

Installed via [roles/valhalla/tasks/prometheus.yml](../roles/valhalla/tasks/prometheus.yml),
gated whole-file by `valhalla__ext_prometheus_in_use` (matches the `munin__in_use`
pattern). `valhalla__prometheus_scraper_ip` MUST be set when enabled — the
play asserts this up front rather than opening ufw rules with an empty
`from_ip`. Both vars default off / unset in
[defaults/main.yml](../roles/valhalla/defaults/main.yml); per-host opt-in is in
[group_vars/valhalla_{service,builder}.yml](../group_vars). The scraper is the
routing.earth Prometheus host (proc-server) defined separately in
[/home/nils/data/dev/routing.earth/monitoring](../../routing.earth/monitoring).

Three exporters, four scrape targets:

| target | port | host | source | what it exports |
|---|---|---|---|---|
| node_exporter | 9100 | both | apt `prometheus-node-exporter` | system metrics (CPU/mem/disk/net) |
| statsd_exporter (builder) | 9102 | builder | upstream Go binary, pinned via `valhalla__statsd_exporter_version` | `valhalla_mjolnir_*` (C++ counters) + `valhalla_mjolnir_timing_*` and `valhalla_mjolnir_build_started_at` (bash-emitted) |
| statsd_exporter (service) | 9102 | service | same binary + `/etc/prometheus/statsd-mapping.yml` | `valhalla_latency_seconds{action,service}` histogram + `valhalla_ok_total` counter (rewritten from `valhalla.<action>.info.<service>.<metric>`) |
| mtail | 9145 | service | apt `mtail` | `nginx_http_requests_total{client,endpoint,status}` from `/var/log/nginx/valhalla-api.log` |

**statsd_exporter is not packaged** on Debian Trixie — installed via
`unarchive:` from the GitHub release tarball. `creates:` makes the task
idempotent; bumping `valhalla__statsd_exporter_version` does NOT auto-upgrade
(rm the binary first).

**Mapping config lives only on the service host.** The builder's
`valhalla_mjolnir_*` are plain counters and need no mapping. The service
host's per-request `<action>.info.<service>.latency_ms` only becomes a
histogram (with `_bucket` series → `histogram_quantile()` p50/p95/p99) when
[roles/valhalla/files/statsd-mapping.yml](../roles/valhalla/files/statsd-mapping.yml)
is loaded. Without it, dashboards lose percentiles. The file is vendored from
routing.earth's monitoring repo; hand-sync when it changes (rare).

**mtail replaces nginx-lua-prometheus.** Routing.earth's
[monitoring docs](../../routing.earth/monitoring/docs/valhalla-server-setup.md)
originally recommended `nginx-lua-prometheus` + git-cloned lua modules; we
substitute mtail (apt-packaged on Trixie at 3.0.9) tailing the existing
`valhalla_log`-formatted access log. Same metric name + label set, so the
existing routing.earth scrape config and `valhalla-service.json` dashboard
work unchanged. The mtail program is at
[roles/valhalla/templates/valhalla-nginx.mtail.j2](../roles/valhalla/templates/valhalla-nginx.mtail.j2);
the systemd drop-in at
[roles/valhalla/files/mtail-override.conf](../roles/valhalla/files/mtail-override.conf)
forces port 9145 and adds `SupplementaryGroups=adm` so mtail can read
`/var/log/nginx/*.log`. Cardinality is bounded upstream: `$client_class` from
nginx's `map $http_x_client_id` allowlist (defaults to "unknown"), endpoint is
the first path segment, status is a small HTTP enum.

**Bash-emitted pipeline timings.** The C++ side covers everything inside
`valhalla_build_tiles` itself, but tar / compress / upload / reload happen
*between* valhalla invocations and are owned by
[build-tiles-iteration.sh.j2](../roles/valhalla/templates/build-tiles-iteration.sh.j2).
That script defines an `emit_metric()` helper using `nc -u -w1 localhost 8125`
and emits gauges with the `valhalla.mjolnir.timing.<phase>` prefix to match
what the C++ code uses. UDP send to nothing is silent: when monitoring is off
(no statsd_exporter listening), the packets are dropped and the script moves
on, so emission is unconditional in the template.

Emitted from bash:
- `valhalla.mjolnir.build_started_at` (epoch, gauge) — top of each iteration
- `valhalla.mjolnir.timing.build_tile_set` — wraps both `valhalla_build_tiles` passes + elevation download
- `valhalla.mjolnir.timing.tar_tile_set` — `valhalla_build_extract`
- `valhalla.mjolnir.timing.compress_tile_set` — `zstd`
- `valhalla.mjolnir.count.compressed_graph_bytes` — `stat -c %s` of the tarball
- `valhalla.mjolnir.timing.upload_tile_set` — rsync to service
- `valhalla.mjolnir.timing.reload_tile_set` — ssh trigger of apply-graph
- `valhalla.mjolnir.timing.update_osm_data` — pyosmium-up-to-date

These match the names in routing.earth's `valhalla-build.json` dashboard
(`time series` panels under "Pipeline timings").

**Handler resolution.** The valhalla role used to rely on the nginx + munin
roles' handlers (`notify: reload nginx`, `notify: restart munin-node`).
Adding `restart statsd-exporter` and `restart mtail` required a real
[roles/valhalla/handlers/main.yml](../roles/valhalla/handlers/main.yml).
The existing cross-role notifies still resolve fine — Ansible's handler
lookup is play-wide, not role-local. The build-tiles unit deliberately
has no handler; see the gotcha above.

**Coexistence with Munin.** Both run side-by-side intentionally. The
overlap (count / consumers / latency / tile_size in Munin ↔ mtail +
statsd_exporter in Prometheus) is deliberate during the transition. Munin
removal is a separate follow-up once Prometheus dashboards are confirmed
stable in production.

## Tarball download endpoint

Two files exposed under `https://<valhalla__api_hostname>/download/`,
Basic-Auth gated, on the existing `valhalla-api` TLS cert. Gated
whole-feature by `valhalla__download_in_use` (default off in
[defaults/main.yml](../roles/valhalla/defaults/main.yml)).

| URL | Backing file | Inode behaviour |
|---|---|---|
| `/download/tiles.tar` | `/srv/valhalla/graph-8000.tar` | atomic `mv` from `.partial` in apply-graph.sh — same file the valhalla_service instances mmap. |
| `/download/tiles.tar.zst` | `/srv/valhalla/graph.tar.zst` | atomic `mv` from `.partial`, produced by `cp` at the tail of apply-graph.sh. |

**Why the .zst is published, not served from $HOME.** The builder rsyncs
`tiles.tar.zst` to the deploy user's home with `--inplace`
([build-tiles-iteration.sh.j2](../roles/valhalla/templates/build-tiles-iteration.sh.j2),
the `rsync_to_service_home` function). `--inplace` modifies the existing
inode rather than writing a tempfile + rename, so an nginx-served download
racing the next push would receive corrupted bytes. Apply-graph copies the
zst to `$GRAPH_DIR` with the same `.partial` + `mv` pattern as the .tar,
giving each apply a fresh inode and isolating active downloads from the
next rsync.

**In-flight download safety.** ext4 (and any POSIX FS) keeps an unlinked
inode alive until every open FD is closed. nginx serving from the old
inode finishes the transfer with the old contents; new requests after the
`mv` see the new inode. Peak disk usage during a swap is therefore ~2×
the graph size for the duration of the longest in-flight download — fine
in practice but worth knowing.

**htpasswd.** `community.general.htpasswd` renders
`/etc/nginx/htpasswd/valhalla-download` (mode 0640, owned by
`root:www-data`). Credential comes from `group_vars/valhalla/vault.yml`
(ansible-vault) — `valhalla__download_password` must be set when
`valhalla__download_in_use` is true (frontend.yml asserts this). Single
shared cred; if multi-user is ever needed, swap to a dict + loop.

**Standalone access log.** `/var/log/nginx/valhalla-download.log`. Keeps
multi-GB transfer rows out of `valhalla-api.log`, which uses a custom
log_format tuned for routing requests and is consumed by mtail.

**No rate-limit / bandwidth cap.** The server-level `valhalla_global`
zone (500 req/s) still applies but a download is one request. Per-IP
zones are scoped to the catch-all `location /` and don't leak in.
`limit_rate` is not configured — add later if abuse appears.

## Icinga2 monitoring (sub-task 11)

valhalla1 + valhalla2 are in the `[icinga2agent]` group, picked up by
[../monitoring.yml](../monitoring.yml) which applies the
`fossgis.icinga2_*` roles. Per-host config flows through the existing
[../templates/icinga2/base.conf.j2](../templates/icinga2/base.conf.j2),
which iterates `group_names` and includes any matching
`icinga2/groups/<group>.conf.j2` (host-internal: `vars.service`,
`vars.http`, `vars.sslcert`) and `<group>-services.conf.j2` (standalone
`object Service` for custom check_commands). All four files we own:

| file | rendered into | checks |
|---|---|---|
| [../templates/icinga2/groups/valhalla_service.conf.j2](../templates/icinga2/groups/valhalla_service.conf.j2) | inside `Host "valhalla1..."` | `vars.sslcert` for `valhalla__api_hostname` + `valhalla__web_hostname`; `vars.http` for `/status` and `/`; `vars.service` for each port in `valhalla__service_ports` (systemd) |
| [../templates/icinga2/groups/valhalla_service-services.conf.j2](../templates/icinga2/groups/valhalla_service-services.conf.j2) | outside (standalone) | `check_command = "file_age"` against `valhalla__apply_sentinel_path` |
| [../templates/icinga2/groups/valhalla_builder.conf.j2](../templates/icinga2/groups/valhalla_builder.conf.j2) | inside `Host "valhalla2..."` | `vars.service` for `valhalla-build-tiles` (systemd) |
| [../templates/icinga2/groups/valhalla_builder-services.conf.j2](../templates/icinga2/groups/valhalla_builder-services.conf.j2) | outside (standalone) | `check_command = "file_age"` against `valhalla__sentinel_path` |

**file_age thresholds.** Critical = `valhalla__sentinel_max_age_hours * 3600`
seconds. Warning = 75% of that. Both pulled from
[../group_vars/valhalla/vars.yml](../group_vars/valhalla/vars.yml) (= 16h
critical, 12h warning at the current value). Built-in icinga2 ITL
`file_age` check command — no plugin install needed.

**Why the parent `[valhalla:children]` group.** `monitoring.yml` does not
include the valhalla role, so role defaults aren't loaded for its plays.
The icinga templates need `valhalla__basedir` (transitively via
`valhalla__apply_sentinel_path` / `valhalla__sentinel_path`) and
`valhalla__sentinel_max_age_hours` — both live in
`group_vars/valhalla/vars.yml` exactly so the icinga2 templates can
resolve them. Adding more shared knobs follows the same pattern.

**No HTTP rate-limit / latency probes.** The existing `vars.http`
behavior only asserts response code; latency SLOs live in Prometheus
(see sub-task 11 prometheus section above). Icinga is for liveness
binary-state, Prometheus is for histograms.

Deploy with `make monitor` (re-runs `ansible-galaxy install -r requirements.yml -f`
to refresh the icinga2 collection roles, then runs monitoring.yml against
`icinga2agent`).

## Quick "did everything land" check

```sh
ls roles/valhalla/{tasks,templates,defaults,meta,handlers}
# tasks: main.yml common.yml builder.yml service.yml web.yml frontend.yml
#        tiles_loop.yml deploy.yml munin.yml prometheus.yml
# templates: build-tiles-loop.sh.j2 build-tiles-iteration.sh.j2 apply-graph.sh.j2
#            deploy-valhalla.sh.j2 deploy-web.sh.j2 valhalla-deploy.sudoers.j2
#            nginx-valhalla.conf.j2 nginx-api.conf.j2 nginx-web.conf.j2
#            statsd-exporter.service.j2 valhalla-nginx.mtail.j2
#            munin_{count,consumers,tile_size}.sh.j2 munin_latency.py.j2
# files: statsd-mapping.yml mtail-override.conf
# defaults: main.yml
# meta: main.yml
# handlers: main.yml (restart statsd-exporter / mtail)

ls templates/icinga2/groups/valhalla_*
# valhalla_service.conf.j2  valhalla_service-services.conf.j2
# valhalla_builder.conf.j2  valhalla_builder-services.conf.j2

ls group_vars/valhalla*
# valhalla/               (parent group)
#   vars.yml              (monitoring-visible shared vars: basedir, sentinel_max_age_hours)
#   vault.yml             (ansible-vault: download_password, prometheus_scraper_ip,
#                          letsencrypt_email, users[])
# valhalla_service.yml    (valhalla1 specifics)
# valhalla_builder.yml    (valhalla2 specifics)

git status
# should show roles/valhalla/ as the bulk of new content,
# plus host_vars/valhalla{1,2}.yml, hosts.ini, site.yml, Makefile,
# group_vars/valhalla{,_service,_builder}/*.yml, templates/icinga2/groups/valhalla_*
```
