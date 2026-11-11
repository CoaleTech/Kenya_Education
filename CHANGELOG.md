# Changelog

All notable changes to Education Kenya are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Transport fares by trip type with effective dates and approved discounts (replaces the single term fee; patch `convert_transport_term_fee_to_fares`).
- Library: copies, circulation (issue/return, loan limits, fines, waiver) and draft fine invoices for students.
- Timetabling: periods, requirements, instructor availability, conflict-checked generation and publish to Course Schedule.
- Teaching preparation: scheme of work, lesson plan and layered exam-paper confidentiality with timed release.
- Fee pledges, bursary awards/allocations, payment channels and electronic collections with Bursar-only reconciliation.
- Guardian consent, scheduled messages, parent login log and a mobile-first `/guardian` self-service page.
- CBC pathways, tracks, subject combinations and guardian-submitted pathway choices with approval workflow.
- Protected Kenyan learner identifiers (KEMIS ULI, SHA number, KJSEA) on Student.
- Select-only access for each writing role on the doctypes its forms link to (`school_operations.LINK_SELECT`), so Desk link fields search and validate.
- M-Pesa Paybill ingress: Daraja C2B confirmation and validation URLs authenticated by a per-channel `?token=`, replay-safe on `TransID`, time-windowed and rate limited; receipts post under the channel's Mode of Payment, only after Bursar approval.

### Notes
- Messaging and pledge reminders are off until `Enable Scheduled Messages` / `Enable Pledge Reminders` are set; fine invoices need a default Selling Price List.
- Register `/api/method/frappe_education_kenya.collections.ingest_paybill?token=<Ingress Token>` (confirmation) and `.validate_paybill?token=<Ingress Token>` (validation) with Safaricom; set a `Mode of Payment` on each Payment Channel whose account is the channel account.
- KCB and Co-operative Bank callbacks and USSD are not implemented: provider payloads and an aggregator are still required.

### Changed
- Desk navigation is now one shared Education sidebar. The Kenya links ship as a site-layer `Custom Sidebar` fixture on the Education module, whose rows Desk appends after Education's own, so Education upgrades still reach the sidebar. The app declares `code_only_modules = {"Frappe Education Kenya": ["Education"]}` and no longer ships a Dock or Sidebar. It keeps a Workspace with CBC number cards and charts (`is_standard`, no hardcoded colours). Previously the Kenya links were written into the archived `Workspace Sidebar`, which Desk no longer reads, so they never showed.
- The fixture is authoritative: it is re-imported on every migrate, so a hand-edited site-layer Education sidebar is reset to it.
- Patch `retire_runtime_navigation` removes the blocks, rows and site-created cards/charts the old code injected into the Education workspace, plus the legacy "Kenya Education" workspace.
- `/guardian` page uses the defined `--border-radius` token (`--radius` does not exist).
- Removed the app stylesheet (`education_kenya.bundle.scss`, loaded on every Desk page): none of its CBC, route, vehicle, meal, MoE or widget classes was emitted by any template, script or fixture.
- The current academic year now lives only in `Education Settings`. `Education Kenya Settings` lost `current_academic_year`, `current_term`, `term_start_date` and `term_end_date` (the term dates had no reader; `Academic Term` holds them). Patch `consolidate_academic_year_setting` copies a Kenya year or term into Education Settings when that field is empty there, then deletes the four values.
- One guardian-to-students lookup: `parent_ops.guardian_students` / `linked_students` replace three private copies in `bursary`, `library` and `portal`.

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
