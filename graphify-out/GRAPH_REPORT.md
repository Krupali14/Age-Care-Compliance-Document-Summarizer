# Graph Report - .  (2026-08-18)

## Corpus Check
- Corpus is ~26,993 words - fits in a single context window. You may not need a graph.

## Summary
- 326 nodes · 478 edges · 29 communities (27 shown, 2 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 72 edges (avg confidence: 0.74)
- Token cost: 135,662 input · 0 output

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
- [[_COMMUNITY_App Entry & Test Fixtures|App Entry & Test Fixtures]]
- [[_COMMUNITY_Eval Scoring|Eval Scoring]]
- [[_COMMUNITY_Upload Tests|Upload Tests]]
- [[_COMMUNITY_Chat Tests|Chat Tests]]
- [[_COMMUNITY_Frontend DockerEntry|Frontend Docker/Entry]]
- [[_COMMUNITY_DB Docker Service|DB Docker Service]]

## God Nodes (most connected - your core abstractions)
1. `apiFetch()` - 19 edges
2. `compilerOptions` - 16 edges
3. `_get_owned_document()` - 13 edges
4. `process_document()` - 11 edges
5. `Aged Care Compliance Summariser Implementation Plan` - 11 edges
6. `graphify /graphify pipeline` - 10 edges
7. `_auth_header()` - 9 edges
8. `Aged Care Compliance Document Summariser Design Spec` - 9 edges
9. `ParsedSection` - 8 edges
10. `test_process_document_persists_extraction()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `Aged Care Compliance Document Summariser Design Spec` --references--> `Project Scope: functional requirements (upload, summarisation, obligation/risk/deadline/action extraction, dashboard, chatbot)`  [EXTRACTED]
  docs/superpowers/specs/2026-08-17-aged-care-compliance-summariser-design.md → Project Scope Template.pdf
- `Aged Care Compliance Document Summariser Design Spec` --references--> `Project Scope: non-functional requirements (accuracy, usability, performance, security, privacy, reliability, responsible model)`  [EXTRACTED]
  docs/superpowers/specs/2026-08-17-aged-care-compliance-summariser-design.md → Project Scope Template.pdf
- `Section/heading-based chunking via docling` --references--> `Project Scope: required resources (datasets, PyMuPDF/python-docx, spaCy/HF/Sentence Transformers, PostgreSQL, LLM service, ground-truth eval dataset)`  [EXTRACTED]
  docs/superpowers/specs/2026-08-17-aged-care-compliance-summariser-design.md → Project Scope Template.pdf
- `Fuzzy-match precision/recall/F1 eval harness` --references--> `Project Scope: required resources (datasets, PyMuPDF/python-docx, spaCy/HF/Sentence Transformers, PostgreSQL, LLM service, ground-truth eval dataset)`  [EXTRACTED]
  docs/superpowers/specs/2026-08-17-aged-care-compliance-summariser-design.md → Project Scope Template.pdf
- `docling dependency` --shares_data_with--> `Task 5: Docling parsing + section splitting`  [INFERRED]
  backend/requirements.txt → docs/superpowers/plans/2026-08-17-aged-care-compliance-summariser.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Docling parse -> LLM structured extraction -> persistence pipeline** — plans_task5_docling_parser, plans_task6_llm_extraction, plans_task7_processing_pipeline, specs_design_chunking_strategy [INFERRED 0.85]
- **graphify Step 3 Part B subagent dispatch and export flow** — skill_graphify_pipeline, references_extraction_spec_prompt, references_exports_pipeline [EXTRACTED 1.00]
- **Scope requirements -> design spec -> implementation plan traceability chain** — scope_project_scope_template_functional_requirements, specs_design_doc, plans_summariser_implementation_plan [INFERRED 0.85]

## Communities (29 total, 2 thin omitted)

### Community 0 - "Backend DB Models & Alembic"
Cohesion: 0.09
Nodes (20): Base, ActionItem, Deadline, Document, EvalRun, Obligation, Risk, Section (+12 more)

### Community 1 - "Frontend API Clients & Views"
Cohesion: 0.11
Nodes (23): login(), register(), askQuestion(), apiFetch(), deleteDocument(), DocumentSummary, listDocuments(), uploadDocument() (+15 more)

### Community 2 - "Backend Router Endpoints"
Cohesion: 0.08
Nodes (25): Session, User, Session, User, Session, User, Session, User (+17 more)

### Community 3 - "Project Docs & Requirements Chain"
Cohesion: 0.09
Nodes (28): docling dependency, langchain-openai dependency, passlib[bcrypt] dependency, python-jose[cryptography] dependency, rapidfuzz dependency, docker-compose backend service, Aged Care Compliance Summariser Implementation Plan, Task 1: LLM/JWT config settings (+20 more)

### Community 4 - "Document Extraction Pipeline"
Cohesion: 0.16
Nodes (20): BaseModel, ParsedSection, parse_document(), ParsedSection, extract_section(), ExtractedActionItem, ExtractedDeadline, ExtractedObligation (+12 more)

### Community 5 - "Frontend App Shell & Auth Context"
Cohesion: 0.14
Nodes (15): EvalRun, getEvalRuns(), DashboardLayout(), navItems, ProtectedRoute(), AuthContext, AuthContextValue, AuthProvider() (+7 more)

### Community 6 - "Frontend Package Dependencies"
Cohesion: 0.08
Nodes (23): dependencies, react, react-dom, react-router-dom, @tanstack/react-query, devDependencies, autoprefixer, postcss (+15 more)

### Community 7 - "Auth & Upload Flow"
Cohesion: 0.15
Nodes (19): create_access_token(), get_current_user(), hash_password(), verify_password(), RegisterRequest, TokenResponse, UploadResponse, Session (+11 more)

### Community 8 - "Frontend TS Config"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+9 more)

### Community 9 - "Graphify Skill Docs"
Cohesion: 0.12
Nodes (17): /graphify slash-command trigger rule, project CLAUDE.md graphify integration section, graphify add <url> ingestion, graphify --watch folder watcher, graphify export pipeline (wiki/neo4j/falkordb/svg/graphml/mcp/benchmark), graphify semantic extraction subagent prompt, graphify clone GitHub repo(s), graphify merge-graphs cross-repo merge (+9 more)

### Community 10 - "Chat & LLM Config"
Cohesion: 0.15
Nodes (11): Settings, Session, User, BaseSettings, ChatOpenAI, chat(), ChatRequest, _top_sections() (+3 more)

### Community 11 - "App Entry & Test Fixtures"
Cohesion: 0.29
Nodes (4): db_session(), Sessionmaker bound to a single in-memory SQLite engine, shared by every     fixt, A session bound to the SAME engine the `client` fixture's endpoints     read/wri, session_local()

### Community 12 - "Eval Scoring"
Cohesion: 0.32
Nodes (5): run_eval(), score_category(), test_score_category_exact_match(), test_score_category_no_match(), test_score_category_partial_match_uses_fuzzy_threshold()

### Community 13 - "Upload Tests"
Cohesion: 0.53
Nodes (4): _auth_header(), test_upload_creates_pending_document(), test_upload_rejects_unsupported_type(), test_upload_sanitizes_path_traversal_filename()

### Community 14 - "Chat Tests"
Cohesion: 0.83
Nodes (3): _auth_header(), test_chat_answers_from_document_sections(), test_chat_not_owned_returns_404()

## Knowledge Gaps
- **86 isolated node(s):** `Session`, `Session`, `User`, `Section`, `Session` (+81 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `process_document()` connect `Document Extraction Pipeline` to `Backend DB Models & Alembic`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Why does `_get_owned_document()` connect `Backend Router Endpoints` to `Chat & LLM Config`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `_get_owned_document()` (e.g. with `get_action_items()` and `chat()`) actually correct?**
  _`_get_owned_document()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `process_document()` (e.g. with `ActionItem` and `Deadline`) actually correct?**
  _`process_document()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Session`, `Session`, `User` to the rest of the system?**
  _91 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Backend DB Models & Alembic` be split into smaller, more focused modules?**
  _Cohesion score 0.08819345661450925 - nodes in this community are weakly interconnected._
- **Should `Frontend API Clients & Views` be split into smaller, more focused modules?**
  _Cohesion score 0.1092436974789916 - nodes in this community are weakly interconnected._