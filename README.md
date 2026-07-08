# Frappe Education Kenya

A custom Frappe application that extends [Frappe Education](https://github.com/frappe/education) with full alignment to Kenya's **Competency-Based Curriculum (CBC)** and **Ministry of Education (MoE)** compliance requirements. This app covers the complete **2-6-3-3 education structure** (ECDE → Primary → Junior Secondary → Senior Secondary) and adds operational modules for school **transport**, **meals/feeding programmes**, and automated **MoE reporting**.

---

## Features

### CBC Curriculum Alignment
- **Complete 2-6-3-3 level structure** — ECDE (PP1-PP2), Primary (G1-G6), Junior Secondary (G7-G9), Senior Secondary (G10-G12)
- **CBC-native assessment model** — Performance Levels (PL1–PL4) with narrative descriptors
- **Learning Areas, Strands, Sub-Strands, and Learning Outcomes** — Full curriculum hierarchy
- **National examination integration** — KPSEA (G6), KJSEA (G9), KACSE (G12)

### Transport Management
- Route definition with pickup/drop-off points
- Vehicle fleet management with NTSA compliance tracking
- Student subscriptions with term-based billing
- SACCO integration support

### Meals & Food Services
- School feeding programme management (NSNP-compatible)
- Daily meal records with waste tracking
- Dietary requirement monitoring
- Government subsidy tracking

### MoE Compliance & Reporting
- Pre-configured MoE return templates (EMIS-001 through EMIS-010)
- Automated NEMIS-compatible CSV export
- Data validation before submission
- Submission tracking with acknowledgement

### Kenya-Specific Student Data
- UPIN and NEMIS number tracking
- Special needs category classification
- Orphan status tracking
- Boarder vs day scholar status
- County, sub-county, and ward residence data

---

## Architecture

```
frappe_education_kenya/
├── cbc_curriculum/        # CBC levels, learning areas, assessments
├── student_lifecycle/     # Transitions, Kenya-specific student fields
├── school_operations/     # Transport, meals, boarding
├── moe_compliance/        # Return templates, submissions, NEMIS export
└── finance_kenya/         # Localised fee components and settings
```

The app is designed as a **separate but dependent Frappe app** that:
- Declares `frappe/education` as an upstream dependency
- Extends existing DocTypes via custom fields (Student, Assessment Result, Fee Structure, Program)
- Introduces new DocTypes for Kenya-specific features
- Provides fixtures for CBC curriculum data, Kenya counties, and MoE templates

---

## Requirements

- **Frappe Framework** v15.0+
- **ERPNext** v15.0+
- **Frappe Education** v16.0+
- **Python** 3.10+
- **MariaDB** 10.6+ (or PostgreSQL 14+)
- **Node.js** 18+

---

## Installation

### Step 1: Install Frappe Education (if not already installed)

```bash
bench get-app education
bench --site your-site.local install-app education
```

### Step 2: Install Frappe Education Kenya

```bash
bench get-app https://github.com/your-org/frappe_education_kenya
bench --site your-site.local install-app frappe_education_kenya
```

### Step 3: Configure School Settings

After installation, navigate to **Education Kenya Settings** and configure:
- School name, code, and type
- County and sub-county
- MoE registration and NEMIS codes
- Enable/disable modules (Transport, Meals, MoE Compliance)

---

## Configuration

### Education Kenya Settings

The main settings single DocType at **Education Kenya Settings** controls:
- School identity and MoE registration
- Academic year and term
- Module enablement flags
- Default accounting accounts

### CBC Student Settings

Configure at **CBC Student Settings**:
- Required student identifiers (UPIN, NEMIS, birth certificate)
- Special needs categories
- Boarding types
- Transport and meals integration

### CBC Fee Settings

Configure at **CBC Fee Settings**:
- Fee components (tuition, activity, exam, development, etc.)
- Billing automation
- Fee waiver policies
- Government capitation tracking

---

## MoE Reporting Workflow

1. **Template Setup** — Pre-configured templates are installed automatically (EMIS-001 to EMIS-010)
2. **Data Collection** — System aggregates data from Student, Assessment, Attendance, and other DocTypes
3. **Validation** — Data completeness is checked before report generation
4. **Report Generation** — Generate MoE-standard reports in Excel/CSV format
5. **Review & Submit** — Head teacher reviews, then submits via NEMIS portal or email
6. **Acknowledgement** — Track MoE acknowledgement and maintain audit trail

---

## User Roles

| Role | Access |
|---|---|
| **Head Teacher** | All modules, MoE reporting, approvals |
| **Academic Admin** | CBC curriculum, assessments, student data |
| **Transport Manager** | Routes, vehicles, subscriptions |
| **Catering Manager** | Meal programmes, daily records |
| **MoE Reporter** | Read-only data access, report generation |
| **Bursar** | Fee management, transport/meal billing |

---

## Directory Structure

```
frappe_education_kenya/
├── frappe_education_kenya/
│   ├── doctype/              # All custom DocTypes
│   │   ├── cbc_level/
│   │   ├── cbc_learning_area/
│   │   ├── cbc_strand/
│   │   ├── cbc_sub_strand/
│   │   ├── cbc_learning_outcome/   # includes Performance Level Rubric (PL1-PL4)
│   │   ├── student_transition/
│   │   ├── transport_route/
│   │   ├── transport_vehicle/
│   │   ├── transport_subscription/
│   │   ├── meal_programme/
│   │   ├── meal_type/              # + meal_type_item (Table MultiSelect master)
│   │   ├── daily_meal_record/
│   │   ├── student_meal_subscription/
│   │   ├── moe_return_template/
│   │   ├── moe_return_submission/
│   │   ├── kenya_county/
│   │   ├── kenya_sub_county/
│   │   ├── education_kenya_settings/
│   │   ├── cbc_student_settings/
│   │   └── cbc_fee_settings/
│   ├── patches/              # Database migration patches
│   ├── assessment.py         # CBC Performance Level mapping (Grading Scale based)
│   ├── workspace_home.py     # Folds Kenya content + analytics into Education home
│   ├── public/
│   │   ├── js/education_kenya.bundle.js     # Desk bundle (esbuild)
│   │   └── scss/education_kenya.bundle.scss # Espresso-token styles
│   ├── templates/            # Jinja templates
│   ├── install.py            # Installation hooks
│   └── hooks.py              # Frappe app hooks
├── pyproject.toml            # Package configuration
├── README.md                 # This file
└── BLUEPRINT.md              # Technical specification
```

---

## Development

### Setup Development Environment

```bash
bench get-app education
bench get-app frappe_education_kenya
bench --site dev-site.local install-app frappe_education_kenya
bench start
```

### Running Tests

```bash
bench --site dev-site.local run-tests --app frappe_education_kenya
```

### Code Style

- **Python**: Black formatter
- **JavaScript**: Prettier
- **Pre-commit hooks** are configured in `.pre-commit-config.yaml`

---

## Contributing

We welcome contributions from the Kenyan education technology community and beyond.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/kenya-feature`)
3. Commit your changes (`git commit -am 'Add Kenya feature'`)
4. Push to the branch (`git push origin feature/kenya-feature`)
5. Create a Pull Request

---

## License

MIT License. See [license.txt](license.txt) for details.

---

## Support

- **Documentation**: [docs.frappe.io/education](https://docs.frappe.io/education) (base Education docs)
- **Issues**: [GitHub Issues](https://github.com/your-org/frappe_education_kenya/issues)
- **Email**: dev@frappeeducationkenya.com

---

## Acknowledgements

- [Frappe Education](https://github.com/frappe/education) — The foundation ERP system
- [Frappe Framework](https://github.com/frappe/frappe) — The Python/JS framework
- Kenya Ministry of Education — For the CBC curriculum framework and EMIS specifications
- Kenya Institute of Curriculum Development (KICD) — For curriculum content guidance
