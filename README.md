# Payment Fraud Detection — DevSecOps Pipeline on Azure

A production-grade **microservices fraud detection system** built to demonstrate deep CircleCI expertise. Features dynamic config, matrix testing, fan-out/fan-in security gates, and automated deployment to Azure Container Apps via Terraform-managed infrastructure.

---

## Table of Contents

- [What This Project Does](#what-this-project-does)
- [Architecture](#architecture)
- [Services](#services)
- [CI/CD Pipeline](#cicd-pipeline)
- [CircleCI Features Demonstrated](#circleci-features-demonstrated)
- [Security Gates](#security-gates)
- [Infrastructure](#infrastructure)
- [GitFlow Strategy](#gitflow-strategy)
- [PCI-DSS Control Mapping](#pci-dss-control-mapping)
- [Running Locally](#running-locally)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)

---

## What This Project Does

Simulates a real-world payment processing system where every transaction is **scored for fraud risk** before approval. The system consists of two independent microservices communicating over HTTPS, deployed to Azure Container Apps, with a full DevSecOps pipeline that enforces security controls on every push.

**Key capabilities:**

- Rule-based fraud scoring across merchant reputation, transaction amount, and card patterns
- API key authentication with timing-attack-safe comparison
- Automated secret scanning, SAST, and container CVE scanning on every commit
- Dynamic CI/CD — only rebuilds the service that actually changed
- Matrix testing across Python 3.10 and 3.11 simultaneously
- Terraform-managed Azure infrastructure with remote state

---

## Architecture

```
Developer pushes to dev branch
          │
          ▼
┌─────────────────────────────────────────────────────┐
│                  CircleCI Pipeline                   │
│                                                      │
│  config.yml (setup)                                  │
│     └── path-filtering → continue_config.yml         │
│                                                      │
│  Per-service pipeline (only changed service runs):   │
│                                                      │
│  secret-scan ──────────────────────┐                 │
│  sast-scan ─────────────────────── ├── (fan-out)     │
│  test (python 3.10) ───────────── ─┤                 │
│  test (python 3.11) ───────────────┘                 │
│                    │                                 │
│                    ▼ (fan-in — all must pass)        │
│              build-and-scan                          │
│                    │                                 │
│                    ▼                                 │
│                 deploy                               │
│            (azure-dev context)                       │
└─────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────┐
│              Azure Container Apps                    │
│                                                      │
│  transaction-api ──► fraud-scorer                    │
│       :8000               :8001                      │
│                                                      │
│  POST /transaction    POST /score                    │
│  GET  /health         GET  /health                   │
└─────────────────────────────────────────────────────┘
```

---

## Services

### Transaction API (`services/transaction-api`)

**Responsibility:** Accept incoming payment transactions, call the fraud scorer, and approve or block based on risk.

**Endpoints:**

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | None | Health check |
| `POST` | `/transaction` | `x-api-key` | Submit transaction for fraud check |
| `GET` | `/docs` | None | Swagger UI |

**Flow:**

```
Client → POST /transaction
           │
           ▼
      verify API key
           │
           ▼
      call fraud-scorer /score
           │
      ┌────┴────┐
   high risk   low/medium risk
      │              │
   403 Blocked    200 Approved
```

---

### Fraud Scorer (`services/fraud-scorer`)

**Responsibility:** Score a transaction based on rule-based signals. Returns a numeric score (0–100) and risk level.

**Scoring Rules:**

| Signal | Condition | Score Added |
|--------|-----------|-------------|
| Merchant reputation | Known bad merchant | +80 |
| Transaction amount | ≥ $10,000 | +60 |
| Transaction amount | ≥ $5,000 | +30 |
| Card pattern | Suspicious last4 (`0000`, `9999`) | +40 |

**Risk Thresholds:**

| Score Range | Risk Level | Action |
|-------------|------------|--------|
| 0 – 59 | `low` / `medium` | Approved |
| 60 – 100 | `high` | Blocked (403) |

---

## CI/CD Pipeline

### Entry Point — `config.yml`

```yaml
setup: true
```

Uses the **continuation orb** to implement dynamic config. On every push, a `filter-paths` job compares changed files against `origin/main` and sets pipeline parameters:

| Changed Path | Parameter Set |
|---|---|
| `services/transaction-api/**` | `run-transaction-api: true` |
| `services/fraud-scorer/**` | `run-fraud-scorer: true` |
| `infra/**` | `run-infra: true` |

**Only the affected service pipeline runs.** Unchanged services are skipped entirely — saving CI credits and reducing noise.

---

### Pipeline — `continue_config.yml`

#### Jobs

| Job | Image | Purpose |
|-----|-------|---------|
| `secret-scan` | `cimg/python:3.11` | TruffleHog v3 scans entire repo for leaked credentials |
| `sast-scan` | `cimg/python:3.11` | Semgrep scans service directory for insecure code patterns |
| `test` | `cimg/python:3.10` / `3.11` | pytest runs unit tests — matrix across two Python versions |
| `build-and-scan` | `cimg/python:3.11` | Docker build + Trivy CVE scan on built image |
| `deploy` | `cimg/azure:2024.03` | `az containerapp update` — deploys new image to Azure |

#### Fan-Out / Fan-In Pattern

```
secret-scan ──┐
sast-scan ────┤ (fan-out — all run in parallel)
test-3.10 ────┤
test-3.11 ────┘
              │
              ▼ (fan-in — build-and-scan waits for all four)
        build-and-scan
              │
              ▼
           deploy
```

`build-and-scan` only starts when **all** parallel jobs pass. A single failure blocks the pipeline.

#### Matrix Jobs

```yaml
test:
  matrix:
    parameters:
      service: [transaction-api]
      python-version: ["3.10", "3.11"]
```

CircleCI generates two parallel jobs: `test-3.10-transaction-api` and `test-3.11-transaction-api`. Both must pass before `build-and-scan` proceeds.

---

## CircleCI Features Demonstrated

| Feature | Where Used | Why |
|---------|------------|-----|
| **Dynamic config** | `config.yml` → `continue_config.yml` | Only builds changed service — critical at scale |
| **Path filtering** | `filter-paths` job | Detects which service changed using `git diff` |
| **Pipeline parameters** | `run-transaction-api`, `run-fraud-scorer` | Controls which workflow runs |
| **Parameterized jobs** | `test`, `sast-scan`, `build-and-scan`, `deploy` | One job definition handles both services |
| **Matrix jobs** | `test` job | Parallel testing across Python 3.10 and 3.11 |
| **Fan-out / Fan-in** | Security gates → `build-and-scan` | All checks must pass before build |
| **Contexts** | `azure-dev` on deploy job | Secure credential injection per environment |
| **Branch filtering** | `deploy` job | Only deploys on `dev` branch, not PRs |
| **Continuation orb** | `config.yml` | Enables dynamic config handoff |
| **`$CIRCLE_SHA1`** | Docker image tag | Traces every image back to exact commit |

---

## Security Gates

| Gate | Tool | Blocks On |
|------|------|-----------|
| Secret scanning | TruffleHog v3 | API keys, credentials, tokens in code |
| SAST | Semgrep (`p/python`) | Insecure code patterns, hardcoded secrets |
| Unit tests | pytest | Any test failure |
| Container CVE scan | Trivy | `CRITICAL` severity CVEs in Docker image |

**All gates run in parallel.** A failure in any one blocks the build immediately.

---

## Infrastructure

### Stack

| Component | Technology |
|-----------|------------|
| Container hosting | Azure Container Apps |
| IaC | Terraform v1.15+ |
| State backend | Azure Blob Storage (`tfstatepaymentfraud`) |
| Container registry | Docker Hub |

### Terraform Structure

```
infra/terraform/
├── modules/
│   ├── resource-group/     # Reusable RG module
│   └── container-app/      # Reusable Container App module
└── environments/
    ├── dev/                # Dev environment config
    └── prod/               # Prod environment config (future)
```

**Design decisions:**

- **Modular** — `container-app` module is reused for both services. No duplication.
- **Remote state** — Terraform state stored in Azure Blob Storage with locking. Safe for CI/CD.
- **Mandatory tagging** — All resources tagged with `Environment`, `Project`, `Owner`, `ManagedBy`.
- **Scale to zero** — `min_replicas = 0` on transaction-api keeps costs minimal.
- **Fraud scorer always warm** — `min_replicas = 1` prevents cold-start timeouts.

### Resource Tags

```hcl
tags = {
  Environment = "dev"
  Project     = "payment-fraud-detection"
  Owner       = "hemant"
  ManagedBy   = "terraform"
}
```

---

## GitFlow Strategy

```
main ──────────────────────────────────────► production
  ▲                                              ▲
  │ PR + merge                        PR + merge │
  │                                              │
dev ──────────────────────────────────────► staging deploy
  ▲
  │ feature branches (future)
```

| Branch | Pipeline Trigger | Deploys To |
|--------|-----------------|------------|
| `dev` | Full pipeline + deploy | Azure dev environment |
| `main` | Full pipeline (approval gate — future) | Azure prod environment |

**Rule:** No direct commits to `main`. All changes flow through `dev` via PR.

---

## PCI-DSS Control Mapping

| PCI-DSS Requirement | Control | Enforced By |
|---------------------|---------|-------------|
| Req 6.3 — Identify vulnerabilities | Static code analysis | Semgrep SAST |
| Req 6.4 — Protect public-facing apps | Container CVE scanning | Trivy |
| Req 7.1 — Restrict access | API key on all endpoints | `x-api-key` header |
| Req 8.2 — No hardcoded credentials | Secret detection on every push | TruffleHog v3 |
| Req 10.2 — Audit trail | Image tagged with Git SHA | `$CIRCLE_SHA1` |
| Req 12.3 — Controlled changes | Branch protection + CI gates | CircleCI + GitFlow |

---

## Running Locally

### Prerequisites

- Python 3.10+
- Docker

### Fraud Scorer

```bash
cd services/fraud-scorer
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload
```

### Transaction API

```bash
cd services/transaction-api
pip install -r requirements.txt

export API_KEY=test-key
export FRAUD_SCORER_URL=http://localhost:8001

uvicorn main:app --port 8000 --reload
```

### Run Tests

```bash
# Fraud Scorer
cd services/fraud-scorer
pytest tests/ -v

# Transaction API
cd services/transaction-api
pytest tests/ -v
```

---

## Environment Variables

### Transaction API

| Variable | Description | Required |
|----------|-------------|----------|
| `API_KEY` | API key for authenticating requests | Yes |
| `FRAUD_SCORER_URL` | Internal URL of fraud scorer service | Yes |

### CircleCI Contexts

#### `azure-dev`

| Variable | Description |
|----------|-------------|
| `AZURE_CLIENT_ID` | Service principal app ID |
| `AZURE_CLIENT_SECRET` | Service principal password |
| `AZURE_TENANT_ID` | Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |

---

## Project Structure

```
payment-fraud-detection/
├── .circleci/
│   ├── config.yml              # Dynamic config entry point
│   └── continue_config.yml     # Full pipeline logic
├── services/
│   ├── transaction-api/
│   │   ├── main.py             # FastAPI app
│   │   ├── requirements.txt
│   │   ├── Dockerfile          # Alpine, non-root
│   │   └── tests/
│   │       └── test_main.py    # 5 unit tests
│   └── fraud-scorer/
│       ├── main.py             # Rule-based scoring engine
│       ├── requirements.txt
│       ├── Dockerfile          # Alpine, non-root
│       └── tests/
│           └── test_main.py    # 7 unit tests
└── infra/
    └── terraform/
        ├── modules/
        │   ├── resource-group/
        │   └── container-app/
        └── environments/
            ├── dev/
            └── prod/
```

---

## API Reference

### Transaction API

**Base URL:** `https://transaction-api-dev.<region>.azurecontainerapps.io`

#### `POST /transaction`

```bash
curl -X POST <BASE_URL>/transaction \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-api-key" \
  -d '{"card_last4": "1234", "amount": 100.0, "merchant": "amazon.com"}'
```

**Approved response (200):**
```json
{"status": "approved", "fraud_score": 0}
```

**Blocked response (403):**
```json
{"detail": "Transaction blocked — high fraud risk"}
```

**Swagger UI:** `<BASE_URL>/docs`

---

### Fraud Scorer

**Base URL:** `https://fraud-scorer-dev.<region>.azurecontainerapps.io`

#### `POST /score`

```bash
curl -X POST <BASE_URL>/score \
  -H "Content-Type: application/json" \
  -d '{"card_last4": "1234", "amount": 15000.0, "merchant": "shadystore.com"}'
```

**Response:**
```json
{"score": 100, "risk": "high"}
```

---

## Roadmap

- [ ] Manual approval gate before prod deploy
- [ ] `prod` environment Terraform config
- [ ] Azure Key Vault for secret management
- [ ] OWASP ZAP DAST scanning
- [ ] Rate limiting on transaction API
- [ ] Audit logging to Azure Monitor
- [ ] Luhn algorithm card validation
