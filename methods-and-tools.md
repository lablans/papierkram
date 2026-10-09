# Methods and tools — DKFZ federated infrastructure (Samply / VerbIS)

Capability inventory of the tools we contribute to proposals and implementation plans.
For each: what it does, (ideally unique) selling points, limitations a critical reviewer
will raise, and pointers. **Prefer pointers over repetition**: versions, release dates,
site counts, stars and pulls go stale — look them up with the commands in
[Live facts](#live-facts--how-to-look-them-up) instead of copying them into a proposal.

Status labels: **production** (in use on real data in ≥1 network), **pilot** (deployed,
limited use), **prototype** (code exists, no real deployment), **gap** (claimed or
desirable, not in code).

## Stack at a glance

```
Lens (UI) ─▶ Spot (central gateway) ─▶ Beam.Proxy ─▶ Beam.Broker (+ Vault PKI)
             Prism (cached facet counts)                  ▲ outbound HTTPS only
                                                          │
Site "Bridgehead":  Beam.Proxy ─▶ Focus ─▶ Blaze (FHIR R4 + CQL) | Postgres (named SQL)
                                         | EUCAIM CDM SQL / API | Beacon v2 | external "omop" mediator
  optional modules: Exporter, DataSHIELD/Opal via Beam.Connect, DNPM:DIP, ID management
  (Mainzelliste/MAGICPL), Directory Sync, TransFAIR ETL, data-quality agent
Central ops: secret-sync (OIDC clients, config-repo tokens), beam-cert-ui (PKI), monitoring

Prospective research (DataCastle): enrollment UI ─▶ Mainzelliste (PID, consent)
  EDC (REDCap) + uploader (DICOM de-id) + forager connectors ─▶ DataVault ─▶ keep portals (PI View)
```

---

## 1. Samply.Beam — distributed communication & security layer

**Status:** production (BBMRI-ERIC, GBN, DKTK/CCP, DHKI and others — see `bridgehead/*/vars`;
EUCAIM via its own Kubernetes manifests and [rusthead](https://github.com/samply/rusthead)).

**What it does**
- Content-agnostic task broker for networks that allow **outbound connections only**:
  central Broker + Vault PKI; one Beam.Proxy per site shared by many local apps;
  hierarchical addresses `app.proxy.broker`.
- Task → claim → result messaging with TTL and failure strategy; long-polling or SSE.
- **Mandatory end-to-end encryption and signing** (XChaCha20-Poly1305, per-recipient
  RSA-OAEP key wrapping) — the broker cannot read payloads.
- Optional encrypted **sockets** for bulk data / streams.
- Works through site HTTPS forward proxies and TLS-intercepting proxies.

**Apps built on Beam**

| App | Function | Pointer |
|---|---|---|
| beam-connect | HTTP(S) tunnelling over Beam (forwarder/receiver, per-target ACL) — transport for DataSHIELD and DNPM:DIP | [samply/beam-connect](https://github.com/samply/beam-connect) |
| secret-sync | Central provisioning of **OIDC clients** (Keycloak, Authentik; per-site groups, secret rotation) and short-lived read-only **GitLab tokens** for site config repos; runs at every Bridgehead start | [samply/secret-sync](https://github.com/samply/secret-sync), [secret-sync-deploy](https://github.com/samply/secret-sync-deploy) |
| secret exchange | *TODO: pointer missing — not located in samply org* | |
| DataSHIELD "in a box" | Bridgehead `ccp` module: Opal + Rock R server + dsCCPhos, Opal reached cross-site via beam-connect (no inbound ports), data loaded by Exporter; token-manager for Opal tokens; Data Science Orchestrator | `bridgehead/ccp/modules/datashield.md`, [token-manager](https://github.com/samply/token-manager), [DSO paper](https://doi.org/10.3233/shti250438) |
| beam-file / file-dispatcher | File transfer (Exporter → beam-file → researcher workspace); needs sockets build | [beam-file](https://github.com/samply/beam-file), [file-dispatcher](https://github.com/samply/file-dispatcher) |
| beam-enroll / beam-cert-ui | Site-side key + CSR generation (private key never leaves site); central invite/OTP portal, Vault signing, auto-renewal | [beam-enroll](https://github.com/samply/beam-enroll), [beam-cert-ui](https://github.com/samply/beam-cert-ui) |
| beam-sel | MainSEL SMPC record linkage across firewalls | [beam-sel](https://github.com/samply/beam-sel) |
| dnpm-broker-connector | DNPM:DIP site routing over beam-connect | [dnpm-broker-connector](https://github.com/samply/dnpm-broker-connector) |

**Selling points**
- Zero inbound ports at sites, yet bidirectional and E2E-encrypted. Compare: DSF needs an
  inbound mTLS FHIR endpoint per site ([network setup](https://dsf.dev/explore/concepts/network-setup));
  vantage6 payload encryption is optional per collaboration
  ([CVE-2024-22193](https://nvd.nist.gov/vuln/detail/CVE-2024-22193)); HDR UK Bunny/RQUEST is
  outbound polling but Basic-auth over TLS, no message-level crypto, OMOP-only.
- **Machine authentication is Beam's job, not the AAI's.** Sites and central services
  authenticate through Beam's PKI and signed, E2E-encrypted messages; per-app API keys
  authorise local apps. A user AAI (e.g. LS Login) covers humans only.
- **One transport for many workloads**: feasibility counts, file transfer, HTTP tunnelling
  (DataSHIELD, DNPM), SMPC linkage — one proxy, one security review per site.
- Automated PKI lifecycle (site-generated keys, auto-renewal) and secret rotation.
- Reused outside DKFZ: EUCAIM deploys it on Kubernetes ([EUCAIM/k8s-deployments](https://github.com/EUCAIM/k8s-deployments/tree/main/federated-search)).

**Limitations to address**
- Broker state is in memory; single broker per network, no HA/federation — in-flight tasks
  are lost on restart. Position as "stateless relay; durability is the app's job".
- No tagged releases (versions only in `CHANGELOG.md`), no SECURITY.md, no paper, no
  third-party audit of Beam itself.
- Small core team (bus factor) — budget a second Rust maintainer.
- No Python/Java SDK; `beam-lib` (Rust) not on crates.io; app-level OAuth2 on roadmap only.
- Interactive/stream workloads (Flower gRPC, DataSHIELD sessions) via sockets/beam-connect:
  DataSHIELD is proven in CCP, others untested.

**Pointers:** [samply/beam](https://github.com/samply/beam) (README = spec),
[beam-deploy](https://github.com/samply/beam-deploy).

---

## 2. Samply.Focus — site query agent

**Status:** production.

**What it does**
- Pulls tasks from the local Beam.Proxy, translates, executes, obfuscates, replies.
- Back-ends via `ENDPOINT_TYPE` (`src/config.rs`): `blaze`, `sql`, `blaze-and-sql`, `omop`,
  `eucaim-api`, `eucaim-sql`, `eucaim-beacon`. **One back-end type per instance**
  (only `blaze-and-sql` combines two) — no cross-backend join.
- Lens AST → CQL via per-project "flavours" (bbmri, miabis, dktk, cce, dhki, nngm, itcc, pscc).
- SQL: only pre-registered named queries (allowlist, compiled in); PostgreSQL only.
- **Beacon v2 client** exists (`src/eucaim_beacon.rs`) but with hard-coded EUCAIM imaging
  category/criterion maps — not a generic or genomic Beacon adapter.
- **`omop` is a pass-through**: POSTs the AST to an external, site-built "query mediator"
  (`src/main.rs`, `EndpointType::Omop`). There is **no OMOP-CDM translator in Focus**.
- Laplace-noise obfuscation with per-stratifier sensitivity ([laplace-rs](https://github.com/samply/laplace-rs)),
  rounding, small-count handling, per-project opt-out; 24 h result caching.
- Pass-through of export tasks to [Samply Exporter](https://github.com/samply/exporter).

**Selling points**
- Translation happens at the site from one abstract query (AST) — the network speaks one
  model while sites run FHIR/CQL, SQL, Beacon or a custom API.
- Auditable SQL path (named queries only).
- Differential-privacy-style obfuscation built in (Bunny: rounding + suppression only).

**Limitations to address**
- **OMOP is new work**: AST → OMOP-CDM SQL (Athena concept mapping, `person`/`condition_occurrence`/
  `measurement`/`specimen`), stratified output, more SQL dialects, health check. Do not cite
  the existing flag as OMOP support. HDR UK Bunny already does this (see overlap map).
  *Proposed pattern (not built)* instead of a native translator: **Bunny as Focus's OMOP mediator** — Focus
  forwards the query to Bunny (MIT), which gains an HTTP mode gated by config and backwards
  compatible (fork + upstream PR; the CLI already takes an RQuest job as JSON); Focus applies its
  own obfuscation and Bunny's is switched off. Optional: **Spot in an RQuest mode** polls HDR UK's
  Cohort Discovery Service and carries jobs over Beam. Shared prerequisite for any AST↔OMOP path: a maintained
  catalogue-code ↔ OMOP `concept_id` mapping (Athena). Limits: Bunny counts persons only (no
  sample counts), filters specimens by concept and date only (`OMOP_SPECIMEN_ENABLED`, off by
  default), and returns no stratification of the cohort — each chart bar would be its own query.
- New project/data model = Rust code change + release (flavours hard-wired); move to config.
- Multi-modal **donor-level intersection** (e.g. clinical ∧ variant ∧ imaging for the same
  donor) is not supported — would need multi-backend execution with a local join on a
  site donor ID.
- Single dominant contributor; no paper, docs = README.

**Pointers:** [samply/focus](https://github.com/samply/focus) (README, CHANGELOG).

---

## 2a. GA4GH Beacon v2 — where it fits with Samply

**Status:** Focus has a Beacon client (EUCAIM only); a generic Lens→Beacon mediator exists but is dormant.

**Beacon v2 in brief** ([spec](https://github.com/ga4gh-beacon/beacon-v2), [docs](https://docs.genomebeacons.org))
- GA4GH standard (2022) for discovery over genomic variants and phenoclinical entities
  (`individuals`, `biosamples`, `g_variants`, `analyses`, `runs`, `cohorts`, `datasets`).
- Response granularity: `boolean`, `count` or `record`. Per-dataset counts come back as
  result sets (`includeResultsetResponses`).
- Filters: ontology terms, alphanumeric comparisons and custom terms. **All filters and
  parameters are ANDed. There are no Boolean expressions** ([docs/filters.md](https://github.com/ga4gh-beacon/beacon-v2/blob/main/docs/filters.md)).
  `/filtering_terms` publishes what a beacon can be asked.
- Networks and aggregators call each beacon **synchronously from the centre**, so every beacon
  needs an inbound HTTPS endpoint ([docs/networks.md](https://github.com/ga4gh-beacon/beacon-v2/blob/main/docs/networks.md)).
  HDR UK's Relay ships a Beacon front end that is disabled by default for exactly that reason.

**What we already have**
- Focus `ENDPOINT_TYPE=eucaim-beacon`: AST → Beacon v2 request (`POST {endpoint}/collections`,
  `requestedGranularity: record`). Its term maps are hard-coded for EUCAIM imaging (`src/eucaim_beacon.rs`).
- [lens-beacon-service](https://github.com/samply/lens-beacon-service): central AST → Beacon
  filters, fanned out to the GDI starter kit, Progenetix and RD-Connect. Dormant; [lens2beacon](https://github.com/samply/lens2beacon) is similar.

**Two directions, both behind Beam** — *proposed, not built*

| Direction | How | What it buys | Limits |
|---|---|---|---|
| **Consume:** a site's Beacon as a Focus back end | Generalise the Focus Beacon client: catalogue code → filter id from config, scopes `individuals`/`g_variants`, `count` granularity, Focus obfuscation on the result | Sites keep a standard Beacon (e.g. MOLGENIS EMX2) without opening an inbound port; allele-level queries reach the Locator | Only queries that are a single AND conjunction. OR across groups can't be computed from counts because overlaps are unknown, so reject it. No stratifiers or charts |
| **Expose:** the federation as a Beacon | Spot serves `/individuals`, `/filtering_terms` (from the Lens catalogue), `boolean`/`count`; translates to AST and fans out over Beam; one result set per site/collection | GDI/EUCAIM/ELIXIR Beacon networks query the whole federation through one inbound endpoint (Spot's), with per-biobank result sets | Counts are already obfuscated per site, so totals carry summed noise. Only the term subset that Beacon filters can express |

**Not a common format between networks.** Beacon has no OR, no NOT, no stratifiers or
distributions, and counts only. The Lens AST (OR-of-ANDs plus stratifiers) is strictly richer,
so translate at the edges (the two rows above) and keep the AST + Beam task API inside the
federation.

---

## 3. Samply.Blaze — FHIR server with embedded CQL

**Status:** production, widely adopted beyond DKFZ.

**What it does**
- FHIR R4 server on embedded RocksDB (immutable, versioned); optional distributed mode
  (Kafka log + Cassandra store, scales reads).
- **CQL evaluated next to the indices**: `Measure/$evaluate-measure`, `$cql`.
- `$everything`, `$purge`, `$compact`, partial GraphQL, async request pattern; optional
  terminology service (LOINC, SNOMED CT, UCUM, …); admin UI; OIDC bearer auth.
- Data-model-agnostic within FHIR: any profile set (BBMRI.de/GBA, MIABIS on FHIR, oBDS/onco,
  MII KDS, molecular markers …); other modalities enter as FHIR resources (e.g. genomic
  Observations, ImagingStudy) and become CQL-joinable per patient.

**Selling points**
- Fast population-level counting: independent benchmark vs HAPI shows faster import, far
  less disk and faster count/aggregate queries ([JMIR Med Inform 2026](https://doi.org/10.2196/82924));
  own benchmarks on [blaze-server.org/performance](https://blaze-server.org/performance.html).
- Single container, no external DB. Signed images, CI vuln scanning, OpenSSF Scorecard,
  SECURITY.md with private reporting.
- Adoption: CODEX/NUM feasibility ([JMIR 2022](https://doi.org/10.2196/36709)), MII tooling
  (FLARE, TORCH, FDPG), MIRACUM Helm charts, PrivateAIM, BBMRI.cz fhir-module — check with
  `gh search code '"samply/blaze"'`.
- Commercial support available (KF Digital Health) — useful for sustainability sections.

**Limitations to address**
- Single core maintainer (Clojure) — highest bus-factor risk in the stack.
- Authentication only, **no authorization** (no SMART scopes / consent filtering) — must
  sit behind a gateway (as in the Bridgehead).
- R4 only; no Bulk `$export`, PATCH, Subscriptions, conditional update; unknown search
  params silently ignored unless `Prefer: handling=strict`; no OMOP export.
- Single serial write log; conformance runs (Touchstone) and CQL coverage docs are stale.

**Pointers:** [samply/blaze](https://github.com/samply/blaze), [blaze-server.org](https://blaze-server.org),
paper [MIE 2026](https://doi.org/10.3233/shti260455).

---

## 4. Samply.Lens (+ Spot, Prism) — federated search UI

**Status:** production (≥5 live explorers).

**What it does**
- Svelte web-component library (`@samply/lens`): catalogue tree, search bar, charts,
  result table, query explain, **Negotiator button**; configured by JSON (schema-validated).
- OR-of-ANDs query → AST → Spot (central gateway, SSE streaming) → Beam; Prism serves
  cached facet counts.
- Directory lookups (biobank names, collection links) and BBMRI-ERIC Negotiator hand-off built in.

**Deployments** (repo → live URL): [bbmri-sample-locator](https://github.com/samply/bbmri-sample-locator)
→ locator.bbmri-eric.eu; [gbn-sample-locator](https://github.com/samply/gbn-sample-locator)
→ samplelocator.bbmri.de; [ccp-explorer](https://github.com/samply/ccp-explorer) →
data.dktk.dkfz.de; [eucaim-frontend](https://github.com/samply/eucaim-frontend) →
explorer.eucaim.cancerimage.eu; [dhki-explorer](https://github.com/samply/dhki-explorer) →
explorer.hector.dkfz.de. Further: cce, itcc, nngm explorers.

**Selling points**
- One code base, many explorers; framework-agnostic web components.
- Discovery → access request in one flow (Negotiator); LS AAI login via oauth2-proxy.
- Natural-language front end piloted: [unified-discovery-interface-pilot](https://github.com/samply/unified-discovery-interface-pilot)
  (Lens fork, searches Directory **and** Locator, local LLM turns free text into a query);
  MCP server prototype for Locator and Directory: [locator_mcp_server](https://github.com/samply/locator_mcp_server).
  Because the query is shown as structured Lens state and the results as structured Lens
  output, the user can check what the LLM did.
- Beacon v2 fan-out existed ([lens-beacon-service](https://github.com/samply/lens-beacon-service): AST →
  Beacon filters → GDI starter kit, Progenetix, RD-Connect) — dormant.

**Limitations to address**
- Each new modality/data model still needs catalogue + Focus flavour work (the "UI
  adaptation" partners notice).
- 0.x API, sparse tests, no accessibility audit; a private rewrite (Lens 3, React) is under
  way — state which generation a proposal relies on.
- lens-beacon-service is unmaintained; current Lens only talks to Spot.

**Pointers:** [samply/lens](https://github.com/samply/lens), [Lens book](https://samply.github.io/lens/book/),
[demo](https://samply.github.io/lens/demo/), [spot](https://github.com/samply/spot), [prism](https://github.com/samply/prism).

---

## 5. Bridgehead — site deployment package

**Status:** production.

**What it does**
- bash + systemd + docker compose turnkey installer: `./bridgehead install|enroll|start|update <project>`
  on a single Linux VM; site config from a per-site Git repo.
- Projects (`bridgehead/bridgehead`): `bbmri` (modules `eric` + `gbn` — one VM, two networks),
  `ccp`, `cce`, `pscc`, `dhki`, `nngm`, `itcc`, `kr`, `minimal`.
- Modules: DataSHIELD/Opal, DNPM:DIP node, ID management (Mainzelliste/MAGICPL), Exporter,
  Directory Sync, BBMRI.cz data-quality agent, TransFAIR ETL, OVIS, fhir2sql, obds2fhir.
- Daily auto-update (git + images), health pings, secret fetching, optional backups.
- Successor in development: [rusthead](https://github.com/samply/rusthead) (compose generated from TOML; bbmri, ccp, dnpm, eucaim).

**Selling points**
- **Zero inbound ports**; centrally operated updates, PKI renewal, secret rotation, monitoring
  — the site only provides a VM and outbound HTTPS.
- One package joins several networks in parallel; data-protection concept via NUM/GBN (README).
- Broadest maintainer base in the stack.

**Limitations to address**
- Rolling updates of mutable tags (`main`, `latest`) without signature/digest verification —
  fix (cosign/digest pinning, change control) before claiming NIS2/EHDS readiness.
- Sites depend on DKFZ-run central services (brokers, registry mirror, config GitLab,
  monitoring) — proposals must fund operations or describe hand-over/self-hosting.
- No releases, no paper; docker compose only (Kubernetes partners, e.g. EUCAIM, wrote their own manifests).

**Pointers:** [samply/bridgehead](https://github.com/samply/bridgehead) (README incl. requirements and data-protection links).

---

## 6. Monitoring

**Status:** production, but spread over several back-ends.

- Site push: self-hosted Healthchecks pings from each Bridgehead (`bridgehead/lib/monitoring.sh`).
- Connectivity: broker per-proxy health (`/v1/health/proxies/<id>`, monitoring key).
- Black-box: a `monitoring` Beam app on each broker sends test queries end to end.
- Icinga 2 checks ([icinga-client](https://github.com/samply/icinga-client), beamctl, managepki, secret-sync central).
- Fleet dashboard [verbis-monitoring-ui](https://github.com/samply/verbis-monitoring-ui) over Zabbix (VM fleet).
- End-to-end UI tests (not monitoring): [headlights](https://github.com/samply/headlights) (Playwright across Lens → Blaze).

**Selling point:** sites need no monitoring effort; network-wide availability is observable centrally.
**Limitation:** three back-ends, partly private config — document one architecture page before citing.

---

## 7. Data-model and integration helpers

| Tool | Function | Status | Pointer |
|---|---|---|---|
| Directory Sync | Pushes FHIR aggregates (collections, counts) from Blaze into the BBMRI-ERIC Directory (MOLGENIS), pulls contacts back; ships in Bridgehead | production | [directory_sync_service](https://github.com/samply/directory_sync_service) |
| TransFAIR | ETL (FHIR copy, bbmri↔mii, dicom2fhir, obds2fhir) + TTP-mediated linkage request API (exchange vs project pseudonym, optional FHIR Consent) | pilot | [samply/transFAIR](https://github.com/samply/transFAIR) |
| Exporter | Project-scoped data export from Blaze/SQL (feeds DataSHIELD, file transfer) | production (CCP) | [samply/exporter](https://github.com/samply/exporter) |
| ITCC federated data hub | Site-side pseudonymisation, FHIR + MAF genomics shipped over Beam to central Blaze + S3 (Parquet/Iceberg), cBioPortal export | pilot, private repo | samply/itcc-federated-data-hub |

---

## 8. Mainzelliste — pseudonymisation, record linkage, consent

**Status:** production (10+ years; many registries, biobanks and networks — reference list in README).

**What it does**
- REST first-level pseudonymisation: IDAT → PIDs, multiple ID types, external and
  **associated IDs** (e.g. specimen/aliquot IDs bound to a patient).
- Error-tolerant record linkage (EpiLink) with tentative-match resolution; Bloom-filter /
  LSH privacy-preserving linkage; SMPC linkage (MainSEL, cross-site via beam-sel).
- FHIR Consent with templates and policy sets, consent scans; multi-tenancy, OIDC
  groups/claims, audit trail; batch API (benchmark in `doc/BENCHMARK.md`).
- Admin GUI ([mainzelliste-gui](https://github.com/medicalinformatics/mainzelliste-gui)); enrollment UI (see §9).

**Selling points**
- Token-based, browser-direct IDAT flow (the research system never sees IDAT).
- Patient **and** sample linkage in one service — fits a "donor + sample linkage core".
- Integrated in Bridgehead (`ccp` ID management) and in DataCastle.

**Limitations to address**
- Maintenance concentrated on few developers; no LTS (latest version only).
- FHIR API and some endpoints flagged experimental.
- In Germany, MII/NUM trust centres mostly run Greifswald's E-PIX/gPAS/gICS (overlap).
- AGPL-3.0 (with additional permission) — check partner licence policies.

**Pointers:** [mainzelliste.de](https://www.mainzelliste.de/), [Bitbucket repo](https://bitbucket.org/medicalinformatics/mainzelliste)
(canonical; `github.com/samply/mainzelliste` is something else), papers
[BMC MIDM 2015](https://doi.org/10.1186/s12911-014-0123-5), [Patterns 2025](https://doi.org/10.1016/j.patter.2025.101432).

---

## 9. DataCastle / keep — Prospective Research Platform

**Status:** pilot/prototype; **repos not public** (`samply/keep`, `datacastle-forager`,
`datacastle-uploader`, `data-castle`) — publish and license before citing as open source.

**What it does**
- Hybrid prospective/retrospective data management around the patient:
  - **Enrollment** with pseudonymisation at the point of capture (Mainzelliste; enrollment
    UI with consent capture, batch enrollment, passkey-encrypted client-side IDAT cache).
  - New data documented in an **EDC (REDCap)** or other tools researchers already use
    (questionnaires, PACS/DICOM via Orthanc/OHIF, documents in S3).
  - **Existing data tied in** via APIs and record linkage: forager connectors for REDCap,
    Orthanc, Onkostar, LabCollector, DIZ FHIR (Blaze), questionnaire tools → DataVault.
  - **Uploader** pipeline: DICOM upload → IDAT check → Mainzelliste PID → DICOM
    de-identification → Orthanc → index.
  - **keep apps ("PI View")**: per-patient overview across sources, filters, statistics,
    study task lists; biobank portal variant.
  - FAIR sharing via the federated explorer (Lens/Beam) — **architecture, not yet wired**.

**Selling points**
- Combines EDC with researchers' own tools instead of replacing them; PID assigned before
  data enters the lake; cross-source per-patient overview for PIs and study nurses.
- Shares IAM and hosting base with the rest of the stack.
- Paper: [DataCastle, MIE 2026](https://doi.org/10.3233/SHTI260407).

**Limitations to address**
- Not public / no licence (paper says open source).
- No authorization model beyond login (no per-study/role scoping) — required for GDPR
  minimisation; parts of auth only on feature branches.
- Many "PI View" tasks (export to secure computation, DICOM export, DQ checks, reports) are
  UI stubs — present as roadmap. Processing environment and HealthDCAT-AP mapping claimed
  in the paper not found in code.
- REDCap is not open source; forager reads REDCap's DB directly (schema coupling).
- No production deployment of the keep/forager stack yet; production evidence comes from
  the TTP/Mainzelliste pieces.

---

## 9a. Sample Selector — keep instance for BPD

**Status:** in development (BPD).

**What it does**
- Site-side tool for biobanks to process sample requests transparently and efficiently,
  selecting samples from local biospecimen and associated clinical data.
- An instance of keep (§9). In BPD it ships as part of the partners' **"Local FDPG"**
  distribution, not the Bridgehead.
- Requests reach it from the NUM Data Portal and, via a Beam-to-DSF facade, from the BBMRI-ERIC
  Locator; it shows them on local data and selects samples. Sample availabilities flow back
  to the application in the portal.
- *Probably* also a **central instance** for the Zentrale Bioproben-Anfrage- und Beratungsstelle
  (BPD AP2 goal 2.2).
- Pointers: BPD Vorhabensbeschreibung, AP2 goals 2.1/2.2/2.6, tasks 2.1.x, 2.2.3, 2.5.4, 2.6.3–2.6.4
  (SharePoint `pantr/2025/Nationale Biobank/Antrag/`).

**Limitations to address**
- Local FDPG is a second site-side package next to the Bridgehead (`bbmri` project) and is
  limited to German university hospitals — say how biobanks outside them get the
  Sample Selector.
- Inherits keep's limitations (§9): not public, no authorization model beyond login.

---

## 10. Analysis workspaces (what we do *not* have)

- **Central analysis workspaces** on [Coder](https://coder.com) (JupyterLab, RStudio, VS Code;
  several instances in operation). We call them analysis workspaces, not SPE/TRE: egress
  control, an output airlock and security certification are unchecked.
- **Federated analysis over Beam** (*proven for DataSHIELD/Opal only; the rest is proposed*): the DataSHIELD pattern generalises. The runtime goes in
  as a Bridgehead module, its traffic is carried by Beam (no inbound ports, E2E), and
  authorisation uses Beam identities and API keys. HTTP request/response
  (DataSHIELD/Opal, Armadillo) works through beam-connect. Streaming protocols (Flower gRPC,
  vantage6 Socket.IO) need a TCP/stream mode over Beam sockets, which is not built yet.
- For SPE/TRE, partner tech is ahead: EUCAIM mini-node (Kubernetes, Guacamole, Jupyter VREs,
  LS AAI-brokered Keycloak) — [EUCAIM/mini-node](https://github.com/EUCAIM/mini-node).
  Our natural contribution is transport (Beam, beam-file), identity provisioning
  (secret-sync) and federated statistics (DataSHIELD over beam-connect).
- Related platforms we co-develop or that come from elsewhere in DKFZ (not ours — coordinate, don't claim):
  - **FLAME** (PrivateAIM, MII): federated learning and analytics platform; our group's
    share is SMPC tooling and PPRL middleware (MainSEL) — see `projects/2023_BMBF_PrivateAIM/`.
  - **[kaapana](https://github.com/kaapana/kaapana)** (DKFZ Medical Image Computing): Kubernetes
    imaging platform with JupyterLab workspaces and federated learning; EUCAIM WP6 builds on
    it — see `projects/2022_EC_EUCAIM/`.

---

## Overlap map with other technologies

| Other technology | Overlaps with | Our differentiator | Where they are stronger |
|---|---|---|---|
| HDR UK Hutch: [Bunny](https://github.com/Health-Informatics-UoN/hutch-bunny) + [Relay](https://github.com/Health-Informatics-UoN/hutch-relay) + [Cohort Discovery Service](https://github.com/HDRUK/cohort-discovery-service-api) | Focus, Beam broker, Lens/Spot | E2E-encrypted generic transport; many back-ends; Laplace obfuscation; FHIR/CQL | **Native OMOP** (availability + distribution); hierarchical relays. Combine rather than compete: Bunny behind Focus, Spot as RQuest gateway (see §2) |
| [DSF](https://dsf.dev) | Beam | Outbound-only, no DMZ endpoint | BPMN processes, MII adoption |
| [vantage6](https://github.com/vantage6/vantage6) | Beam (+ partly Focus) | Mandatory E2E; transport separate from compute | Federated-learning algorithm containers, Python SDK |
| [Flower](https://github.com/flwrlabs/flower) | Beam (transport) | — | Federated learning framework |
| DataSHIELD / [Armadillo](https://github.com/molgenis/molgenis-service-armadillo) / Opal | — (complement) | We run DataSHIELD **without inbound ports** via beam-connect | Statistical methods, community |
| GA4GH [Beacon v2](https://github.com/ga4gh-beacon/beacon-v2) / GDI | Focus/Lens (partly) | Can carry Beacon queries behind Beam (no inbound endpoint) | Global genomics standard, allele-level queries |
| [MOLGENIS EMX2](https://github.com/molgenis/molgenis-emx2) | — (complement) | Donor/sample-level federated counts | Catalogue/Directory, Beacon API, FAIR Data Point |
| [HAPI FHIR](https://hapifhir.io) | Blaze | Embedded CQL, storage efficiency, count performance | Feature completeness, R5, community |
| Greifswald E-PIX/gPAS/gICS | Mainzelliste | Associated sample IDs, PPRL/SMPC, token flow | MII/NUM trust-centre adoption |
| EUCAIM mini-node / processing env. | — (gap on our side) | — | Ready SPE with Guacamole + Jupyter |

---

## Live facts — how to look them up

| Fact | Command / source |
|---|---|
| Sites online per network | `curl -s https://<broker>/v1/health/proxies \| jq length` (brokers: see `bridgehead/*/vars`, `bridgehead/bbmri/modules/*-setup.sh`); exclude central/test proxies |
| Releases / latest version | `gh api repos/samply/<repo>/releases --jq '.[0].tag_name,.[0].published_at'` (Beam: `CHANGELOG.md`) |
| Active maintainers (12 mo) | `gh api 'repos/samply/<repo>/commits?since=<date>' --paginate --jq '.[].author.login' \| sort \| uniq -c` |
| Docker pulls | `curl -s https://hub.docker.com/v2/repositories/samply/<image>/ \| jq .pull_count` |
| Blaze adoption | `gh search code '"samply/blaze"' --limit 100` |
| Versions running at sites | `bridgehead/versions/prod` |
| Lens version per explorer | `package.json` of each explorer repo |
| Repo visibility (public/private) | `gh repo view samply/<repo> --json visibility` |

## Publications (by DOI)

- Blaze: [10.3233/shti260455](https://doi.org/10.3233/shti260455); Blaze vs HAPI benchmark: [10.2196/82924](https://doi.org/10.2196/82924); CODEX server choice: [10.2196/36709](https://doi.org/10.2196/36709)
- Sample Locator / GBN: [10.1016/j.compbiomed.2024.108941](https://doi.org/10.1016/j.compbiomed.2024.108941), [10.2196/17739](https://doi.org/10.2196/17739), [10.1371/journal.pone.0257632](https://doi.org/10.1371/journal.pone.0257632), [10.3233/978-1-61499-808-2-75](https://doi.org/10.3233/978-1-61499-808-2-75)
- DKTK CCP: [10.1200/cci.17.00062](https://doi.org/10.1200/cci.17.00062), [10.1007/s10654-023-00990-w](https://doi.org/10.1007/s10654-023-00990-w)
- Data Science Orchestrator (DataSHIELD over Beam): [10.3233/shti250438](https://doi.org/10.3233/shti250438)
- Privacy-preserving data quality: [10.1186/s12911-025-03328-6](https://doi.org/10.1186/s12911-025-03328-6)
- Mainzelliste: [10.1186/s12911-014-0123-5](https://doi.org/10.1186/s12911-014-0123-5), [10.1016/j.patter.2025.101432](https://doi.org/10.1016/j.patter.2025.101432)
- DataCastle: [10.3233/SHTI260407](https://doi.org/10.3233/SHTI260407)
- **Gap:** no paper on Beam, Focus, Lens or Bridgehead.
