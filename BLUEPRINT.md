# Frappe Education Kenya — Technical Blueprint
## A Custom Frappe App for Kenya's Competency-Based Curriculum (CBC) and School Operations

**Version:** 1.0.0  
**Date:** July 2026  
**Target Platform:** Frappe Framework v15+ with Frappe Education dependency  
**License:** MIT

---

## 1. Executive Summary

Frappe Education Kenya (`frappe_education_kenya`) is a custom Frappe application designed to extend the open-source **Frappe Education** platform with full alignment to Kenya's **Competency-Based Curriculum (CBC)** and **Ministry of Education (MoE)** compliance requirements. The app covers the complete **2-6-3-3 education structure** (ECDE → Primary → Junior Secondary → Senior Secondary), adds operational modules for **school transport** and **meals/feeding programmes**, and provides automated **MoE reporting** and **EMIS data integration** capabilities.

The application is architected as a **separate but dependent Frappe app** that declares `frappe/education` as its upstream dependency, extending existing DocTypes via custom fields, server scripts, and introducing new DocTypes for Kenya-specific features. This approach ensures compatibility with upstream updates while providing localized functionality.

---

## 2. Kenya's Education Landscape & CBC Structure

### 2.1 The 2-6-3-3 Curriculum Architecture

Kenya transitioned from the 8-4-4 system to the **Competency-Based Curriculum (CBC)** under the **Basic Education Curriculum Framework (BECF)**. The structure is organised as follows:

| Level | Years | Grades | Age Range | MoE Classification |
|---|---|---|---|---|
| **Early Childhood Development Education (ECDE)** | 2 | Pre-Primary 1 (PP1), Pre-Primary 2 (PP2) | 4–5 years | Pre-Primary |
| **Lower Primary** | 3 | Grade 1, Grade 2, Grade 3 | 6–8 years | Primary |
| **Upper Primary** | 3 | Grade 4, Grade 5, Grade 6 | 9–11 years | Primary |
| **Junior Secondary School (JSS)** | 3 | Grade 7, Grade 8, Grade 9 | 12–14 years | Junior Secondary |
| **Senior Secondary School (SSS)** | 3 | Grade 10, Grade 11, Grade 12 | 15–17 years | Senior Secondary |

The CBC emphasises **seven core competencies**: Communication and Collaboration, Critical Thinking and Problem Solving, Imagination and Creativity, Citizenship, Learning to Learn, Self-Efficacy, and Digital Literacy. Assessment is continuous and formative, using **Performance Levels (PL)** rather than traditional percentage grades.

### 2.2 MoE Compliance & Reporting Requirements

The Ministry of Education mandates regular data submissions through the **National Education Management Information System (NEMIS/EMIS)**. Schools must report:

- **Enrolment data** by grade, gender, and special needs status
- **Teacher deployment** and qualification records
- **Infrastructure** and learning resource inventory
- **Financial returns** for public and government-subsidised schools
- **Examination and assessment results** at transition points (Grade 6 KPSEA, Grade 9 KJSEA, Grade 12 KACSE)
- **Attendance tracking** with daily and monthly aggregates

The system must generate **standardised MoE report formats** including the **NEMIS upload templates**, **termly returns**, and **annual school census** data.

### 2.3 School Operations Context

Kenyan schools, whether public (Day/Boarding), private, or faith-based, share common operational needs:

- **Fee management** with structured fee components (tuition, activity, exam, development funds)
- **Transport services** for day scholars with route-based billing
- **Meal programmes** (school feeding) with dietary tracking and per-meal costing
- **Boarding facilities** management for boarding schools
- **Co-curricular activity** tracking (sports, clubs, societies)

---

## 3. Application Architecture

### 3.1 Design Principles

The architecture follows five core principles derived from both Frappe best practices and Kenya education sector requirements:

1. **Upstream Compatibility** — The app extends rather than replaces Frappe Education, ensuring seamless updates
2. **MoE Compliance by Design** — Every data structure encodes MoE reporting requirements at the schema level
3. **CBC-Native Assessment** — Assessment models follow CBC Performance Levels, not legacy grading
4. **Operational Completeness** — Transport, meals, and boarding are first-class modules, not afterthoughts
5. **Multi-Tenancy Ready** — Supports school chains, county-level administration, and national aggregation

### 3.2 Module Structure

The application is organised into six logical modules, each mapped to a Frappe Workspace:

```
frappe_education_kenya/
├── cbc_curriculum/           # CBC-aligned curriculum & assessment
├── moe_compliance/           # MoE reporting & EMIS integration
├── school_operations/        # Transport, meals, boarding, co-curricular
├── student_lifecycle/        # Admission, progression, transition
├── finance_kenya/            # Localised fee management & reporting
└── portal_kenya/             # Parent/student portal enhancements
```

### 3.3 Integration Architecture

The app integrates with Frappe Education at multiple layers:

| Integration Point | Method | Purpose |
|---|---|---|
| **Student DocType** | Custom Fields | Add CBC-specific fields (UPIN, NEMIS ID, special needs, transfer history) |
| **Assessment Result** | Server Script Override | Map to CBC Performance Levels |
| **Program/Grade** | New DocType + Link Fields | CBC level structure |
| **Fee Structure** | Custom Fields + Server Scripts | Kenya fee components and MoE reporting |
| **Course** | Extended Model | CBC learning areas and strands |
| **Report Generation** | Custom Reports | MoE standard format reports |

---

## 4. Core Data Model

### 4.1 CBC Curriculum Model

The CBC curriculum requires a hierarchical subject model that differs significantly from traditional course-based structures. Learning is organised around **Learning Areas** (subjects), each containing **Strands**, **Sub-Strands**, and **Learning Outcomes**.

#### 4.1.1 Key DocTypes

**CBC Level** (`CBCLevel`) — Defines each level in the 2-6-3-3 structure:

| Field | Type | Description |
|---|---|---|
| `level_code` | Data | Unique code: ECDE_PP1, ECDE_PP2, PRI_G1–G6, JSS_G7–G9, SSS_G10–G12 |
| `level_name` | Data | Human-readable name |
| `education_sector` | Select | Pre-Primary / Primary / Junior Secondary / Senior Secondary |
| `years_of_study` | Int | Duration in years |
| `moef_level_code` | Data | MoE EMIS classification code |
| `is_transition_level` | Check | Whether this level has a national exam (G6, G9, G12) |
| `examination_body` | Data | KNAT/LNEC (Grade 6), KNAT (Grade 9), KNEC (Grade 12) |

**CBC Learning Area** (`CBCLearningArea`) — Subject equivalent in CBC terminology:

| Field | Type | Description |
|---|---|---|
| `learning_area_code` | Data | Unique subject code (e.g., MAT, ENG, KIS, SCI) |
| `learning_area_name` | Data | Full name (e.g., Mathematics, English Language) |
| `applicable_levels` | Table MultiSelect | Linked to CBCLevel — which levels teach this area |
| `strand_count` | Int | Number of strands |
| `is_core` | Check | Whether compulsory for all learners |
| `is_examinable` | Check | Whether assessed in national examinations |
| `learning_area_category` | Select | Languages / Sciences / Humanities / Creative Arts / Technical / Life Skills |

**CBC Strand** (`CBCStrand`) — Major division within a learning area:

| Field | Type | Description |
|---|---|---|
| `strand_code` | Data | Unique code |
| `strand_name` | Data | Descriptive name |
| `learning_area` | Link | Parent learning area |
| `level` | Link | Applicable CBC level |
| `sub_strand_count` | Int | Number of sub-strands |

**CBC Sub-Strand** (`CBCSubStrand`) — Teachable unit:

| Field | Type | Description |
|---|---|---|
| `sub_strand_code` | Data | Unique code |
| `sub_strand_name` | Data | Descriptive name |
| `strand` | Link | Parent strand |
| `suggested_activities` | Text | Suggested learning activities |
| `assessment_criteria` | Text | How competence is assessed |

**CBC Learning Outcome** (`CBCLearningOutcome`) — Specific observable competence:

| Field | Type | Description |
|---|---|---|
| `outcome_code` | Data | Unique code |
| `outcome_description` | Text | What the learner should be able to do |
| `sub_strand` | Link | Parent sub-strand |
| `performance_level_indicators` | Table | PL1–PL4 descriptors for this outcome |
| `suggested_resources` | Text | Teaching/learning resources needed |

### 4.2 Assessment & Grading Model

The CBC uses **Performance Levels (PLs)** rather than percentage grades:

| Performance Level | Descriptor | Traditional Equivalent |
|---|---|---|
| **PL1** | Exceeds Expectations | A (80–100%) |
| **PL2** | Meets Expectations | B (65–79%) |
| **PL3** | Approaches Expectations | C (50–64%) |
| **PL4** | Below Expectations | D (Below 50%) |

**CBC Assessment** (`CBCAssessment`) DocType captures this model:

| Field | Type | Description |
|---|---|---|
| `assessment_name` | Data | Name of assessment |
| `assessment_type` | Select | Formative / Summative / Diagnostic / National Exam |
| `cbc_level` | Link | Applicable level |
| `learning_area` | Link | Subject being assessed |
| `strand` | Link | Specific strand (optional) |
| `sub_strand` | Link | Specific sub-strand (optional) |
| `assessment_method` | Select | Observation / Oral / Written / Practical / Project |
| `performance_level_criteria` | Table | Rubric defining PL1–PL4 for this assessment |
| `weight_percentage` | Float | Weight towards term/annual grade |
| `assessment_period` | Link | Academic term/period |

**CBC Assessment Result** (`CBCAssessmentResult`) captures learner performance:

| Field | Type | Description |
|---|---|---|
| `student` | Link | Student reference |
| `assessment` | Link | Assessment reference |
| `performance_level` | Select | PL1 / PL2 / PL3 / PL4 |
| `competence_comment` | Text | Narrative feedback on competence |
| `teacher_remarks` | Text | Qualitative feedback |
| `assessed_by` | Link | Instructor |
| `assessment_date` | Date | Date of assessment |

### 4.3 Student Lifecycle Model

The student lifecycle in Kenya involves specific transitions and identifiers:

**Student (Extended via Custom Fields on existing Student DocType):**

| Custom Field | Type | Purpose |
|---|---|---|
| `kenya_upin` | Data | Unique Personal Identifier (UPIN) from NEMIS |
| `kenya_nemis_number` | Data | NEMIS registration number |
| `kenya_birth_certificate_no` | Data | Birth certificate number |
| `kenya_special_needs_category` | Select | None / Physical / Visual / Hearing / Intellectual / Autism / Multiple |
| `kenya_orphan_status` | Select | Not Applicable / Partial Orphan / Total Orphan |
| `kenya_boarder_status` | Select | Day Scholar / Boarder / Quarter Boarder |
| `kenya_transport_route` | Link | Assigned transport route |
| `kenya_meal_programme` | Check | Enrolled in school feeding |
| `kenya_dietary_requirements` | Text | Allergies, religious restrictions |
| `kenya_transfer_history` | Table | Previous schools, transfer dates, reasons |
| `kenya_cbc_level` | Link | Current CBC level |
| `kenya_sub_county` | Data | Sub-county of residence (for MoE zoning) |
| `kenya_county` | Link | County of residence |
| `kenya_ward` | Data | Ward (electoral area) |

**Student Transition** (`StudentTransition`) — Tracks movement between CBC levels:

| Field | Type | Description |
|---|---|---|
| `student` | Link | Student |
| `from_level` | Link | Previous CBC level |
| `to_level` | Link | New CBC level |
| `transition_type` | Select | Automatic Progression / Exam-Based / Transfer In / Transfer Out / Repeat |
| `transition_date` | Date | Effective date |
| `examination_number` | Data | KPSEA/KJSEA/KACSE number (if applicable) |
| `examination_results` | Attach | Result slip attachment |
| `approved_by` | Link | Head teacher / Principal |
| `moef_notification_sent` | Check | Whether transition was reported to MoE |

### 4.4 Transport Management Model

**Transport Route** (`TransportRoute`) — Defines a school transport route:

| Field | Type | Description |
|---|---|---|
| `route_code` | Data | Unique route identifier |
| `route_name` | Data | Descriptive name (e.g., "Route A: Ngong Road") |
| `vehicle` | Link | Assigned vehicle |
| `driver` | Link | Assigned driver |
| `pickup_points` | Table | Ordered list of pickup/drop-off points |
| `route_distance_km` | Float | Total route distance |
| `estimated_duration_minutes` | Int | Estimated trip duration |
| `term_fee` | Currency | Transport fee per term |
| `route_status` | Select | Active / Inactive / Seasonal |
| `applicable_days` | Select | All School Days / Specific Days |

**Transport Vehicle** (`TransportVehicle`):

| Field | Type | Description |
|---|---|---|
| `vehicle_registration` | Data | Number plate |
| `vehicle_type` | Select | School Bus / Van / Matatu / Other |
| `seating_capacity` | Int | Passenger capacity |
| `insurance_expiry` | Date | Insurance valid until |
| `inspection_certificate` | Attach | NTSA inspection certificate |
| `sacco_association` | Data | Transport SACCO (if applicable) |
| `gps_tracking_enabled` | Check | GPS monitoring active |
| `vehicle_status` | Select | Active / Maintenance / Retired |

**Transport Subscription** (`TransportSubscription`) — Links students to routes:

| Field | Type | Description |
|---|---|---|
| `student` | Link | Student |
| `route` | Link | Transport route |
| `pickup_point` | Link | Specific pickup point |
| `subscription_term` | Link | Academic term |
| `fee_amount` | Currency | Charged fee |
| `payment_status` | Select | Unpaid / Partially Paid / Paid / Waived |
| `subscription_status` | Select | Active / Suspended / Cancelled |

### 4.5 Meals & Food Services Model

**Meal Programme** (`MealProgramme`) — Defines a school feeding programme:

| Field | Type | Description |
|---|---|---|
| `programme_name` | Data | e.g., "Government School Feeding", "Private Catering" |
| `programme_type` | Select | Government Funded / Parent Funded / Mixed / External Provider |
| `meals_per_day` | Int | Number of meals served |
| `meal_types` | MultiSelect | Breakfast / Mid-Morning Snack / Lunch / Evening Tea / Dinner |
| `dietary_category` | Select | Regular / Special Diet / Medical / Religious |
| `term_cost` | Currency | Cost per student per term |
| `provider_name` | Data | Catering company or internal |
| `provider_contact` | Data | Contact information |

**Daily Meal Record** (`DailyMealRecord`) — Tracks actual meal service:

| Field | Type | Description |
|---|---|---|
| `record_date` | Date | Date of service |
| `meal_type` | Select | Breakfast / Lunch / Dinner / Snack |
| `menu_description` | Text | What was served |
| `students_served` | Int | Number of students who ate |
| `meals_prepared` | Int | Total meals prepared |
| `meals_wasted` | Int | Wasted/unconsumed meals |
| `cost_per_serving` | Currency | Actual cost per meal |
| `dietary_compliance` | Check | Met all dietary requirements |
| `recorded_by` | Link | Staff member |

**Student Meal Subscription** (`StudentMealSubscription`):

| Field | Type | Description |
|---|---|---|
| `student` | Link | Student |
| `meal_programme` | Link | Enrolled programme |
| `academic_term` | Link | Term |
| `included_meals` | MultiSelect | Which meals are included |
| `dietary_notes` | Text | Specific requirements |
| `subscription_fee` | Currency | Term fee |
| `payment_status` | Select | Unpaid / Partially Paid / Paid / Government Sponsored |

### 4.6 MoE Compliance Model

**MoE Return Template** (`MoEReturnTemplate`) — Defines required reports:

| Field | Type | Description |
|---|---|---|
| `template_code` | Data | MoE template identifier |
| `template_name` | Data | Report name |
| `return_type` | Select | Enrolment / Staff / Infrastructure / Financial / Examination / Attendance |
| `frequency` | Select | Daily / Weekly / Monthly / Termly / Annual / Ad-hoc |
| `due_date_rule` | Data | When submission is due |
| `data_sources` | Table | Which DocTypes/fields feed this report |
| `nemis_upload_format` | Check | Whether this generates NEMIS-compatible CSV |
| `template_file` | Attach | Official MoE template (if available) |

**MoE Return Submission** (`MoEReturnSubmission`) — Tracks actual submissions:

| Field | Type | Description |
|---|---|---|
| `template` | Link | Return template used |
| `reporting_period` | Data | e.g., "Term 1 2026" |
| `submission_date` | Date | Date submitted |
| `submitted_by` | Link | Staff member |
| `submission_method` | Select | NEMIS Portal / Email / Physical / API Upload |
| `status` | Select | Draft / Ready for Review / Submitted / Acknowledged |
| `generated_report` | Attach | The actual report file |
| `acknowledgement` | Attach | MoE acknowledgement receipt |

---

## 5. Detailed Module Specifications

### 5.1 CBC Curriculum Module

This module transforms Frappe Education's generic course/assessment model into a CBC-native system. The key architectural decision is to **map CBC Learning Areas to Frappe Education's Course DocType** while adding hierarchical strand/sub-strand/outcome tracking.

**Curriculum Mapping Strategy:**
- Each CBC Learning Area → Frappe Education `Course` (with custom fields for CBC metadata)
- Each CBC Strand/Sub-Strand → Custom child tables within the course
- Learning Outcomes → Assessable items linked to assessment plans
- Performance Level rubrics → Grading scale intervals with narrative descriptors

**Assessment Workflow:**
1. Teacher creates an `Assessment Plan` linked to a Learning Area and Strand
2. The system auto-populates applicable Learning Outcomes as assessment criteria
3. Teacher selects assessment method (observation, written, practical)
4. During assessment, teacher records Performance Level (PL1–PL4) per outcome
5. System generates narrative report with competence statements
6. Results feed into termly and annual MoE reports

**National Examination Integration:**
- Grade 6: Kenya Primary School Education Assessment (KPSEA)
- Grade 9: Kenya Junior School Education Assessment (KJSEA)
- Grade 12: Kenya Advanced Certificate of Secondary Education (KACSE)

Each examination type has a dedicated DocType capturing registration numbers, subject entries, result uploads, and analysis.

### 5.2 Transport Management Module

The transport module handles the complete lifecycle of school transport operations:

**Operational Workflow:**
1. **Route Setup** — Administrator defines routes with pickup points, assigns vehicles and drivers
2. **Student Assignment** — Students are assigned to routes based on residence; system suggests nearest route
3. **Fee Billing** — Transport fees are auto-added to student fee structures per term
4. **Daily Operations** — Driver marks attendance; GPS tracking (if enabled) records actual route adherence
5. **Safety Monitoring** — Insurance and inspection certificate expiry alerts; incident reporting
6. **Reporting** — Utilisation reports, revenue by route, cost per student

**Key Features:**
- **Route Optimisation Suggestions** — Based on student residence locations
- **Parent Notifications** — SMS/email alerts for delays, route changes
- **Term-based Billing** — Automatic prorated billing for mid-term enrolments
- **Multi-vehicle Coordination** — Fleet management for schools with multiple vehicles
- **SACCO Integration** — Links to Kenya's transport SACCO regulatory framework

### 5.3 Meals & Food Services Module

The meals module supports both government-funded and parent-funded feeding programmes:

**Operational Workflow:**
1. **Programme Setup** — Define meal types, dietary categories, providers
2. **Menu Planning** — Weekly/monthly menu with nutritional targets
3. **Student Enrollment** — Students opt-in; dietary requirements captured
4. **Daily Service** — Kitchen staff record meals served, waste, compliance
5. **Cost Tracking** — Per-meal costing, inventory consumption tracking
6. **Government Reporting** — NSNP (National School Nutrition Programme) returns

**Key Features:**
- **Dietary Compliance Monitoring** — Flags for allergies, religious requirements
- **Inventory Integration** — Links to Frappe's stock module for food supplies
- **Government Subsidy Tracking** — Records government contributions vs parent top-ups
- **Nutritional Analysis** — Basic nutrition reporting against Kenya dietary guidelines
- **Kitchen Staff Rosters** — Staff scheduling and hygiene compliance tracking

### 5.4 MoE Compliance Module

This is the critical module ensuring the school meets all statutory reporting obligations:

**Automated Report Generation:**
The system pre-configures all standard MoE returns with field mappings. When a reporting period closes, the system:

1. Aggregates data from relevant DocTypes (Student, Instructor, Assessment, Attendance, Fee)
2. Validates data completeness (flags missing NEMIS numbers, incomplete records)
3. Generates the report in MoE-specified format (Excel/CSV)
4. Provides a review interface for the head teacher
5. Tracks submission status and maintains an audit trail

**Pre-configured Reports:**

| Report Code | Report Name | Frequency | Data Sources |
|---|---|---|---|
| EMIS-001 | Enrolment by Grade and Sex | Termly | Student, CBCLevel |
| EMIS-002 | Teacher Establishment & Deployment | Annual | Instructor, CBCLevel |
| EMIS-003 | Learners with Special Needs | Termly | Student (custom fields) |
| EMIS-004 | Orphaned and Vulnerable Children | Termly | Student (custom fields) |
| EMIS-005 | Infrastructure and Facilities | Annual | Custom Infrastructure DocType |
| EMIS-006 | Examination Results Summary | Per Exam | Assessment Result |
| EMIS-007 | Financial Returns (Public Schools) | Annual | Fee, Programme |
| EMIS-008 | Daily Attendance Summary | Daily | Student Attendance |
| EMIS-009 | Boarder vs Day Scholar Ratio | Termly | Student (custom fields) |
| EMIS-010 | School Feeding Programme Returns | Termly | Daily Meal Record |

**NEMIS Integration:**
The system supports both manual export (CSV upload to NEMIS portal) and API integration (when NEMIS API becomes available). The export format follows the exact column structure required by the NEMIS bulk upload templates.

---

## 6. User Interface Design

### 6.1 Workspace Organisation

The app adds a **"Kenya Education"** workspace alongside Frappe Education's default workspaces:

**Kenya Education Workspace:**
- **CBC Curriculum** — Learning Areas, Strands, Assessments, Performance Levels
- **Students Kenya** — Student list with CBC filters, transitions, special needs
- **Transport** — Routes, Vehicles, Subscriptions, Daily operations
- **Meals** — Programmes, Menus, Daily records, Subscriptions
- **MoE Compliance** — Return templates, Submissions, NEMIS export
- **Examinations** — KPSEA, KJSEA, KACSE registration and results
- **Reports Kenya** — MoE standard reports, custom analytics

### 6.2 Role-Based Access

| Role | Permissions |
|---|---|
| **Kenya System Administrator** | Full access to all modules and configurations |
| **Head Teacher** | All academic and operational data; MoE reporting |
| **Deputy Head** | Academic data, assessments, student management |
| **Class Teacher** | Student attendance, assessments for assigned class |
| **Subject Teacher** | Assessments for assigned learning areas |
| **Bursar/Accountant** | Fee management, transport/meal billing |
| **Transport Manager** | Routes, vehicles, subscriptions |
| **Catering Manager** | Meal programmes, daily records |
| **MoE Reporter** | Read access to all data; report generation only |
| **Parent (Portal)** | Own children's data, fee payments, transport/meal status |
| **Student (Portal)** | Own academic data, timetable, assessments |

---

## 7. Implementation Phases

### Phase 1: Foundation (Weeks 1–3)
- App scaffolding and dependency setup
- CBC Level, Learning Area, Strand, Sub-Strand DocTypes
- Custom fields on Student DocType
- Kenya-specific education settings

### Phase 2: Assessment & Curriculum (Weeks 4–6)
- CBC Assessment and Assessment Result DocTypes
- Performance Level rubric system
- Integration with Frappe Education's assessment workflow
- Curriculum fixtures for all 2-6-3-3 levels

### Phase 3: Operations (Weeks 7–9)
- Transport module (Routes, Vehicles, Subscriptions)
- Meals module (Programmes, Daily records, Subscriptions)
- Fee integration for transport and meals

### Phase 4: Compliance (Weeks 10–12)
- MoE Return Template and Submission DocTypes
- Pre-configured report generation
- NEMIS export functionality
- Student Transition tracking

### Phase 5: Portal & Polish (Weeks 13–14)
- Parent portal enhancements
- Student portal CBC features
- Documentation and testing

---

## 8. Fixtures & Seed Data

The app includes comprehensive fixtures for:

1. **All CBC Learning Areas** by level (Mathematics, English, Kiswahili, Science, etc.)
2. **Performance Level Rubrics** with standard descriptors
3. **MoE Return Templates** for all standard reports
4. **Kenya Counties and Sub-counties** for geographic data
5. **Special Needs Categories** per MoE classification
6. **Sample Assessment Methods** and criteria

---

## 9. Technical Standards

- **Frappe Framework:** v15.0+
- **Python:** 3.10+
- **Node.js:** 18+
- **Database:** MariaDB 10.6+ (or PostgreSQL 14+)
- **Frappe Education Dependency:** v16.0+
- **Code Style:** Black (Python), Prettier (JavaScript)
- **Testing:** pytest with minimum 80% coverage for custom logic
- **Documentation:** Docstrings for all Python methods, README for each module

---

## 10. Appendices

### Appendix A: CBC Learning Areas by Level

**Pre-Primary (PP1–PP2):**
- Language Activities (English, Kiswahili, Indigenous)
- Mathematical Activities
- Environmental Activities
- Psychomotor and Creative Activities
- Religious Education

**Lower Primary (Grade 1–3):**
- English, Kiswahili, Indigenous Language
- Mathematics
- Environmental Activities
- Hygiene and Nutrition Activities
- Religious Education (CRE/IRE/HRE)
- Movement and Creative Activities

**Upper Primary (Grade 4–6):**
- English, Kiswahili, Home Science
- Agriculture, Science and Technology
- Mathematics, Social Studies, CRE/IRE/HRE
- Creative Arts, Physical and Health Education

**Junior Secondary (Grade 7–9):**
- English, Kiswahili, Mathematics
- Integrated Science, Social Studies, CRE/IRE/HRE
- Business Studies, Agriculture, Life Skills
- Sports and Physical Health, Creative Arts and Sports

**Senior Secondary (Grade 10–12):**
- Core: English, Kiswahili, Mathematics, Life Skills
- Arts and Sports Science pathway
- Social Sciences pathway
- Science, Technology, Engineering and Mathematics (STEM) pathway

### Appendix B: MoE EMIS Data Dictionary

Key data elements required for EMIS submissions and their mapping to DocType fields.

### Appendix C: Glossary

- **BECF** — Basic Education Curriculum Framework
- **CBC** — Competency-Based Curriculum
- **ECDE** — Early Childhood Development Education
- **EMIS** — Education Management Information System
- **JSS** — Junior Secondary School
- **KACSE** — Kenya Advanced Certificate of Secondary Education
- **KJSEA** — Kenya Junior School Education Assessment
- **KNAT** — Kenya National Assessment Test
- **KNEC** — Kenya National Examinations Council
- **KPSEA** — Kenya Primary School Education Assessment
- **LNEC** — Local National Examinations Council
- **MoE** — Ministry of Education
- **NEMIS** — National Education Management Information System
- **NSNP** — National School Nutrition Programme
- **PL** — Performance Level
- **SSS** — Senior Secondary School
- **UPIN** — Unique Personal Identification Number

---

*This blueprint serves as the authoritative reference for all implementation work. All DocType definitions, field specifications, and workflow designs documented here must be implemented exactly as specified.*
