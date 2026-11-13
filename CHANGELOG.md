# Changelog

All notable changes to Education Kenya are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Day Scholar / Boarder fee structures through Education's own chain (Fee Structure → Fee Schedule → Sales Invoice, no new DocType): Program Enrollment copies the student's Boarder Status into a blank Student Category (a current or future year with neither is rejected; past years may stay blank), Fee Structure requires a Student Category, and a Fee Schedule must carry its Fee Structure's category. Bill with one Fee Structure per program × category × term, a Fee Schedule with the same category, one Student Group per class, then *Create Fees*. Leave Program Enrollment `fees` empty: Education's auto-fill is dead.
- `install.seed_student_categories()` seeds the Student Categories `Day Scholar`, `Boarder`, `Quarter Boarder`, `Weekly Boarder` on install and migrate.
- Transport fares by trip type with effective dates and approved discounts (replaces the single term fee; patch `convert_transport_term_fee_to_fares`).
- Library: copies, circulation (issue/return, loan limits, fines, waiver) and draft fine invoices for students.
- Timetabling: periods, requirements, instructor availability, conflict-checked generation and publish to Course Schedule.
- Teaching preparation: scheme of work, lesson plan and layered exam-paper confidentiality with timed release.
- CBC curriculum links on Education's own records, as custom fields: `Course.cbc_learning_area`, and `Topic.cbc_level` / `cbc_strand` / `cbc_sub_strand` (pickers narrowed by level and strand; the server rejects a strand outside the level or a sub-strand outside the strand). A Scheme Week now names a `Topic` and shows that topic's strand and sub-strand (read-only, refreshed on save), replacing the free-text `strand` (no migration: the doctype has not been released).
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
- `Student.kenya_boarder_status` option `Boarder (Full)` is now `Boarder`, matching its Student Category (patch `rename_full_boarder_status` converts the options and existing students).
- A full Boarder cannot have an Active Transport Subscription; Quarter and Weekly Boarders can.
- The Fee Structure validation warning no longer implies automatic Transport or Meals components: nothing adds them, add a Fee Component. The README, BLUEPRINT, MARKETPLACE and `hooks.py` claims of automatic transport/meal fee components and mid-term proration are corrected.
- Desk navigation is now one shared Education sidebar and one Education Home. The Kenya links ship as a site-layer `Custom Sidebar` fixture on the Education module, whose rows Desk appends after Education's own, so Education upgrades still reach the sidebar. The app declares `code_only_modules = {"Frappe Education Kenya": ["Education"]}` and no longer ships a Dock, Sidebar or Workspace of its own. Previously the Kenya links were written into the archived `Workspace Sidebar`, which Desk no longer reads, so they never showed.
- The "Education Kenya" workspace is gone (its "Kenya Home" sidebar row too). Education's Home is not a standard workspace, so Desk gives it no site layer: `workspace_home.merge_home()` folds the CBC number cards, charts, shortcuts and link cards from `home.json` into Education's Home on install and on every migrate. It is idempotent (a re-run or an Education resync never duplicates a block), keeps Education's own rows, and the widgets stay `is_standard` with no hardcoded colours.
- The fixture is authoritative: it is re-imported on every migrate, so a hand-edited site-layer Education sidebar is reset to it.
- Patch `retire_runtime_navigation` removes the blocks, rows and site-created cards/charts the old code injected into the Education workspace, plus the legacy "Kenya Education" workspace.
- `/guardian` page uses the defined `--border-radius` token (`--radius` does not exist).
- Removed the app stylesheet (`education_kenya.bundle.scss`, loaded on every Desk page): none of its CBC, route, vehicle, meal, MoE or widget classes was emitted by any template, script or fixture.
- The current academic year now lives only in `Education Settings`. `Education Kenya Settings` lost `current_academic_year`, `current_term`, `term_start_date` and `term_end_date` (the term dates had no reader; `Academic Term` holds them). Patch `consolidate_academic_year_setting` copies a Kenya year or term into Education Settings when that field is empty there, then deletes the four values.
- One guardian-to-students lookup: `parent_ops.guardian_students` / `linked_students` replace three private copies in `bursary`, `library` and `portal`.
- Student Transition is now submittable: submitting is the approval (`approved_by`, `approval_date` are set and read-only), and amend/cancel are enabled. Approval syncs the Student register: a level change sets `kenya_cbc_level`; Transfer Out, Dropout and Graduation disable the student and record `date_of_leaving` and `reason_for_leaving`; a later transition re-admits a student who has a leaving date. Cancelling restores the register from the latest remaining approved transition. The `Student Transitions` number card counts submitted transitions only.
- Program Enrollment creates its transition already approved, links it through the new `program_enrollment` field, and cancels it when the enrollment is cancelled (`on_cancel` hook).
- The Kenya `Custom Sidebar` fixture now names every Education row and places Student Transition, Student Pathway Choice, CBC Pathway, CBC Track and CBC Subject Combination inside Education's Student Management section, not in a Kenya section. `tests/test_navigation.py` fails when the fixture drifts from Education's sidebar.
- Kenya settings are one page: `CBC Student Settings` is now the **Students** tab of `Education Kenya Settings` (tabs: School, Students, Finance). Patch `merge_student_settings_into_kenya_settings` moves the stored values and the child rows (program level mapping, special-needs categories, boarding types) before the old DocType is dropped. `Library Settings` stays a separate page: a Single grants write per page, and Librarians must not edit the finance defaults.
- The **Communications** tab (pledge reminder days, `Enable Pledge Reminders`, `Enable Scheduled Messages`) moved from `Education Kenya Settings` to `Education Settings`, as Custom Fields `kenya_pledge_reminder_days`, `kenya_enable_pledge_reminders`, `kenya_enable_scheduled_messages`. Patch `move_communications_settings_to_education_settings` copies the stored values across and deletes the old ones. Anyone who may edit `Education Settings` (System Manager, Education Manager) can now change them; Head Teacher and Academic Admin no longer see them.

### Removed
- Every `CBC Fee Settings` field (`billing_day_of_month`, `prorate_for_late_enrolment`, `prorate_for_early_withdrawal`, `enable_fee_waivers`, `waiver_approval_required`, `max_waiver_percentage`, `track_government_capitation`, `capitation_per_student`, `government_bursary_fund`, `auto_generate_transport_invoice`, `auto_generate_meals_invoice`): nothing read them. Patch `remove_unused_fee_settings` deletes their stored values. The `CBC Fee Settings` page itself is gone; its Fee Structure validation hook now lives in `billing.py`.

### Fixed
- A saved `CBC Learning Area` could not be opened or deleted (`Unknown column 'parent'`): its `strands` field was a Table pointing at `CBC Strand`, which is not a child table. Removed the `strands` table and the never-populated `strand_count` counter; a strand's `learning_area` link already gives the reverse list. No data migration: a Table field has no column.
- `Special Needs Categories` and `Boarding Types` (Education Kenya Settings, Students tab; formerly on `CBC Student Settings`) were Table MultiSelect fields whose child tables have only a Data field. Desk needs a Link field there, so it threw on load and showed a blank form. They are now plain Tables; stored rows are unchanged. A test checks every Table MultiSelect child in this app has a Link field.

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
