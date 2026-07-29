# Changelog

All notable changes to Education Kenya are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-29

### Added
- `MARKETPLACE.md` — canonical Frappe Cloud Marketplace "Long Description" source, free of installation commands so it passes the marketplace metadata check.
- `education` declared in `[tool.bench.frappe-dependencies]` (`pyproject.toml`) so Frappe Cloud auto-provisions the base Education app on install.

### Changed
- `[tool.bench.frappe-dependencies]` version constraints capped to `>=15.0.0,<17.0.0` for `frappe`, `erpnext`, and `education`, matching the supported v15–v16 range.
- `required_apps` in `hooks.py` switched to org/repo form (`frappe/erpnext`, `frappe/education`) for Frappe Cloud dependency resolution.
- Ignore local tooling artifacts (`graphify-out/`, `.graphifyignore`, `.mcp.json`, caches) in `.gitignore`.

### Notes
- Verified on Frappe 16.25 / Education (v17-dev) bench: `bench migrate` clean and the app test suite passing (25 tests, 0 failures).

### Foundation (prior to this release)
- CBC-aligned school management across the full 2-6-3-3 structure (ECDE, Primary, Junior Secondary, Senior Secondary) with Performance Levels (PL1–PL4) mapped from a configurable grading scale.
- Operational modules: transport (routes, vehicles, subscriptions), meals/feeding programmes, and MoE compliance (EMIS/NEMIS returns).
- Kenya-specific student data, localised fees, and a single unified Education desk (no competing app tile or second workspace).
- Automated test suite and standard fixtures for CBC curriculum, Kenya counties, and MoE return templates.

[1.0.0]: https://github.com/CoaleTech/Kenya_Education/releases/tag/v1.0.0
