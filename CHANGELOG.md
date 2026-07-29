# Changelog

All notable changes to Education Kenya are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-07-29

Frappe Cloud Marketplace readiness, aligned to the CoaleTech app conventions.

### Added
- `MARKETPLACE.md` — canonical Frappe Cloud Marketplace "Long Description" source, free of installation commands so it passes the marketplace metadata check.
- `education` declared in `[tool.bench.frappe-dependencies]` so Frappe Cloud auto-provisions the base Education app on install.
- GitHub Actions workflows: server tests on Frappe v16 (`ci.yml`) and pre-commit linters (`linters.yml`).
- README status badges (CI, tests, DocTypes, license, Frappe version) and a payroll_africa-style layout with centered header, navigation, and module sections.

### Changed
- Aligned publisher, author, and copyright to **CoaleTech** (`support@coale.tech`) across `hooks.py` and `pyproject.toml`.
- Relicensed to **GPL-3.0** (matching the base Education/ERPNext apps and the CoaleTech app suite): `hooks.py`, `pyproject.toml`, and `license.txt` (full GPL-3.0 text).
- `required_apps` switched to org/repo form (`frappe/erpnext`, `frappe/education`) for Frappe Cloud dependency resolution.
- `frappe-dependencies` version constraints capped to `>=15.0.0,<17.0.0` for `frappe`, `erpnext`, and `education`.
- Ignore local tooling artifacts (`graphify-out/`, `.graphifyignore`, `.mcp.json`, caches) in `.gitignore`.

### Verified
- On Frappe 16.25 / Education bench: `bench migrate` clean and the app test suite passing (25 tests, 0 failures).

## Foundation

The pre-1.0 work that this release builds on:

### Added
- CBC-aligned school management across the full 2-6-3-3 structure (ECDE, Primary, Junior Secondary, Senior Secondary) with Performance Levels (PL1–PL4) mapped from a configurable grading scale.
- Operational modules: transport (routes, vehicles, subscriptions), meals/feeding programmes, and MoE compliance (EMIS/NEMIS returns).
- Kenya-specific student data, localised fees, and a single unified Education desk (no competing app tile or second workspace).
- Automated test suite and standard fixtures for CBC curriculum, Kenya counties, and MoE return templates.

[Unreleased]: https://github.com/CoaleTech/Kenya_Education/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/CoaleTech/Kenya_Education/releases/tag/v1.0.0
