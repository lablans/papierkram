---
# Full official title of the project
title: "EUCAIM — European Federation for Cancer Images"

# Funding agency (e.g. DFG, EC, BMBF)
funder: EC

# Call / programme name
program: DIGITAL-2022-CLOUD-AI-02 (Topic DIGITAL-2022-CLOUD-AI-02-CANCER-IMAGE, DIGITAL-SIMPLE)

# Short project name / acronym
acronym: EUCAIM

# Submitting institution (DKFZ | UMM)
institution: DKFZ

# Your role on the project (PI | Co-PI | Coordinator)
role: Co-PI

# Lifecycle status (proposal | rejected | ongoing | finished)
status: ongoing

# Date the proposal was submitted (ISO date or ~ if not yet)
submitted: 2022-05-17

# Proposal submission deadline (~ if not applicable)
deadline: 2022-05-17

# Funding decision date (~ if not yet known)
decision: ~

# Direct costs requested in EUR (excl. overhead)
amount_requested: 967975

# Project duration: calendar span and runtime in months
period: 2023–2026
runtime_months: 48

# Keywords
tags: [cancer-imaging, federated-infrastructure, FAIR, artificial-intelligence, health-data, interoperability, EHDS]

# SharePoint folder URL for project documents
sharepoint_folder: https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/eucaim/
---

# EUCAIM — European Federation for Cancer Images

EUCAIM (EUropean Federation for CAncer IMages) joins 79 partners to deploy a pan-European digital federated infrastructure of FAIR, de-identified real-world cancer images. The infrastructure preserves the data sovereignty of providers and offers a platform — including an Atlas of Cancer Images — for developing and benchmarking AI tools for precision medicine. EUCAIM addresses the fragmentation of existing cancer-image repositories by building on the AI4HI initiative, European Research Infrastructures, and national/regional repositories, integrating clinical images, pathology, molecular, and laboratory data. It defines the legal grounds for pan-European operation, implements a compliant federation of providers with common data models, ontologies, quality standards, FAIR principles and de-identification procedures, and provides a dashboard for data discovery, federated search, metadata harvesting, annotation, and distributed (federated, privacy-preserving) processing. A central hub hosts the Atlas of Cancer Images to enable trustworthy AI, aligned with the European Health Data Space (EHDS) toward a sustainable flagship repository. As a partner (Co-PI), DKFZ contributes across training/evangelisation, the federated-search dashboard, de-identification, image annotation, and federated analysis.

## Project Goals

Source: `Management/Antrag/Proposal-SEP-210846135.pdf` (SEP application, Part B) and `Management/EUCAIM_DKFZ_task_descriptions.xlsx`.

### Consortium objectives

- Deploy a **pan-European federated infrastructure** of FAIR, de-identified real-world cancer images preserving provider data sovereignty.
- Build a **central hub hosting the Atlas of Cancer Images** for development and benchmarking of trustworthy AI tools.
- Define the **legal/ethical grounds (ELSI)** for pan-European operation across differing national clinical-data regimes.
- Establish **common data models, ontologies, quality standards, FAIR principles, and de-identification** procedures across a compliant federation of providers.
- Provide a **dashboard** for data discovery, federated search, metadata harvesting, annotation, and distributed processing (incl. federated & privacy-preserving learning).
- Support **new providers** in joining the federation, monitor the distributed infrastructure, and align with **EHDS** toward sustainability.

Total eligible cost of EUCAIM: **€35,579,685.17** (€17,789,829.02 requested EC contribution, 50 % funding rate). Financial support to third parties: 18 open-call grants à €200k (€3.6M, via coordinator EIBIR).

### DKFZ tasks (partner contribution)

**Multiple DKFZ departments are involved.** The DKFZ budget funds five positions across four divisions (177 PM total); the work-package allocation is:

| Department | Position | FTE | PM | Direct cost | Work packages (PM) |
|---|---|---|---|---|---|
| Radiology | Radiologist (Ä1-2) | 0.5 | 36 | €148,950 | WP2 (36) |
| Radiology | Coordinator (E13) | 1.0 | 42 | €270,900 | WP2 (42) |
| **Federated Information Systems (E260)** | PostDoc (E13) | 1.0 | 33 | €212,850 | **WP4 (15), WP5 (18)** |
| Medical Image Computing (E230) | PostDoc (E13) | 1.0 | 33 | €212,850 | WP5 (21), WP6 (12) |
| Radiooncology/Radiobiology (E220) | PostDoc (E13) | 0.5 | 33 | €106,425 | WP5 (16.5) |

**Federated Information Systems (E260) — Prof. Lablans' department** funds **1.0 FTE PostDoc (E13), 33 PM** (Year 1 = 12, Year 2 = 12, Year 3 = 9, Year 4 = 0; FTE 4-year equivalent 0.6875), direct cost **€212,850** (+7% overhead €14,899.50 = €227,749.50 total). Its 33 PM are allocated to **WP4 (15 PM)** and **WP5 (18 PM)** — i.e. the EUCAIM Dashboard / BBMRI Sample Locator (T4.3), de-identification via Mainzelliste (T5.3.3), and federated search via Bridgehead + Sample Locator/Lens (T5.6). This is DKFZ's E260-led contribution to the federation infrastructure.

#### E260 (Federated Information Systems) key contributions

E260's 33 PM fund the federation-infrastructure work in **WP4 and WP5**:

- **WP4 Central Hub — T4.3 EUCAIM Dashboard:** provide the software behind the **BBMRI Sample Locator** for making distributed data findable, running feasibility queries, and introducing a data-transfer process; deliver the EUCAIM-specific adaptations and BBMRI integration.
- **WP5 Data federation & interoperability:**
  - **T5.3.3 De-identification** — provide the **Mainzelliste** pseudonymisation software and E260's experience in setting up complex pseudonymisation services for federated networks, supporting EUCAIM's own service design/implementation.
  - **T5.6 Interoperability with existing data infrastructures** — provide **federated search via the Bridgehead + Sample Locator (Lens)** technology, adding interoperability with Beacon-based search infrastructures.
  - **T5.2 Common Data Model / interoperability** — expertise on data models for federated use (FHIR and adapters) and linking existing standards for EUCAIM.

#### Other DKFZ departments' key contributions

- **Radiology (WP2 — Engagement & liaison of data providers):** **lead-coordination of training** (four teams: legal/ethical, interoperability, governance, clinical) and **evangelisation** (T2.2); requirements analysis (T2.1), FAIR implementation support (T2.4), and **lead-coordination of data-population monitoring** incl. the monitoring dashboard (T2.5); joint actions with TEF-Health. (Travel budget: evangelisation trips.)
- **Medical Image Computing / E230 (WP5 + WP6):** **T5.3.4 Image annotation** — MITK Workbench, nnU-Net, nnDetection; **T5.4.1 metadata management** incl. **kaapana.ai**; **WP6** — federated learning/analysis infrastructure based on **kaapana.ai** (T6.1) and the EUCAIM analysis toolbox / AI components (T6.2).
- **Radiooncology/Radiobiology / E220 (WP5, 16.5 PM):** contribution to the WP5 data pre-processing / interoperability tasks.

> Note: the DKFZ budget gives PM **per department per work package**; task-level detail comes from the DKFZ-wide `EUCAIM_DKFZ_task_descriptions.xlsx`. Mapping specific tasks to specific departments above combines the WP allocation with technology ownership (Mainzelliste & Sample Locator/Bridgehead → E260; MITK/nnU-Net/kaapana.ai → Medical Image Computing E230). Note also that the budget allocates **0 PM to WP1** — project-management/coordination tasks (T1.1–T1.4) are covered at management level, not by dedicated funded effort.

## SharePoint Documents

⚠️ Layout deviation: for an `ongoing` project the expected document base is `Management/Anträge/`. EUCAIM instead uses `Management/Antrag/` (singular) plus loose files directly under `Management/` and the grant under `Management/Bewilligung/`. Paths below reflect the actual layout.

| Document | Type | File |
|---|---|---|
| Full Proposal (SEP, Part A + Part B) | PDF | Management/Antrag/Proposal-SEP-210846135.pdf |
| Grants office checklist (DKFZ) | PDF | Management/Antrag/Checkliste_DKFZ.pdf |
| Grant Agreement (101100633) | PDF | Management/Bewilligung/Grant Agreement-101100633-EUCAIM.pdf |
| DKFZ Budget planning | XLSX | Management/DKFZ EUCAIM Budgetplanung.xlsx |
| DKFZ Task descriptions | XLSX | Management/EUCAIM_DKFZ_task_descriptions.xlsx |
| DKFZ Contacts | XLSX | Management/DKFZ-Kontakte_EUCAIM.xlsx |
| Call fiche (DIGITAL-2022-CLOUD-AI-02) | PDF | Management/Antrag/Vorarbeiten/call-fiche_digital-2022-cloud-ai-02_en.pdf |
| Checklist EUCAIM (draft) | DOCX | Management/Antrag/Vorarbeiten/Checklist_EUCAIM.docx |
| DKFZ Budget planning (draft) | XLSX | Management/Antrag/Vorarbeiten/DKFZ EUCAIM Budgetplanung.xlsx |
| Partner Details Form | DOCX | Management/Antrag/Vorarbeiten/EUCAIM_Partner Details Form_DEF.docx |
| Partner contributions to WPs | PDF | Management/Antrag/Vorarbeiten/PARTNER CONTRIBUTIONS TO WPs.docx.pdf |
| Grant-office meeting note 2022-05-05 | DOCX | Management/Antrag/Vorarbeiten/2022-05-05_Gesprächnotiz_grant office.docx |
| Grant-office meeting note 2022-05-09 | DOCX | Management/Antrag/Vorarbeiten/2022-05-09_Gesprächsnotiz_grant office.docx |
| Dept-heads/grant-office/budget note 2022-05-10 | DOCX | Management/Antrag/Vorarbeiten/2022-05-10_Gesprächsnotiz_departmenthheads_grant-office_budget.docx |

## Key Contacts

## Notes

- Funder: European Commission — **DIGITAL Europe Programme**, grant **101100633**, DIGITAL-AG (Budget-Based). Coordinator: **EIBIR** (European Institute for Biomedical Imaging Research).
- **Duration:** GA fixed start **1 January 2023**, 48 months → ends **31 December 2026** (`period: 2023–2026`).
- **`amount_requested` = DKFZ direct costs €967,975** (personnel €951,975 + travel €16,000); 7 % overhead (€67,758) excluded per convention. DKFZ total incl. overhead: €1,035,733.25.
- Consortium: **79 partners**; total eligible €35.58M, EC contribution €17.79M.
- DKFZ divisions involved: Radiology, Federated Information Systems (E260), Radiooncology/Radiobiology, Medical Image Computing.
