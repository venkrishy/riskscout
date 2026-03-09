# RiskScout — Real-Document API Test

Three real SEC 10-K filings tested against the live API.
All files are in `eval/real-docs/`.

---

## Documents

| File | Company | Source | Risk Profile |
|------|---------|--------|-------------|
| `dollar-general-10k-2025.txt` | Dollar General Corp | 10-K filed 2025-03-21 (FY2024) | Healthy retailer, high-volume low-margin |
| `rite-aid-10k-2023.txt` | Rite Aid Corp | 10-K filed 2023-05-01 (FY2023) | Filed Chapter 11 bankruptcy Oct 2023 |
| `bed-bath-beyond-10k-2023.txt` | Bed Bath & Beyond | 10-K filed 2023-06-14 (FY2022) | Filed Chapter 11 Apr 2023, liquidated Aug 2023 |

All excerpts are the **Liquidity & Capital Resources / Going Concern** section — the part a credit analyst reads first.
Downloaded directly from SEC EDGAR (no paywalls, all public).

---

## How to Run

### Step 1 — Upload a document

```bash
curl -X POST https://riskscout-prod-app.prouddesert-00e9f2f2.eastus2.azurecontainerapps.io/api/v1/analyze \
  -F "file=@eval/real-docs/dollar-general-10k-2025.txt"
```

Response (HTTP 202):
```json
{
  "run_id": "b1e8db1a-6104-4712-9da4-6b75f807db47",
  "document_id": "ab143aff-b348-4d6f-b444-8e6a5f1d9e23",
  "status": "ingesting",
  "message": "Document accepted. Poll /status/{run_id} for progress."
}
```

### Step 2 — Poll status (every few seconds)

```bash
curl https://riskscout-prod-app.prouddesert-00e9f2f2.eastus2.azurecontainerapps.io/api/v1/status/{run_id}
```

Status values in order: `ingesting` → `extracting` → `retrieving` → `scoring` → `rejected | approved | awaiting_review | failed`

### Step 3 — Fetch decision (once status is terminal)

```bash
curl https://riskscout-prod-app.prouddesert-00e9f2f2.eastus2.azurecontainerapps.io/api/v1/decision/{run_id}
```

### Step 3b — Submit human review (if status = awaiting_review)

This exercises LangGraph's `interrupt()` / resume pattern:

```bash
curl -X POST https://riskscout-prod-app.prouddesert-00e9f2f2.eastus2.azurecontainerapps.io/api/v1/review/{run_id} \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_id": "analyst-001",
    "override_decision": "reject",
    "notes": "Confirmed going concern language. Do not extend credit.",
    "approved": false
  }'
```

---

## Test Results (2026-03-09)

### Dollar General Corp — FY2024 10-K

```
run_id   : b1e8db1a-6104-4712-9da4-6b75f807db47
score    : 85
routing  : reject
status   : rejected
pipeline : ingest → extract → retrieve → score → route
```

**Extracted entities:**
- Borrower: Dollar General Corp (corporation)
- Loan amount: $2,375,000,000 (revolving credit facility)
- Risk indicators: high leverage, covenant violations
- Collateral: none extracted

**Model reasoning:**
> "The loan amount of $2.375 billion is substantial, and the borrower has high leverage and covenant violations, which are significant risk indicators. The lack of collateral and financial metrics further increases the risk."

**Notes:** Dollar General is actually a financially sound company (S&P BBB rated). The high score is expected given we only fed the *risk factors / liquidity* section of the 10-K — which is intentionally cautionary — and the policy index in Azure AI Search is empty (no credit policy documents have been loaded). Without calibration policies, the model scores conservatively. See [Policy Index](#policy-index-note) below.

---

### Rite Aid Corp — FY2023 10-K (pre-bankruptcy)

```
run_id   : 8d766b8f-0e4a-4928-9dd7-e5302ea6ba33
score    : 85
routing  : reject
status   : rejected
pipeline : ingest → extract → retrieve → score → route
```

**Extracted entities:**
- Borrower: Rite Aid Corp (corporation)
- Loan amount: $1,600,000,000
- Loan purpose: working capital, debt service, capex
- Collateral: cash, receivables, inventory, prescription files, IP, equipment
- Risk indicators: high leverage, bankruptcy

**Model reasoning:**
> "The borrower is seeking a substantial loan amount of $1.6 billion without providing key financial metrics such as annual revenue, net income, or debt-to-income ratio. The presence of high leverage and bankruptcy as risk indicators significantly increases the risk profile."

**Notes:** Correct outcome. Rite Aid filed Chapter 11 five months after this filing. Bankruptcy was explicitly flagged as a risk indicator by the extraction node.

---

### Bed Bath & Beyond — FY2022 10-K (final filing)

```
run_id   : f4a8404c-0d2b-4b9c-8220-ed2ee6037e91
score    : 50
routing  : review
status   : awaiting_review  ← LangGraph interrupt() fired
pipeline : ingest → extract → retrieve → score → route → human_review (paused)
```

**Status response while awaiting review:**
```json
{
  "run_id": "f4a8404c-0d2b-4b9c-8220-ed2ee6037e91",
  "status": "awaiting_review",
  "routing_decision": "review",
  "risk_score": 50,
  "error": "extract_node: Expecting ',' delimiter: line 5 column 28 (char 115)"
}
```

**Notes:** Score of 50 lands in the human-review band (40–79), correctly triggering `interrupt()`. The extract node had a JSON parsing error (GPT-4o returned malformed JSON for this document) — the pipeline continued with a partial entity set rather than failing hard. BBB filed Chapter 11 six weeks after this filing. A human reviewer submitting `override_decision: reject` would complete the graph and persist to Cosmos DB.

---

## Summary Table

| Company | Expected | Score | Routing | Terminal Status |
|---------|---------|-------|---------|----------------|
| Dollar General (healthy) | approve | 85 | reject | rejected |
| Rite Aid (pre-bankruptcy) | reject | 85 | reject | rejected |
| Bed Bath & Beyond (pre-bankruptcy) | reject | 50 | review | awaiting_review |

---

## Policy Index Note

The Azure AI Search policy index (`riskscout-policies`) is currently empty. This means the retrieval node returns no policy passages, and the scoring node has no calibration anchor — it scores purely from document language. Two consequences:

1. Risk-factor sections (which are always written cautiously) get inflated scores
2. The approve band (score < 40) will never trigger without policy documents

**To fix:** Load credit policy documents into the search index via the ingest endpoint. Example policies to add: acceptable LTV ratios, minimum DSCR thresholds, industry concentration limits, covenant definitions. Once loaded, the scoring node will cite specific policy violations and produce more differentiated scores.

---

## Pipeline Nodes (all 7)

```
ingest_node      Parse & chunk the document, index to Azure AI Search
extract_node     GPT-4o extracts structured entities (borrower, amount, ratios, risk flags)
retrieval_node   Embed query, hybrid vector+keyword search against policy index
score_node       GPT-4o scores 0-100 with reasoning, citing policy passages
route_node       Threshold gate: score>=80 reject, score<40 approve, 40-79 review
human_review     LangGraph interrupt() — pauses graph, waits for POST /review/{run_id}
decision_node    Assembles FinalDecision, persists full audit trail to Cosmos DB
```
