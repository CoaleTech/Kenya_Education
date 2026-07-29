# Education Kenya

Kenya CBC-aligned school management for **the full 2-6-3-3 education structure**, built on Frappe + Frappe Education.

Education Kenya localises Frappe Education for Kenyan schools: it aligns assessment to the Competency-Based Curriculum (CBC), automates Ministry of Education (MoE) returns, and adds the operational modules Kenyan schools actually run on — transport, school meals, and Kenya-specific student data. It extends the base Education app in place rather than replacing it, so schools keep one unified desk and one set of student, fee, and enrolment records.

> This file is the canonical **Frappe Cloud Marketplace "Long Description"** source. It deliberately contains **no installation commands** (no `get-app`, `install-app`, or migration commands), which the marketplace metadata check rejects. Paste it into the listing's Long Description field, or sync the listing from it.

## Key Features

- **Complete 2-6-3-3 CBC structure** — ECDE (PP1–PP2), Primary (G1–G6), Junior Secondary (G7–G9), Senior Secondary (G10–G12), with national exam checkpoints (KPSEA, KJSEA, KACSE)
- **CBC-native assessment** — base Assessment Results are auto-mapped to Performance Levels (PL1–PL4) from a configurable grading scale, with no parallel assessment doctypes
- **Full curriculum hierarchy** — Learning Areas, Strands, Sub-Strands, and Learning Outcomes, shipped as standard fixtures
- **MoE compliance & reporting** — pre-configured EMIS return templates, NEMIS-compatible export, deadline reminders, and auto-generated monthly enrolment return drafts
- **Transport management** — routes, vehicle fleet with NTSA insurance/inspection expiry checks, and term-based student subscriptions
- **Meals & food services** — NSNP-compatible feeding programmes, daily meal records, and student meal subscriptions
- **Kenya-specific student data** — UPIN and NEMIS tracking, county/sub-county/ward residence, special-needs and boarder/day-scholar classification
- **Localised fees** — CBC fee components, transport/meal fee automation, and government capitation tracking wired into the base Fee Structure
- **Single unified desk** — folds Kenya links and CBC analytics into the shared Education workspace instead of adding a competing app tile or second sidebar
- **29 DocTypes** across curriculum, student lifecycle, school operations, MoE compliance, and finance
- **Automated test suite** — 25 unit tests, all passing

## How It Works

Education Kenya hooks into base Education DocTypes via `doc_events`. On **Student** save it validates and normalises Kenya identifiers (UPIN, NEMIS); on **Assessment Result** save it resolves the CBC Performance Level from the grading scale; on **Fee Structure** save it wires in transport and meal components; on **Program Enrollment** submit it records the student's CBC level progression. Scheduled jobs handle MoE reporting — daily deadline checks and attendance snapshots, weekly NEMIS completeness validation, monthly enrolment-return drafts, and weekly vehicle-compliance checks. CBC curriculum, Kenya counties, and MoE return templates install as fixtures, so the app is usable immediately after installation.

## Installation

Available on the Frappe Cloud Marketplace. Frappe Education (and ERPNext) are provisioned automatically as dependencies.

## License

MIT
