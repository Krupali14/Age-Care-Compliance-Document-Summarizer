# Graph Report - krupali-project-personal  (2026-09-18)

## Corpus Check
- 136 files · ~92,848 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 907 nodes · 1357 edges · 56 communities (52 shown, 4 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 208 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1635a841`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Backend DB Models & Alembic|Backend DB Models & Alembic]]
- [[_COMMUNITY_Frontend API Clients & Views|Frontend API Clients & Views]]
- [[_COMMUNITY_Backend Router Endpoints|Backend Router Endpoints]]
- [[_COMMUNITY_Project Docs & Requirements Chain|Project Docs & Requirements Chain]]
- [[_COMMUNITY_Document Extraction Pipeline|Document Extraction Pipeline]]
- [[_COMMUNITY_Frontend App Shell & Auth Context|Frontend App Shell & Auth Context]]
- [[_COMMUNITY_Frontend Package Dependencies|Frontend Package Dependencies]]
- [[_COMMUNITY_Auth & Upload Flow|Auth & Upload Flow]]
- [[_COMMUNITY_Frontend TS Config|Frontend TS Config]]
- [[_COMMUNITY_Graphify Skill Docs|Graphify Skill Docs]]
- [[_COMMUNITY_Chat & LLM Config|Chat & LLM Config]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Eval Scoring|Eval Scoring]]
- [[_COMMUNITY_Upload Tests|Upload Tests]]
- [[_COMMUNITY_Chat Tests|Chat Tests]]
- [[_COMMUNITY_Auth Tests|Auth Tests]]
- [[_COMMUNITY_Frontend DockerEntry|Frontend Docker/Entry]]
- [[_COMMUNITY_DB Docker Service|DB Docker Service]]
- [[_COMMUNITY_Vite Config|Vite Config]]
- [[_COMMUNITY_Vite Env Types|Vite Env Types]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]

## God Nodes (most connected - your core abstractions)
1. `Aged Care Compliance Summariser Implementation Plan` - 22 edges
2. `_get_owned_document()` - 19 edges
3. `find_incident_datetime()` - 19 edges
4. `_auth_header()` - 19 edges
5. `process_document()` - 17 edges
6. `12 — Design decisions` - 17 edges
7. `FastAPI` - 16 edges
8. `compilerOptions` - 16 edges
9. `run_check()` - 14 edges
10. `ParsedSection` - 14 edges

## Surprising Connections (you probably didn't know these)
- `Aged Care Compliance Document Summariser Design Spec` --references--> `Project Scope: functional requirements (upload, summarisation, obligation/risk/deadline/action extraction, dashboard, chatbot)`  [EXTRACTED]
  docs/superpowers/specs/2026-08-17-aged-care-compliance-summariser-design.md → Project Scope Template.pdf
- `Aged Care Compliance Document Summariser Design Spec` --references--> `Project Scope: non-functional requirements (accuracy, usability, performance, security, privacy, reliability, responsible model)`  [EXTRACTED]
  docs/superpowers/specs/2026-08-17-aged-care-compliance-summariser-design.md → Project Scope Template.pdf
- `Section/heading-based chunking via docling` --references--> `Project Scope: required resources (datasets, PyMuPDF/python-docx, spaCy/HF/Sentence Transformers, PostgreSQL, LLM service, ground-truth eval dataset)`  [EXTRACTED]
  docs/superpowers/specs/2026-08-17-aged-care-compliance-summariser-design.md → Project Scope Template.pdf
- `Fuzzy-match precision/recall/F1 eval harness` --references--> `Project Scope: required resources (datasets, PyMuPDF/python-docx, spaCy/HF/Sentence Transformers, PostgreSQL, LLM service, ground-truth eval dataset)`  [EXTRACTED]
  docs/superpowers/specs/2026-08-17-aged-care-compliance-summariser-design.md → Project Scope Template.pdf
- `docker-compose backend service` --shares_data_with--> `Aged Care Compliance Summariser Implementation Plan`  [INFERRED]
  docker-compose.yml → docs/superpowers/plans/2026-08-17-aged-care-compliance-summariser.md

## Import Cycles
- 1-file cycle: `backend/app/main.py -> backend/app/main.py`
- 1-file cycle: `backend/app/services/compliance_check.py -> backend/app/services/compliance_check.py`
- 1-file cycle: `backend/app/services/deadlines.py -> backend/app/services/deadlines.py`

## Hyperedges (group relationships)
- **Docling parse -> LLM structured extraction -> persistence pipeline** — plans_task5_docling_parser, plans_task6_llm_extraction, plans_task7_processing_pipeline, specs_design_chunking_strategy [INFERRED 0.85]
- **graphify Step 3 Part B subagent dispatch and export flow** — skill_graphify_pipeline, references_extraction_spec_prompt, references_exports_pipeline [EXTRACTED 1.00]
- **Scope requirements -> design spec -> implementation plan traceability chain** — scope_project_scope_template_functional_requirements, specs_design_doc, plans_summariser_implementation_plan [INFERRED 0.85]

## Communities (56 total, 4 thin omitted)

### Community 0 - "Backend DB Models & Alembic"
Cohesion: 0.07
Nodes (46): datetime, Deadline, bucket_for(), is_relative_due_date(), parse_relative(), Turning a deadline's stated due date into a point in time, a bucket and a status, Which urgency bucket a due time falls in., The offset a relative timeframe names, or None if it names no timeframe.      Se (+38 more)

### Community 1 - "Frontend API Clients & Views"
Cohesion: 0.07
Nodes (33): create_access_token(), get_current_user(), hash_password(), verify_password(), Settings, clear(), client_ip(), enforce() (+25 more)

### Community 2 - "Backend Router Endpoints"
Cohesion: 0.05
Nodes (52): lifespan(), Fail anything left mid-processing by the previous run of this process.      Extr, Fail anything left mid-processing by the previous run of this process.      run_, _release_interrupted_checks(), _release_interrupted_documents(), Session, User, Session (+44 more)

### Community 3 - "Project Docs & Requirements Chain"
Cohesion: 0.06
Nodes (36): docling dependency, langchain-openai dependency, passlib[bcrypt] dependency, python-jose[cryptography] dependency, rapidfuzz dependency, docker-compose backend service, Aged Care Compliance Summariser Implementation Plan, File Structure (+28 more)

### Community 4 - "Document Extraction Pipeline"
Cohesion: 0.08
Nodes (57): BaseModel, ChatOpenAI, date, ParsedSection, ParsedSection, _batch(), BatchExtraction, check_relevance() (+49 more)

### Community 5 - "Frontend App Shell & Auth Context"
Cohesion: 0.05
Nodes (35): 1. The automatic self-check, 2. The ground-truth run, 3. Running an evaluation, 4. Reading the results honestly, 5. Worth adding next, Coverage — the check against silent gaps, Evaluation results: what the numbers mean and how to run them, From the command line (+27 more)

### Community 6 - "Frontend Package Dependencies"
Cohesion: 0.07
Nodes (28): dependencies, react, react-dom, react-markdown, react-router-dom, @tanstack/react-query, devDependencies, autoprefixer (+20 more)

### Community 7 - "Auth & Upload Flow"
Cohesion: 0.09
Nodes (22): 1. The path a file takes, 2. End-to-end timing, 3. A batching trap worth knowing about, 4. How relevant content is identified, (a) Is this document in scope at all?, (b) Which sections answer this user's question? (`routers/chat.py`), (c) Questions about categories the document never names, Correctness under batching: index + heading echo (+14 more)

### Community 8 - "Frontend TS Config"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+9 more)

### Community 9 - "Graphify Skill Docs"
Cohesion: 0.12
Nodes (17): /graphify slash-command trigger rule, project CLAUDE.md graphify integration section, graphify add <url> ingestion, graphify --watch folder watcher, graphify export pipeline (wiki/neo4j/falkordb/svg/graphml/mcp/benchmark), graphify semantic extraction subagent prompt, graphify clone GitHub repo(s), graphify merge-graphs cross-repo merge (+9 more)

### Community 10 - "Chat & LLM Config"
Cohesion: 0.27
Nodes (11): _login(), Regression cover for the auth rate limits.  Unlimited password guessing against, Pin the router's limits to something small and deterministic., Otherwise an attacker learns they found it from the response changing., The per-address counter must not lock out the whole application., _register(), _small_limits(), test_a_different_account_is_unaffected_by_another_s_lockout() (+3 more)

### Community 11 - "Community 11"
Cohesion: 0.07
Nodes (28): 04 — API reference, Authentication, Chat, Compliance checks, Conventions, CORS, `DELETE /api/compliance-checks/item/{check_id}`, `DELETE /api/documents/{id}` (+20 more)

### Community 12 - "Eval Scoring"
Cohesion: 0.11
Nodes (26): EvalRun, Session, run_eval(), _findings(), Score a document's extracted rows against hand-annotated ground truth,     persi, Every extracted finding for a document, as (section_id, text)., Score a document against itself, with no hand-annotated ground truth.      run_e, run_auto_eval() (+18 more)

### Community 13 - "Upload Tests"
Cohesion: 0.14
Nodes (19): _auth(), _auth_header(), A rejected upload must not leave a half-created document behind., A 254-character name raised OSError deep inside the write — the filesystem     c, 90 CJK characters is 270 bytes. Counting characters would have let it through, Only HTTPException used to trigger cleanup, so any other failure during the, A renamed text file used to be accepted and only failed minutes later, deep in, Unbounded uploads were read wholly into memory. (+11 more)

### Community 14 - "Chat Tests"
Cohesion: 0.29
Nodes (12): _auth_header(), _chat_auth(), _doc_with_sections(), What deadlines are mentioned?" used to retrieve nothing: the provisions     neve, A 13-character contents fragment used to outrank the section that actually     a, test_chat_answers_from_document_sections(), test_chat_not_owned_returns_404(), test_chat_ranks_real_content_above_contents_scraps() (+4 more)

### Community 15 - "Auth Tests"
Cohesion: 0.25
Nodes (4): Empty passwords were accepted, and bcrypt silently ignores everything past 72, Registration lowercases the address, so sign-in has to as well or the account, test_email_is_case_insensitive_end_to_end(), test_register_rejects_weak_and_oversized_passwords()

### Community 23 - "Vite Config"
Cohesion: 0.12
Nodes (17): 12 — Design decisions, D10 — 404, never 403, D11 — Rate limiting in memory, with the ceiling written down, D12 — The token lives in `localStorage`, D13 — React Query only, no global store, D14 — Two evaluation modes, labelled differently, D15 — The E2E suite raises the rate limits rather than lowering them, D16 — Suggested questions belong to the empty state (+9 more)

### Community 27 - "Vite Env Types"
Cohesion: 0.12
Nodes (16): 06 — AI and retrieval, 1. BM25 over the document's own text, 2. Extracted findings are retrievable passages, 3. Category questions get guaranteed slots, Cost and safety controls, Every place a model is called, Extraction prompting, Retrieval — how the assistant finds the answer (+8 more)

### Community 29 - "Community 29"
Cohesion: 0.13
Nodes (20): DocumentConverter, _converter(), _has_text_layer(), _norm(), _page_texts(), parse_document(), _parse_pdf_text_layer(), _parse_with_docling() (+12 more)

### Community 30 - "Community 30"
Cohesion: 0.12
Nodes (17): 03 — Data model, `action_items`, `check_findings`, `compliance_checks`, `deadlines`, `documents`, `eval_runs`, `obligations` (+9 more)

### Community 31 - "Community 31"
Cohesion: 0.13
Nodes (14): Aged Care Compliance Document Summariser — Design, API, Architecture, Data model (Postgres, SQLAlchemy + Alembic), Evaluation, Frontend, Goals, Key decisions (+6 more)

### Community 32 - "Community 32"
Cohesion: 0.13
Nodes (15): 07 — Frontend guide, Accessibility, as implemented, `AIAssistant`, `api/client.ts` — the one fetch wrapper, AuthContext, Build and scripts, `ComplianceCheckPanel`, Components worth knowing (+7 more)

### Community 33 - "Community 33"
Cohesion: 0.16
Nodes (17): Session, User, chat(), ChatRequest, _findings(), _passages(), The document's extracted obligations, risks, deadlines and actions as     (text,, The k best passages, within a character budget, and the sections to cite. (+9 more)

### Community 34 - "Community 34"
Cohesion: 0.15
Nodes (13): 05 — The processing pipeline, 1. Parsing — `docling_parser.py`, 2. The relevance gate — `extraction.check_relevance()`, 3. Sections first, 4. Extraction — where the time goes, 5. Retrying the gaps, 6. Persisting, End-to-end timing (+5 more)

### Community 35 - "Community 35"
Cohesion: 0.17
Nodes (11): 11 — Running locally, A first walk-through, Environment variables, First run, For the editor, Make targets, Prerequisites, Resetting (+3 more)

### Community 37 - "Community 37"
Cohesion: 0.18
Nodes (11): 08 — Evaluation, A real reading, Coverage — the check against silent gaps, Grounding — the check against invented content, Overall, Reading results honestly, Running it, The automatic self-check (+3 more)

### Community 38 - "Community 38"
Cohesion: 0.18
Nodes (11): 09 — Security, Authentication, Authorisation, CORS, Error handling, Injection, Input validation, Rate limiting (+3 more)

### Community 40 - "Community 40"
Cohesion: 0.20
Nodes (10): 02 — Architecture, Asynchronous — upload, Frontend structure, How the pieces fail, Layering in the backend, Request paths, Synchronous — everything except upload, Technology choices in one line each (+2 more)

### Community 41 - "Community 41"
Cohesion: 0.22
Nodes (9): 10 — Testing, Adding a test, Backend suite — `backend/tests/`, Conventions, End-to-end suite — `frontend/e2e/`, Running them, Wait for what you assert, and nothing more, What is not tested (+1 more)

### Community 42 - "Community 42"
Cohesion: 0.25
Nodes (7): How risk severity and priority are decided, How the value is constrained, If a defensible, repeatable rating is needed, Short answer, What this means in practice, Where it is stored and shown, Where the prompt lives

### Community 43 - "Community 43"
Cohesion: 0.25
Nodes (8): 01 — What this is, Domain vocabulary, Scope boundaries enforced in the product, The problem, The shape of a session, What it explicitly is not, What the application does, Who uses it

### Community 45 - "Community 45"
Cohesion: 0.29
Nodes (7): 14 — Known limitations and what comes next, Product limits, Quality limits, Security gaps, Technical limits, Testing gaps, What I would do next, in order

### Community 46 - "Community 46"
Cohesion: 0.40
Nodes (5): One-paragraph version, Project Understanding, Read in this order, Related material elsewhere in the repository, Shortest useful path

### Community 47 - "Community 47"
Cohesion: 0.50
Nodes (4): 13 — Glossary, Aged-care and regulatory terms, Application terms, Technical terms

### Community 48 - "Community 48"
Cohesion: 0.40
Nodes (4): Hour-scale deadlines and the compliance check, Sample documents, These are not real documents, Why they demo well

### Community 50 - "Community 50"
Cohesion: 0.08
Nodes (49): datetime, Obligation, CheckBatch, CheckVerdict, find_incident_datetime(), _first_time_in(), load_requirements(), Checking a case-study document against a compliance document's requirements.  Th (+41 more)

### Community 51 - "Community 51"
Cohesion: 0.08
Nodes (12): Base, ActionItem, CheckFinding, ComplianceCheck, One case-study document checked against one compliance document.      The case s, Document, EvalRun, Risk (+4 more)

### Community 52 - "Community 52"
Cohesion: 0.12
Nodes (31): UploadResponse, BackgroundTasks, Session, UploadFile, User, BackgroundTasks, Path, Session (+23 more)

### Community 53 - "Community 53"
Cohesion: 0.14
Nodes (13): API, Compliance check — design, Data model, Direction is one-way, Frontend, Out of scope, Problem, Processing (+5 more)

### Community 54 - "Community 54"
Cohesion: 0.17
Nodes (11): Compliance Check Implementation Plan, Global Constraints, Task 1: Move BM25 retrieval into a shared service, Task 2: Share the upload validation, Task 3: Models and migration, Task 4: Read the incident time out of a case study, Task 5: Run the check, Task 6: The API (+3 more)

## Knowledge Gaps
- **322 isolated node(s):** `Session`, `Request`, `Session`, `User`, `User` (+317 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Aged Care Compliance Summariser README` connect `Frontend App Shell & Auth Context` to `Project Docs & Requirements Chain`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `_get_owned_document()` (e.g. with `get_action_items()` and `chat()`) actually correct?**
  _`_get_owned_document()` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `find_incident_datetime()` (e.g. with `_latest_date_in()` and `test_a_24_hour_clock_is_understood()`) actually correct?**
  _`find_incident_datetime()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `process_document()` (e.g. with `ActionItem` and `Deadline`) actually correct?**
  _`process_document()` has 16 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Session`, `Fail anything left mid-processing by the previous run of this process.      Extr`, `Fail anything left mid-processing by the previous run of this process.      run_` to the rest of the system?**
  _408 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Backend DB Models & Alembic` be split into smaller, more focused modules?**
  _Cohesion score 0.07329462989840348 - nodes in this community are weakly interconnected._
- **Should `Frontend API Clients & Views` be split into smaller, more focused modules?**
  _Cohesion score 0.0696969696969697 - nodes in this community are weakly interconnected._