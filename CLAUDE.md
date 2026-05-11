# CLAUDE.md

## What this repo is

The Ansible repository for the FOSSGIS Server Admin Working Group — provisioning
playbooks for the machines that host openstreetmap.de and related infrastructure.
All targets run Debian 13 (Trixie). One role per service (osrm, overpass,
valhalla, tile, wordpress, ...), wired up via `site.yml`, group/host
inventory in `hosts.ini`, and a `Makefile` with per-role convenience targets.

General setup (Ansible install, bootstrapping a new host, deploy targets)
lives in [README](README).

## Valhalla

The `valhalla` role is the most recent and complex addition. All of the
implementation context (architecture, variable layout, SSH trust paths,
deploy flows, vagrant testing, known gotchas) lives in:

→ **[doc/valhalla_ai.md](ai/valhalla.md)**

Read that first when working on anything valhalla-related. The
maintainer-facing operations / troubleshooting guide is at
[doc/valhalla.md](doc/valhalla.md). Keep that up-to-date as well.
