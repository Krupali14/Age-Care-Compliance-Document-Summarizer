# Graph Report - krupali-project-personal  (2026-09-02)

## Corpus Check
- 91 files · ~34,952 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 501 nodes · 727 edges · 41 communities (34 shown, 7 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 116 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4294be67`
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
- [[_COMMUNITY_Eval Scoring|Eval Scoring]]
- [[_COMMUNITY_Upload Tests|Upload Tests]]
- [[_COMMUNITY_Chat Tests|Chat Tests]]
- [[_COMMUNITY_Frontend DockerEntry|Frontend Docker/Entry]]
- [[_COMMUNITY_DB Docker Service|DB Docker Service]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]

## God Nodes (most connected - your core abstractions)
1. `Aged Care Compliance Summariser Implementation Plan` - 22 edges
2. `apiFetch()` - 19 edges
3. `process_document()` - 16 edges
4. `compilerOptions` - 16 edges
5. `_get_owned_document()` - 14 edges
6. `ParsedSection` - 14 edges
7. `Aged Care Compliance Document Summariser — Design` - 14 edges
8. `SectionExtraction` - 11 edges
9. `extract_batch()` - 11 edges
10. `What You Must Do When Invoked` - 11 edges

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
- None detected.

## Hyperedges (group relationships)
- **Docling parse -> LLM structured extraction -> persistence pipeline** — plans_task5_docling_parser, plans_task6_llm_extraction, plans_task7_processing_pipeline, specs_design_chunking_strategy [INFERRED 0.85]
- **graphify Step 3 Part B subagent dispatch and export flow** — skill_graphify_pipeline, references_extraction_spec_prompt, references_exports_pipeline [EXTRACTED 1.00]
- **Scope requirements -> design spec -> implementation plan traceability chain** — scope_project_scope_template_functional_requirements, specs_design_doc, plans_summariser_implementation_plan [INFERRED 0.85]

## Communities (41 total, 7 thin omitted)

### Community 0 - "Backend DB Models & Alembic"
Cohesion: 0.07
Nodes (26): Base, ActionItem, Deadline, Document, EvalRun, Obligation, Risk, Section (+18 more)

### Community 1 - "Frontend API Clients & Views"
Cohesion: 0.07
Nodes (32): login(), register(), askQuestion(), ChatResponse, ChatSource, apiFetch(), deleteDocument(), DocumentSummary (+24 more)

### Community 2 - "Backend Router Endpoints"
Cohesion: 0.05
Nodes (47): create_access_token(), get_current_user(), hash_password(), verify_password(), RegisterRequest, TokenResponse, UploadResponse, Session (+39 more)

### Community 3 - "Project Docs & Requirements Chain"
Cohesion: 0.05
Nodes (43): docling dependency, langchain-openai dependency, passlib[bcrypt] dependency, python-jose[cryptography] dependency, rapidfuzz dependency, docker-compose backend service, Aged Care Compliance Summariser Implementation Plan, File Structure (+35 more)

### Community 4 - "Document Extraction Pipeline"
Cohesion: 0.09
Nodes (50): BaseModel, ChatOpenAI, date, ParsedSection, ParsedSection, _batch(), BatchExtraction, check_relevance() (+42 more)

### Community 5 - "Frontend App Shell & Auth Context"
Cohesion: 0.14
Nodes (15): DashboardLayout(), ProtectedRoute(), AuthContext, AuthContextValue, AuthProvider(), expiryOf(), storedToken(), useAuth() (+7 more)

### Community 6 - "Frontend Package Dependencies"
Cohesion: 0.08
Nodes (24): dependencies, react, react-dom, react-markdown, react-router-dom, @tanstack/react-query, devDependencies, autoprefixer (+16 more)

### Community 7 - "Auth & Upload Flow"
Cohesion: 0.43
Nodes (7): EvalRun, Session, User, create_eval_run(), EvalRequest, get_eval_runs(), _serialize()

### Community 8 - "Frontend TS Config"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+9 more)

### Community 9 - "Graphify Skill Docs"
Cohesion: 0.12
Nodes (17): /graphify slash-command trigger rule, project CLAUDE.md graphify integration section, graphify add <url> ingestion, graphify --watch folder watcher, graphify export pipeline (wiki/neo4j/falkordb/svg/graphml/mcp/benchmark), graphify semantic extraction subagent prompt, graphify clone GitHub repo(s), graphify merge-graphs cross-repo merge (+9 more)

### Community 10 - "Chat & LLM Config"
Cohesion: 0.29
Nodes (5): Settings, BaseSettings, Deployments set their own session length; the default is only a default., test_session_length_is_configurable(), test_settings_load_from_env()

### Community 12 - "Eval Scoring"
Cohesion: 0.18
Nodes (12): EvalRun, Session, run_eval(), Score a document's extracted rows against hand-annotated ground truth,     persi, run_eval(), score_category(), _auth_header(), test_post_eval_not_owned_returns_404() (+4 more)

### Community 13 - "Upload Tests"
Cohesion: 0.53
Nodes (4): _auth_header(), test_upload_creates_pending_document(), test_upload_rejects_unsupported_type(), test_upload_sanitizes_path_traversal_filename()

### Community 14 - "Chat Tests"
Cohesion: 0.83
Nodes (3): _auth_header(), test_chat_answers_from_document_sections(), test_chat_not_owned_returns_404()

### Community 29 - "Community 29"
Cohesion: 0.13
Nodes (20): DocumentConverter, _converter(), _has_text_layer(), _norm(), _page_texts(), parse_document(), _parse_pdf_text_layer(), _parse_with_docling() (+12 more)

### Community 30 - "Community 30"
Cohesion: 0.08
Nodes (23): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+15 more)

### Community 31 - "Community 31"
Cohesion: 0.13
Nodes (14): Aged Care Compliance Document Summariser — Design, API, Architecture, Data model (Postgres, SQLAlchemy + Alembic), Evaluation, Frontend, Goals, Key decisions (+6 more)

### Community 32 - "Community 32"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 33 - "Community 33"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 34 - "Community 34"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 35 - "Community 35"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 36 - "Community 36"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

## Knowledge Gaps
- **161 isolated node(s):** `Session`, `Session`, `User`, `Section`, `Session` (+156 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `process_document()` connect `Document Extraction Pipeline` to `Backend DB Models & Alembic`, `Community 29`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `parse_document()` connect `Community 29` to `Document Extraction Pipeline`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Why does `ParsedSection` connect `Document Extraction Pipeline` to `Community 29`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `process_document()` (e.g. with `ActionItem` and `Deadline`) actually correct?**
  _`process_document()` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `_get_owned_document()` (e.g. with `get_action_items()` and `chat()`) actually correct?**
  _`_get_owned_document()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Session`, `Session`, `User` to the rest of the system?**
  _184 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Backend DB Models & Alembic` be split into smaller, more focused modules?**
  _Cohesion score 0.0673758865248227 - nodes in this community are weakly interconnected._