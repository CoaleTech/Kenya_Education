<p align="center">
  <img src="frappe_education_kenya/public/images/education_kenya_logo.png" alt="Education Kenya" width="80" />
</p>

<h1 align="center">Education Kenya</h1>

<p align="center">
  Kenya CBC-aligned school management for the full <strong>2-6-3-3 structure</strong>.<br/>
  Built on <a href="https://frappeframework.com">Frappe</a> + <a href="https://github.com/frappe/education">Frappe Education</a>.
</p>

<p align="center">
  <a href="#cbc-structure">CBC Structure</a> &middot;
  <a href="#how-it-works">How It Works</a> &middot;
  <a href="#installation">Installation</a> &middot;
  <a href="#configuration">Configuration</a> &middot;
  <a href="#modules">Modules</a> &middot;
  <a href="#development">Development</a> &middot;
  <a href="#contributing">Contributing</a>
</p>

<p align="center">
  <a href="https://github.com/CoaleTech/Kenya_Education/actions/workflows/ci.yml"><img src="https://github.com/CoaleTech/Kenya_Education/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <img src="https://img.shields.io/badge/tests-25%20passing-brightgreen" alt="Tests" />
  <img src="https://img.shields.io/badge/doctypes-29-blue" alt="DocTypes" />
  <img src="https://img.shields.io/badge/license-GPL--3.0-blue" alt="License" />
  <img src="https://img.shields.io/badge/Frappe-v15%20%7C%20v16-0089FF" alt="Frappe" />
</p>

---

## Overview

Education Kenya localises [Frappe Education](https://github.com/frappe/education) for Kenyan schools. It aligns assessment to the **Competency-Based Curriculum (CBC)**, automates **Ministry of Education (MoE)** returns, and adds the operational modules Kenyan schools actually run on — transport, school meals, and Kenya-specific student data.

It **extends** the base Education app in place rather than replacing it: one unified desk, one set of Student, Fee, and Enrolment records. No parallel doctypes, no second workspace.

### Key Features

- **Complete 2-6-3-3 CBC structure** — ECDE (PP1–PP2), Primary (G1–G6), Junior Secondary (G7–G9), Senior Secondary (G10–G12), with national exam checkpoints (KPSEA, KJSEA, KACSE)
- **CBC-native assessment** — base Assessment Results are auto-mapped to Performance Levels (PL1–PL4) from a configurable grading scale, on every save
- **Full curriculum hierarchy** — Learning Areas, Strands, Sub-Strands, and Learning Outcomes, shipped as standard fixtures
- **MoE compliance & reporting** — pre-configured EMIS return templates, NEMIS-compatible export, deadline reminders, and auto-generated monthly enrolment-return drafts
- **Transport management** — routes, vehicle fleet with NTSA insurance/inspection expiry checks, and term-based student subscriptions
- **Meals & food services** — NSNP-compatible feeding programmes, daily meal records, and student meal subscriptions
- **Kenya-specific student data** — UPIN and NEMIS tracking, county/sub-county/ward residence, special-needs and boarder/day-scholar classification
- **Localised fees** — CBC fee components, transport/meal fee automation, and government capitation tracking wired into the base Fee Structure
- **Single unified desk** — folds Kenya links and CBC analytics into the shared Education workspace instead of adding a competing app tile or second sidebar
- **29 DocTypes** across curriculum, student lifecycle, school operations, MoE compliance, and finance
- **25 unit tests** — all passing

---

## CBC Structure

Education Kenya covers the full Kenyan **2-6-3-3** basic-education pathway:

| Level | Grades | Duration | National Assessment |
|-------|--------|----------|---------------------|
| ECDE (Pre-Primary) | PP1–PP2 | 2 years | School-based |
| Primary | G1–G6 | 6 years | KPSEA (Grade 6) |
| Junior Secondary | G7–G9 | 3 years | KJSEA (Grade 9) |
| Senior Secondary | G10–G12 | 3 years | KACSE (Grade 12) |

Assessment is CBC-native: results are graded into **Performance Levels PL1–PL4** ("Below Expectation" → "Exceeding Expectation") resolved from a configurable grading scale, rather than percentage marks.

---

## How It Works

Education Kenya hooks into base Education DocTypes via `doc_events`:

- **Student** save → validates and normalises Kenya identifiers (UPIN, NEMIS)
- **Assessment Result** save → resolves the CBC Performance Level from the grading scale
- **Fee Structure** save → wires in transport and meal fee components
- **Program Enrollment** submit → records the student's CBC level progression

Scheduled jobs handle MoE reporting and compliance — daily deadline checks and attendance snapshots, weekly NEMIS completeness validation, monthly enrolment-return drafts, and weekly vehicle-compliance checks. CBC curriculum, Kenya counties, and MoE return templates install as **fixtures**, so the app is usable immediately after installation.

---

## Installation

### Prerequisites

- **Frappe Framework** v15+ / v16
- **ERPNext** v15+ / v16
- **Frappe Education** v15+ / v16
- **Python** 3.10+ · **MariaDB** 10.6+ · **Node.js** 18+

### Frappe Cloud (recommended)

Available on the Frappe Cloud Marketplace. Add **Education Kenya** to your site — Frappe Education and ERPNext are provisioned automatically as dependencies (declared in `required_apps`). See [MARKETPLACE.md](MARKETPLACE.md) for the full listing description.

### Self-hosted (bench)

```bash
bench get-app https://github.com/CoaleTech/Kenya_Education
bench --site your-site.local install-app frappe_education_kenya
```

Frappe Education is pulled in automatically via `required_apps`; install `education` first if you manage apps manually.

### Uninstall

```bash
bench --site your-site.local uninstall-app frappe_education_kenya
```

---

## Configuration

After installation, configure the three settings pages:

### Education Kenya Settings

School identity and MoE registration, academic year and term, module enablement flags (Transport, Meals, MoE Compliance), and default accounting accounts.

### CBC Student Settings

Required student identifiers (UPIN, NEMIS, birth certificate), special-needs categories, boarding types, and transport/meals integration.

### CBC Fee Settings

Fee components (tuition, activity, exam, development), billing automation, fee-waiver policies, and government capitation tracking.

---

## Modules

### Transport

Route definition with pickup/drop-off points, a vehicle fleet with NTSA insurance/inspection expiry tracking (weekly compliance checks), and term-based student subscriptions.

### Meals & Food Services

NSNP-compatible feeding-programme management, daily meal records with waste tracking, dietary-requirement monitoring, and government subsidy tracking.

### MoE Compliance & Reporting

Pre-configured MoE return templates (EMIS-001 to EMIS-010) and a NEMIS-compatible export workflow:

1. **Template setup** — standard templates installed as fixtures
2. **Data collection** — aggregated from Student, Assessment, Attendance, and related DocTypes
3. **Validation** — completeness checked before generation
4. **Generation** — MoE-standard Excel/CSV output
5. **Review & submit** — head teacher submits via the NEMIS portal or email
6. **Acknowledgement** — tracked with an audit trail

---

## Architecture

```
frappe_education_kenya/
├── frappe_education_kenya/
│   ├── doctype/            # 29 DocTypes: CBC curriculum, student lifecycle,
│   │                       #   transport, meals, MoE compliance, finance
│   ├── assessment.py       # CBC Performance Level mapping (grading-scale based)
│   ├── workspace_home.py   # Folds Kenya content + analytics into Education home
│   ├── install.py          # Install / migrate hooks (unified navigation)
│   ├── patches/            # Database migration patches
│   ├── public/             # Desk bundle (esbuild) + Espresso-token styles
│   ├── templates/          # Jinja templates
│   └── hooks.py            # Frappe app hooks
├── pyproject.toml
├── README.md
├── MARKETPLACE.md          # Frappe Cloud long description
├── CHANGELOG.md
└── BLUEPRINT.md            # Technical specification
```

Education Kenya declares `frappe/education` and `frappe/erpnext` as `required_apps`, extends existing DocTypes via Custom Fields (Student, Assessment Result, Fee Structure, Program), and adds new DocTypes for Kenya-specific features.

### Roles

| Role | Access |
|---|---|
| **Head Teacher** | All modules, MoE reporting, approvals |
| **Academic Admin** | CBC curriculum, assessments, student data |
| **Transport Manager** | Routes, vehicles, subscriptions |
| **Catering Manager** | Meal programmes, daily records |
| **MoE Reporter** | Read-only data access, report generation |
| **Bursar** | Fee management, transport/meal billing |

---

## Development

```bash
bench get-app education
bench get-app https://github.com/CoaleTech/Kenya_Education
bench --site dev-site.local install-app frappe_education_kenya
bench start
```

### Running Tests

The app ships a standalone runner (bench's `run-tests` eagerly imports every app's tests, which triggers an unrelated ERPNext Fiscal Year bootstrap conflict):

```bash
bench --site dev-site.local execute frappe_education_kenya.run_own_tests.run
```

25 unit tests cover assessment mapping, student transitions, MoE returns, transport compliance, and fee/student settings hooks.

---

## Contributing

Contributions from the Kenyan education-technology community are welcome.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/kenya-feature`)
3. Commit your changes
4. Push and open a Pull Request

Run `pre-commit` (ruff, eslint, prettier) before pushing — the same checks run in CI.

---

## License

GPL-3.0. See [license.txt](license.txt).

Built and maintained by **[CoaleTech](https://coale.tech)** · support@coale.tech · [github.com/CoaleTech/Kenya_Education](https://github.com/CoaleTech/Kenya_Education)
