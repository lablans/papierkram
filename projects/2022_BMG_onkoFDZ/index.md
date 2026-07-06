---
# Full official title of the project
title: "Krebs-Forschungsdatenzentrum – KI-gestützte Evidenzgenerierung aus versorgungsnahen Daten Klinischer Krebsregister, GKV-Routinedaten, Klinikdaten und deren Linkage"

# Funding agency (e.g. DFG, EC, BMBF)
funder: BMG

# Call / programme name
program: BMG-Projektförderung (Zuwendung)

# Short project name / acronym
acronym: onkoFDZ

# Submitting institution (DKFZ | UMM)
institution: DKFZ

# Your role on the project (PI | Co-PI | Coordinator)
role: PI

# Lifecycle status (proposal | rejected | ongoing | finished)
status: ongoing

# Date the proposal was submitted (ISO date or ~ if not yet)
submitted: 2022-01-25

# Proposal submission deadline (~ if not applicable)
deadline: ~

# Funding decision date (~ if not yet known)
decision: ~

# Direct costs requested in EUR (excl. overhead)
amount_requested: 378568

# Project duration: calendar span and runtime in months
period: 2022–2026
runtime_months: 42

# Keywords
tags: [cancer-registry, real-world-data, record-linkage, artificial-intelligence, oncology, GKV-routine-data]

# SharePoint folder URL for project documents
sharepoint_folder: https://webcoop.inet.dkfz-heidelberg.de/sites/verbis/onkoFDZ/
---

# onkoFDZ — Krebs-Forschungsdatenzentrum

onkoFDZ builds a nationwide cancer research data centre that uses AI methods to generate evidence from real-world data. The German clinical cancer registries (Klinische Krebsregister, KKR) established since 2014 under § 65c SGB V record cancer care across the country, but their potential for transparency and evidence generation has so far been underused. The project links registry data from four federal states with other real-world sources — the certified centres of the German Cancer Society (CCCs and oncology centres) and statutory health insurance (GKV) routine data — to generate evidence for clinically relevant questions that randomised controlled trials cannot practically answer. Using colorectal cancer as an exemplar, the project combines KKR data with further care-related data, quantifies and accounts for treatment-preference effects, and answers questions (e.g. on third-line therapy of colorectal carcinoma) for which no evidence-based recommendations currently exist. The data-protection-compliant linkage and AI-based analysis methods established in the project are designed to scale to broad use and serve as a blueprint for a research infrastructure for cancer research in Germany. DKFZ (department E260, Verbundinformationssysteme) leads the data infrastructure work (data harmonisation, the bridgehead toolkit, and the pseudonymous patient list; AP 6–10).

## Project Goals

Source: `Vor_Antrag Juni2021/20210923_onkoFDZ_Vorhabenbeschreibung.pdf` (detailed project description), confirmed against the signed Antrag abstract. The goals below reflect the **original funded proposal**; the 2025 extension (onkoFDN) re-scoped the consortium focus from building permanent infrastructure toward piloting privacy-compliant linkage methods and analysing the linked data.

### Overarching research questions (whole consortium)

1. **Evidence generation** — How to generate high-quality, clinically relevant oncological evidence with AI, using linked data from multiple clinical cancer registries (KKR) combined with other real-world data: statutory-insurance (GKV) claims, hospital-certification data (Oncobox Research), comprehensive cancer centres (CCCs), and DKTK clinical/molecular data.
2. **Methods & tooling** — Which processes and tools for data harmonisation, linkage, and machine learning are required, and how to make them reusable for broad adoption.
3. **Clinical impact** — How to generate evidence for clinically relevant evidence gaps in **colorectal cancer** care.

### Consortium goals — three pillars

**A. Infrastructure (harmonisation & linkage)**
- Develop/extend processes for heterogeneous registry data, where useful via standards such as HL7 FHIR.
- Link KKR, GKV, CCC, and Oncobox Research data **at the person level** across ≥7 registries (Saxony ×4, Berlin-Brandenburg, Hesse, Bavaria).
- Evaluate multiple **privacy-preserving record-linkage (PPRL)** variants — Bloom-filter PPRL (DKTK) and a **novel Secure Multi-Party Computation (SMPC) PPRL** — and determine which fits which data holder, backed by a data-protection concept and real-world evaluation.
- Package the methods as a **reusable toolkit** (incl. the DKTK CCP "Brückenkopf" bridgehead).
- Build the workflow as a **generic, transferable platform** (other tumour entities), respecting state-specific data-protection law.
- Design and consent a **Use&Access procedure** for the wider research community.

**B. Artificial Intelligence**
- Develop ML methods (initially Random-Forest-based) for **case-level reconstruction of the primary treatment intention** and of missing information, to quantify/control "confounding by indication."
- Reconstruct **treatment preferences of individual centres** as AI-generated features.
- **Target metric:** stable, treatment-arm-balanced prediction accuracy for **≥80 % of the patient population** in internal *and* external validation.
- Establish **automated real-time reporting** to monitor new surgical techniques (e.g. robotic surgery).

**C. Use Cases (colorectal-cancer evidence)** — where the guideline gives no/unclear recommendation:
- a) Adjuvant chemo, colon cancer UICC III, age > 75 / molecular subgroups
- b) Adjuvant chemo, colon cancer UICC II
- c) Adjuvant chemo, rectal cancer after short-course radiation (5×5 Gy), post-op stage III
- d) Systemic-therapy choice by molecular-pathology subgroup & tumour location (e.g. triplet therapy)
- e) Laparoscopic vs. robotic surgery for rectal cancer

**Overarching / sustainability**
- Establish the infrastructure permanently as a **Krebs-Forschungsdatenzentrum**, with continuous open exchange with the ZfKD and the "Stage 2" actors of the cancer-registry-data merger law.
- **Systematic patient involvement** (Deutsche ILCO e.V.); an 18-month workshop with clinicians, patient reps, and the colorectal-cancer guideline group.
- **Proof of concept:** ≥1 significant, potentially **guideline-changing publication**, feeding into the Living Guideline.

### Work-package structure (23 APs, 5 groups)

- **Organisation:** AP1 Overall concept & coordination · AP2 Contracts · AP3 Dataset definition · AP4 Clinical-expertise consultation · AP5 Use&Access concept
- **Data infrastructure:** AP6 Concept phase (linkage/transfer/harmonisation) · AP7 Agreed data-protection concept · AP8 Pseudonymisation+transfer dev & operation · AP9 Data-structure workshop · AP10 Local implementation · AP11 Data provision (KKR/AOK PLUS/DKTK/DKG) · AP12 Harmonisation by ADT · AP13 ADT delivery to analysis sites
- **AI:** AP14 Feature engineering · AP15 Training & performance tests · AP16 Comparison vs. conventional statistics · AP17 Propensity-weight provision
- **Use-case analysis:** AP18 Study protocol & ethics · AP19 Statistical analysis plan · AP20 Data analysis
- **Exploitation:** AP21 Transfer to guideline programme · AP22 Result dissemination & publication · AP23 Reusable infrastructure toolkit

### DKFZ-specific goals (Prof. Dr. Martin Lablans, dept. E260)

DKFZ co-leads — with ADT (Kleihues-van Tol) — the **data transfer, harmonisation, and linkage** domain. DKFZ's funded work is **AP 6–10 (data infrastructure)**:

- **AP6** — Concept phase for linkage, transfer, and harmonisation.
- **AP7** — Develop the jointly agreed **data-protection concept** (the bottleneck that later drove the extension).
- **AP8** — Develop and operate the **pseudonymisation + transfer** pipeline.
- **AP9** — Run the workshop presenting the established data structure.
- **AP10** — **Local implementation** of pseudonymisation + data transfer at partner sites.

Concrete DKFZ deliverables (budget DKFZ sheet): **data harmonisation**, the **"Brückenkopf" (CCP bridgehead) toolkit**, and the **pseudonymous patient list**; DKFZ also contributes the **novel SMPC-PPRL** linkage method (cf. `SMPC-PPRL-Plato2.docx`).

## SharePoint Documents

Documents for ongoing projects are located under `Management/Anträge/`.

| Document | Type | File |
|---|---|---|
| Full Proposal / Antrag (signed) | PDF | Management/Anträge/onkoDKFZ_Antrag_sign.pdf |
| Budget / Kalkulation | XLSX | Management/Anträge/Kalkulation BMG KKR KI 20.01.2022_Mit_DKFZ_JS.xlsx |
| Timeline annex (Zeitplan) | DOCX | Management/Anträge/Anlage onkoFDZ Zeitplan.docx |
| Technical concept (SMPC/PPRL) | DOCX | Management/Anträge/SMPC-PPRL-Plato2.docx |
| Signature page (Unterschriftenseite, signed) | PDF | Management/Anträge/Untrerschriftenseite _OnkoFDZ_sign.pdf |
| Project extension request | PDF | Management/Anträge/Antrag Verlängerung bis 26/2025.05.19_Antrag auf Projektverlängerung_onkoFDZ.pdf |
| Extension budget (latest, _JS) | XLSX | Management/Anträge/Antrag Verlängerung bis 26/2025.05.19_Kalkulation BMG onkoFDN_16Monate_JS.xlsx |
| Extension budget (earlier version) (review label) | XLSX | Management/Anträge/Antrag Verlängerung bis 26/2025.05.19_Kalkulation BMG onkoFDN_16Monate.xlsx |
| Extension milestone changes | XLSX | Management/Anträge/Antrag Verlängerung bis 26/Änderungen Meilensteinplan Projektverlängerung_16Monate_onkoFDZ.xlsx |
| Grants office checklist | DOCX | Management/Anträge/Antrag Verlängerung bis 26/Checklist_new.docx |
| Antragsvorlage – Ausfüllhinweise (Archiv) (review label) | DOTX | Management/Anträge/Archiv/03_Anlage 2_BMG_Projektantrag-Ausfüllhinweise.dotx |
| Kooperationsvereinbarung Vorlage (Archiv) (review label) | DOTX | Management/Anträge/Archiv/06_Anlage 5_BMG_Projektantrag_KooperationsvereinbarungVerbundprojekte.dotx |
| Formantrag Lablans (Archiv) (review label) | PDF | Management/Anträge/Archiv/20220128_onkoFDZ_Formantrag_Lablans.pdf |
| EU-Beihilferelevanz Anlage (Archiv) (review label) | DOCX | Management/Anträge/Archiv/Anlage EU Beihilferelevanz.docx |
| EU-Beihilfe Erklärung (Archiv) (review label) | PDF | Management/Anträge/Archiv/EU_Beihilfe_BMG_Lablans.pdf |
| Budget 14.01.2022 (Archiv) (review label) | XLSX | Management/Anträge/Archiv/Kalkulation BMG KKR KI 14.01.2022.xlsx |
| Budget 20.01.2022 (Archiv) (review label) | XLSX | Management/Anträge/Archiv/Kalkulation BMG KKR KI 20.01.2022.xlsx |
| Budget 20.01.2022 mit DKFZ-Tabellenblatt (Archiv) (review label) | XLSX | Management/Anträge/Archiv/Kalkulation BMG KKR KI 20.01.2022_Mit_DKFZ_Tabellenblatt.xlsx |
| Formantrag signed, compressed (Archiv) (review label) | PDF | Management/Anträge/Archiv/onkoDKFZ_Formantrag_sign-komprimiert.pdf |
| Formantrag signed (Archiv) (review label) | PDF | Management/Anträge/Archiv/onkoDKFZ_Formantrag_sign.pdf |
| Formantrag Lablans draft (Archiv) (review label) | DOCX | Management/Anträge/Archiv/onkoFDZ_Formantrag_Lablans.docx |
| Formantrag Lablans draft _JS (Archiv) (review label) | DOCX | Management/Anträge/Archiv/onkoFDZ_Formantrag_Lablans_JS.docx |
| Formantrag Seite 8 (AP22/23) (Archiv) (review label) | PDF | Management/Anträge/Archiv/onkoFDZ_Formantrag_Seite8_MitAP22_23.pdf |
| Formantrag ZEGV 2022-01-14 (Archiv) (review label) | DOCX | Management/Anträge/Archiv/onkoFDZ_Formantrag_ZEGV_20220114.docx |
| Formantrag ZEGV 2022-01-20 (Archiv) (review label) | DOCX | Management/Anträge/Archiv/onkoFDZ_Formantrag_ZEGV_20220120.docx |
| Vorhabenbeschreibung 2021-09-23 (pre-proposal) (review label) | PDF | Management/Anträge/Vor_Antrag Juni2021/20210923_onkoFDZ_Vorhabenbeschreibung.pdf |
| ADT Arbeitsaufwände (pre-proposal) (review label) | DOCX | Management/Anträge/Vor_Antrag Juni2021/ADT_Arbeitsaufwände.docx |
| ADT Arbeits-/Meilensteinplan 2021-07-01 (pre-proposal) (review label) | XLSX | Management/Anträge/Vor_Antrag Juni2021/ADT_ArbeitsMeilensteinplan_onkoFDZ_20210701.xlsx |
| ADT Checkliste (pre-proposal) (review label) | PDF | Management/Anträge/Vor_Antrag Juni2021/ADT_Checkliste.pdf |
| ADT Gantt-Chart (pre-proposal) (review label) | XLSX | Management/Anträge/Vor_Antrag Juni2021/ADT_GanttChart.xlsx |
| ADT onkoFDZ Einreichung (pre-proposal) (review label) | PDF | Management/Anträge/Vor_Antrag Juni2021/ADT_onkoFDZ_Einreichung.pdf |
| ADT onkoFDZ Einreichung – Anlagen (pre-proposal) (review label) | PDF | Management/Anträge/Vor_Antrag Juni2021/ADT_onkoFDZ_Einreichung_Anlagen.pdf |
| ADT Pseudonymisierung (pre-proposal) (review label) | DOCX | Management/Anträge/Vor_Antrag Juni2021/ADT_Pseudonymisierung.docx |
| ADT Record Linkage (pre-proposal) (review label) | PPTX | Management/Anträge/Vor_Antrag Juni2021/ADT_Record Linkage.pptx |
| ADT Vorhabenbeschreibung (pre-proposal) (review label) | DOCX | Management/Anträge/Vor_Antrag Juni2021/ADT_Vorhabenbeschreibung.docx |
| RKI Datenharmonisierung slides (pre-proposal) (review label) | PPTX | Management/Anträge/Vor_Antrag Juni2021/RKI_ Datenharmonisierung.pptx |
| RKI Antrag (pre-proposal) (review label) | DOCX | Management/Anträge/Vor_Antrag Juni2021/RKI_Antrag.docx |
| RKI Datenharmonisierung (pre-proposal) (review label) | DOCX | Management/Anträge/Vor_Antrag Juni2021/RKI_Datenharmonisierung.docx |
| RKI Gantt-Chart (pre-proposal) (review label) | XLSX | Management/Anträge/Vor_Antrag Juni2021/RKI_GanttChart.xlsx |

## Key Contacts

- Project leader (Projektleiter): Prof. Dr. Martin Lablans (DKFZ, E260 — Verbundinformationssysteme)

## Notes

- Funder: Bundesministerium für Gesundheit (BMG), 53107 Bonn — Handlungsfeld „Digitalisierung", Forschungsschwerpunkt „Krebsregisterdaten zusammenführen und intelligent nutzen". Förderkennzeichen ZMI5-2522DAT14A-O (DKFZ partner Finanzplan: 2522DAT14K). Application "ANTRAG AUF GEWÄHRUNG EINER ZUWENDUNG" dated Heidelberg, 25.01.2022.
- Original funding period: 01.09.2022 – 31.08.2025 (36 months). DKFZ-application figures from the cover sheet: requested funding (Beantragte Fördermittel) 378.567,96 €; total expenses 416.424,79 € incl. ~38 k€ own contribution (Eigenanteil, ~10 %). `amount_requested` records the requested funding (no overhead/indirect line in a BMG Zuwendung).
- **Extension:** the consortium *requested* a 16-month cost-incurring extension (2025-05-19), but the funder (BMG/Projektträger, approval 22.09.2025) granted only a **6-month, cost-neutral** extension **until 28.02.2026** — hence `period: 2022–2026`, `runtime_months: 42`, and no change to `amount_requested`. (The 31.08.2026 date in the approval is the deadline for the final *Verwendungsnachweis*, not the project runtime.) On the (proposed) extension the project is being **renamed onkoFDZ → onkoFDN — Krebsforschungsdatennutzung**; the acronym is kept as onkoFDZ here to match the SharePoint folder and the original grant.
- A separate change notice exists in `Management/Bewilligungen/` — `14_2522DAT14K_ÄB Aufstockung_2025_Reinschrift.pdf` (2025-11-25), an *Aufstockung* (budget top-up) Änderungsbescheid with a new Finanzplan — not quantified here; the original DKFZ application figure is retained as `amount_requested`.
- The main `Kalkulation` XLSX is the consortium-wide budget (~2.7 M€ total across all partners: ADT Berlin, ZEGV/TUD Dresden, Institut VF Regensburg, THS Dresden, several KKR, DKTK/CCP, DKG, OnkoZert, IBSM Freiburg, ADDZ, DKFZ). The DKFZ sheet isolates the DKFZ portion (personnel 370.087 € + 10 k€ server).
