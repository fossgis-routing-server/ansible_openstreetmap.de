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

Two relevant docs:

→ **[ai/valhalla.md](ai/valhalla.md)** — written for you (the AI agent).
Dense implementation reference: architecture, variable layout, SSH trust
paths, deploy flows, known gotchas. Read this first when working on
anything valhalla-related.

→ **[doc/valhalla.md](doc/valhalla.md)** — written for humans / maintainers.
Operations & troubleshooting playbook, common commands, vagrant
end-to-end testing recipes.

Keep both up-to-date as the role evolves. Things meant for the AI reference
(implementation invariants, why-not-X notes) go in `ai/`; things meant for
human operators (commands to run, browser-side gotchas) go in `doc/`.
