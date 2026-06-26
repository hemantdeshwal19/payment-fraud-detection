Payment Fraud Detection — DevSecOps Pipeline on Azure

A production-grade microservices fraud detection system built to demonstrate deep CircleCI expertise. Features dynamic config, matrix testing, fan-out/fan-in security gates, and automated deployment to Azure Container Apps via Terraform-managed infrastructure.


Table of Contents


What This Project Does
Architecture
Services
CI/CD Pipeline
CircleCI Features Demonstrated
Security Gates
Infrastructure
GitFlow Strategy
PCI-DSS Control Mapping
Running Locally
Environment Variables
Project Structure
API Reference



What This Project Does

Simulates a real-world payment processing system where every transaction is scored for fraud risk before approval. The system consists of two independent microservices communicating over HTTPS, deployed to Azure Container Apps, with a full DevSecOps pipeline that enforces security controls on every push.

Key capabilities:


Rule-based fraud scoring across merchant reputation, transaction amount, and card patterns
API key authentication with timing-attack-safe comparison
Automated secret scanning, SAST, and container CVE scanning on every commit
Dynamic CI/CD — only rebuilds the service that actually changed
Matrix testing across Python 3.10 and 3.11 simultaneously
Terraform-managed Azure infrastructure with remote state



Architecture

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


Services

Transaction API (services/transaction-api)

Responsibility: Accept incoming payment transactions, call the fraud scorer, and approve or block based on risk.

Endpoints:

MethodPathAuthDescriptionGET/healthNoneHealth checkPOST/transactionx-api-keySubmit transaction for fraud checkGET/docsNoneSwagger UI

Flow:

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


Fraud Scorer (services/fraud-scorer)

Responsibility: Score a transaction based on rule-based signals. Returns a numeric score (0–100) and risk level.

Scoring Rules:

SignalConditionScore AddedMerchant reputationKnown bad merchant+80Transaction amount≥ $10,000+60Transaction amount≥ $5,000+30Card patternSuspicious last4 (0000, 9999)+40

Risk Thresholds:

Score RangeRisk LevelAction0 – 59low / mediumApproved60 – 100highBlocked (403)


CI/CD Pipeline

Entry Point — config.yml

yamlsetup: true

Uses the continuation orb to implement dynamic config. On every push, a filter-paths job compares changed files against origin/main and sets pipeline parameters:

Changed PathParameter Setservices/transaction-api/**run-transaction-api: trueservices/fraud-scorer/**run-fraud-scorer: trueinfra/**run-infra: true

Only the affected service pipeline runs. Unchanged services are skipped entirely — saving CI credits and reducing noise.


Pipeline — continue_config.yml

Jobs

JobImagePurposesecret-scancimg/python:3.11TruffleHog v3 scans entire repo for leaked credentialssast-scancimg/python:3.11Semgrep scans service directory for insecure code patternstestcimg/python:3.10 / 3.11pytest runs unit tests — matrix across two Python versionsbuild-and-scancimg/python:3.11Docker build + Trivy CVE scan on built imagedeploycimg/azure:2024.03az containerapp update — deploys new image to Azure

Fan-Out / Fan-In Pattern

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

build-and-scan only starts when all parallel jobs pass. A single failure blocks the pipeline.

Matrix Jobs

yamltest:
  matrix:
    parameters:
      service: [transaction-api]
      python-version: ["3.10", "3.11"]

CircleCI generates two parallel jobs: test-3.10-transaction-api and test-3.11-transaction-api. Both must pass before build-and-scan proceeds.


CircleCI Features Demonstrated

FeatureWhere UsedWhyDynamic configconfig.yml → continue_config.ymlOnly builds changed service — critical at scalePath filteringfilter-paths jobDetects which service changed using git diffPipeline parametersrun-transaction-api, run-fraud-scorerControls which workflow runsParameterized jobstest, sast-scan, build-and-scan, deployOne job definition handles both servicesMatrix jobstest jobParallel testing across Python 3.10 and 3.11Fan-out / Fan-inSecurity gates → build-and-scanAll checks must pass before buildContextsazure-dev on deploy jobSecure credential injection per environmentBranch filteringdeploy jobOnly deploys on dev branch, not PRsContinuation orbconfig.ymlEnables dynamic config handoff$CIRCLE_SHA1Docker image tagTraces every image back to exact commit


Security Gates

GateToolBlocks OnSecret scanningTruffleHog v3API keys, credentials, tokens in codeSASTSemgrep (p/python)Insecure code patterns, hardcoded secretsUnit testspytestAny test failureContainer CVE scanTrivyCRITICAL severity CVEs in Docker image

All gates run in parallel. A failure in any one blocks the build immediately.


Infrastructure

Stack

ComponentTechnologyContainer hostingAzure Container AppsIaCTerraform v1.15+State backendAzure Blob Storage (tfstatepaymentfraud)Container registryDocker Hub

Terraform Structure

infra/terraform/
├── modules/
│   ├── resource-group/     # Reusable RG module
│   └── container-app/      # Reusable Container App module
└── environments/
    ├── dev/                # Dev environment config
    └── prod/               # Prod environment config (future)

Design decisions:


Modular — container-app module is reused for both services. No duplication.
Remote state — Terraform state stored in Azure Blob Storage with locking. Safe for CI/CD.
Mandatory tagging — All resources tagged with Environment, Project, Owner, ManagedBy.
Scale to zero — min_replicas = 0 on transaction-api keeps costs minimal.
Fraud scorer always warm — min_replicas = 1 prevents cold-start timeouts.


Resource Tags

hcltags = {
  Environment = "dev"
  Project     = "payment-fraud-detection"
  Owner       = "hemant"
  ManagedBy   = "terraform"
}


GitFlow Strategy

main ──────────────────────────────────────► production
  ▲                                              ▲
  │ PR + merge                        PR + merge │
  │                                              │
dev ──────────────────────────────────────► staging deploy
  ▲
  │ feature branches (future)

BranchPipeline TriggerDeploys TodevFull pipeline + deployAzure dev environmentmainFull pipeline (approval gate — future)Azure prod environment

Rule: No direct commits to main. All changes flow through dev via PR.


PCI-DSS Control Mapping

PCI-DSS RequirementControlEnforced ByReq 6.3 — Identify vulnerabilitiesStatic code analysisSemgrep SASTReq 6.4 — Protect public-facing appsContainer CVE scanningTrivyReq 7.1 — Restrict accessAPI key on all endpointsx-api-key headerReq 8.2 — No hardcoded credentialsSecret detection on every pushTruffleHog v3Req 10.2 — Audit trailImage tagged with Git SHA$CIRCLE_SHA1Req 12.3 — Controlled changesBranch protection + CI gatesCircleCI + GitFlow


Running Locally

Prerequisites


Python 3.10+
Docker


Fraud Scorer

bashcd services/fraud-scorer
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload

Transaction API

bashcd services/transaction-api
pip install -r requirements.txt

export API_KEY=test-key
export FRAUD_SCORER_URL=http://localhost:8001

uvicorn main:app --port 8000 --reload

Run Tests

bash# Fraud Scorer
cd services/fraud-scorer
pytest tests/ -v

# Transaction API
cd services/transaction-api
pytest tests/ -v


Environment Variables

Transaction API

VariableDescriptionRequiredAPI_KEYAPI key for authenticating requestsYesFRAUD_SCORER_URLInternal URL of fraud scorer serviceYes

CircleCI Contexts

azure-dev

VariableDescriptionAZURE_CLIENT_IDService principal app IDAZURE_CLIENT_SECRETService principal passwordAZURE_TENANT_IDAzure tenant IDAZURE_SUBSCRIPTION_IDAzure subscription ID


Project Structure

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


API Reference

Transaction API

Base URL: https://transaction-api-dev.<region>.azurecontainerapps.io

POST /transaction

bashcurl -X POST <BASE_URL>/transaction \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-api-key" \
  -d '{"card_last4": "1234", "amount": 100.0, "merchant": "amazon.com"}'

Approved response (200):

json{"status": "approved", "fraud_score": 0}

Blocked response (403):

json{"detail": "Transaction blocked — high fraud risk"}

Swagger UI: <BASE_URL>/docs


Fraud Scorer

Base URL: https://fraud-scorer-dev.<region>.azurecontainerapps.io

POST /score

bashcurl -X POST <BASE_URL>/score \
  -H "Content-Type: application/json" \
  -d '{"card_last4": "1234", "amount": 15000.0, "merchant": "shadystore.com"}'

Response:

json{"score": 100, "risk": "high"}


Roadmap


 Manual approval gate before prod deploy
 prod environment Terraform config
 Azure Key Vault for secret management
 OWASP ZAP DAST scanning
 Rate limiting on transaction API
 Audit logging to Azure Monitor
 Luhn algorithm card validation
