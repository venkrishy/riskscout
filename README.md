# RiskScout

This is an AI Agentic solution written using LangGraph and deployed on Azure Container Apps.

It is an Financial document intelligence agent

Ingests loan applications, financial statements, and contracts — extracts entities, scores risk with GPT-4o, and routes to **approve / human review / reject** based on configurable policy thresholds. Implements human-in-the-loop review via LangGraph's interrupt/resume pattern.

The frontend for this can be seen at [RiskScout (theaiguru.dev)](https://risk-scout.theaiguru.dev/).  Upload any financial statement or use some of the provided samples.  It will score the financial document for risk.  

Watch the 7-node pipeline run live — status polls every 2 seconds.
If the risk score lands 40–79, the graph pauses and you get a human-review form to approve or reject with a note.
Final decision shows extracted entities, risk score, policy citations, and full audit trail.

---

## Architecture

```
                         ┌─────────────────────────────────────────────────────────┐
                         │                   Azure Container Apps                   │
                         │                                                           │
  PDF / Text             │   FastAPI                  LangGraph StateGraph           │
  ──────────────────────►│   POST /analyze            ┌──────────────────────────┐  │
                         │        │                   │                          │  │
                         │        ▼                   │  START                   │  │
                         │   run_id returned          │    │                     │  │
                         │   (202 Accepted)           │    ▼                     │  │
                         │                            │  ingest_node             │  │
                         │   GET /status/{run_id}     │  (parse PDF → chunk →    │  │
                         │   POST /review/{run_id}    │   index to AI Search)    │  │
                         │   GET /decision/{run_id}   │    │                     │  │
                         │                            │    ▼                     │  │
                         │                            │  extract_node            │  │
                         │                            │  (GPT-4o → structured    │  │
                         │                            │   Pydantic entities)     │  │
                         │                            │    │                     │  │
                         │                            │    ▼                     │  │
                         │                            │  retrieval_node          │  │
                         │                            │  (embed query → hybrid   │  │
                         │                            │   search policy corpus)  │  │
                         │                            │    │                     │  │
                         │                            │    ▼                     │  │
                         │                            │  score_node              │  │
                         │                            │  (GPT-4o → risk score    │  │
                         │                            │   0-100 + reasoning)     │  │
                         │                            │    │                     │  │
                         │                            │    ▼                     │  │
                         │                            │  route_node              │  │
                         │                            │  (score>=80 → reject     │  │
                         │                            │   score<40  → approve    │  │
                         │                            │   40-79     → review)    │  │
                         │                            │    │                     │  │
                         │                            │    ├──────────────────┐  │  │
                         │                            │    │                  │  │  │
                         │                            │  decision_node   human_review_node  │
                         │                            │  (write to       (interrupt() —     │
                         │                            │   Cosmos DB)      awaits human)     │
                         │                            │    │                  │  │  │
                         │                            │    └──────────────────┘  │  │
                         │                            │         END              │  │
                         │                            └──────────────────────────┘  │
                         └─────────────────────────────────────────────────────────┘

Azure Services:
  Azure OpenAI          GPT-4o (reasoning) + text-embedding-3-large (RAG)
  Azure AI Search       Hybrid keyword + vector search for documents and policy corpus
  Azure Cosmos DB       Durable run history, checkpoints, and audit trail (serverless)
  Application Insights  Structured traces: node, run_id, duration_ms, tokens, timestamp
  Container Registry    Docker image storage
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | LangGraph 0.2+ (StateGraph, interrupt/resume, MemorySaver) |
| LLM / Embeddings | Azure OpenAI — GPT-4o + text-embedding-3-large |
| Vector store | Azure AI Search (hybrid search, HNSW vectors) |
| State persistence | Azure Cosmos DB (serverless NoSQL) |
| API | FastAPI + Uvicorn |
| Deployment | Azure Container Apps (auto-scale 1-5 replicas) |
| IaC | Bicep |
| CI/CD | GitHub Actions (lint → build → push → deploy) |
| Observability | OpenTelemetry + Azure Monitor / Application Insights |
| Config | pydantic-settings (`.env` → environment variables) |

---

## LangGraph Node Reference

| Node | Responsibility |
|------|---------------|
| `ingest_node` | Parse PDF/text, chunk with overlap, index to Azure AI Search |
| `extract_node` | GPT-4o call — extract typed entities (amounts, parties, risk flags) as Pydantic model |
| `retrieval_node` | Embed query, hybrid search policy corpus, return top-5 passages |
| `score_node` | GPT-4o call — produce risk score (0-100) + reasoning grounded in policy |
| `route_node` | Apply thresholds: `score>=80` → reject, `score<40` → approve, else → human review |
| `human_review_node` | `interrupt()` — pauses graph, surfaces risk summary to reviewer |
| `decision_node` | Assemble final decision + full audit trail, persist to Cosmos DB |

---

## Quickstart

### Prerequisites

- Python 3.11+
- Azure subscription with: OpenAI, AI Search, Cosmos DB, Container Apps
- `uv` package manager (`pip install uv`)

### 1. Clone and install

```bash
git clone https://github.com/venkrishy/riskscout.git
cd riskscout
uv pip install -e .
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your Azure credentials
```

### 3. Run locally

```bash
python -m riskscout.api.main
# API available at http://localhost:8000
# Swagger UI at http://localhost:8000/docs
```

### 4. Deploy to Azure

```bash
# Create resource group
az group create --name rg-riskscout --location eastus

# Deploy all infrastructure
az deployment group create \
  --resource-group rg-riskscout \
  --template-file infra/main.bicep \
  --parameters environment=prod \
               containerRegistryServer=<your-acr>.azurecr.io \
               azureOpenAiApiKey=<key> \
               azureSearchApiKey=<key>
```

---

## API Reference

### POST `/api/v1/analyze`

Upload a financial document to start an agent run.

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@loan_application.pdf"
```

Response:
```json
{
  "run_id": "3f2a1b4c-...",
  "document_id": "7e8d9f0a-...",
  "status": "ingesting",
  "message": "Document accepted. Poll /status/{run_id} for progress."
}
```

---

### GET `/api/v1/status/{run_id}`

Check run status and current routing decision.

```bash
curl http://localhost:8000/api/v1/status/3f2a1b4c-...
```

Response:
```json
{
  "run_id": "3f2a1b4c-...",
  "status": "awaiting_review",
  "routing_decision": "review",
  "risk_score": 62,
  "error": null
}
```

Status values: `pending` → `ingesting` → `extracting` → `retrieving` → `scoring` → `awaiting_review` | `approved` | `rejected`

---

### POST `/api/v1/review/{run_id}`

Submit a human review decision to resume a paused graph.
Only valid when `status == awaiting_review`.

```bash
curl -X POST http://localhost:8000/api/v1/review/3f2a1b4c-... \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_id": "analyst@bank.com",
    "override_decision": "approve",
    "notes": "Verified financials independently. Approve with covenant monitoring."
  }'
```

Response:
```json
{
  "run_id": "3f2a1b4c-...",
  "status": "deciding",
  "message": "Review accepted. Graph resumed."
}
```

---

### GET `/api/v1/decision/{run_id}`

Get the final structured decision with full audit trail.

```bash
curl http://localhost:8000/api/v1/decision/3f2a1b4c-...
```

Response:
```json
{
  "run_id": "3f2a1b4c-...",
  "document_id": "7e8d9f0a-...",
  "routing_decision": "approve",
  "risk_score": 62,
  "reasoning": "Borrower shows moderate leverage but stable revenue trend...",
  "entities": {
    "borrower_name": "Acme Corp",
    "loan_amount": 2500000,
    "credit_score": 720,
    "risk_indicators": ["elevated DTI", "margin compression"]
  },
  "human_review": {
    "reviewer_id": "analyst@bank.com",
    "override_decision": "approve",
    "notes": "Verified financials independently.",
    "reviewed_at": "2024-04-01T14:32:00Z"
  },
  "audit_trail": [
    { "step": "ingest_node", "duration_ms": 342, "timestamp": "..." },
    { "step": "extract_node", "duration_ms": 1821, "timestamp": "..." },
    { "step": "retrieval_node", "duration_ms": 654, "timestamp": "..." },
    { "step": "score_node", "duration_ms": 2103, "timestamp": "..." },
    { "step": "route_node", "duration_ms": 2, "timestamp": "..." },
    { "step": "human_review_node", "duration_ms": 47832, "timestamp": "..." },
    { "step": "decision_node", "duration_ms": 189, "timestamp": "..." }
  ],
  "decided_at": "2024-04-01T14:32:01Z"
}
```

---

## Evaluation Harness

Run against 20 synthetic financial documents (6 approve, 7 review, 7 reject cases):

```bash
python -m eval.runner
```

Outputs JSON + Markdown report to `eval/results/`. Metrics reported:
- Accuracy (% correct routing decisions)
- Average latency per document (ms)
- Token cost per decision (input + output)
- False positive rate (approved when should reject)
- False negative rate (rejected when should approve)

---

## Observability

Every node emits a structured log entry captured by Application Insights:

```json
{
  "node": "score_node",
  "run_id": "3f2a1b4c-...",
  "duration_ms": 2103.45,
  "input_tokens": 1842,
  "output_tokens": 387,
  "total_tokens": 2229,
  "timestamp": "2024-04-01T14:31:58.123Z"
}
```

Dashboards available in Azure Monitor for latency, token spend, and decision distribution.

---

## GitHub Actions Secrets Required

| Secret | Description |
|--------|-------------|
| `AZURE_CREDENTIALS` | Service principal JSON (`az ad sp create-for-rbac`) |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `AZURE_RESOURCE_GROUP` | Target resource group name |
| `AZURE_CONTAINER_REGISTRY` | ACR login server (e.g. `myreg.azurecr.io`) |
| `ACR_NAME` | ACR name (without `.azurecr.io`) |
| `ACR_USERNAME` | ACR admin username |
| `ACR_PASSWORD` | ACR admin password |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_SEARCH_API_KEY` | Azure AI Search admin key |

---

## Project Structure

```
riskscout/
├── src/riskscout/
│   ├── agent/
│   │   ├── graph.py          # LangGraph StateGraph assembly
│   │   ├── state.py          # TypedDict state + Pydantic models
│   │   └── nodes/            # One file per node (7 nodes)
│   ├── api/
│   │   ├── main.py           # FastAPI app + lifespan
│   │   └── routes.py         # All 4 API endpoints
│   ├── infrastructure/
│   │   ├── cosmos.py         # Cosmos DB async client
│   │   ├── search.py         # Azure AI Search client + index management
│   │   └── observability.py  # OpenTelemetry + App Insights setup
│   └── config.py             # pydantic-settings configuration
├── eval/
│   ├── dataset.py            # 20 synthetic labeled documents
│   ├── runner.py             # Evaluation harness with concurrency
│   └── report.py             # JSON + Markdown report generation
├── infra/                    # Bicep IaC modules
├── .github/workflows/        # CI/CD pipeline
├── Dockerfile                # Multi-stage production image
└── pyproject.toml
```

---

Built by [Venky Krishnaswamy](https://theaiguru.dev)
