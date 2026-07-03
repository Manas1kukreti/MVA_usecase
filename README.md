# MVA Data Profiling Engine

**Multi-Variance Analysis — Schema, Quality, Hierarchy, Readiness, and Chart Intelligence**

A production-structured backend that profiles CSV/XLSX datasets, classifies them into domains, validates hierarchy structures, assesses data quality, evaluates AI-readiness, and generates typed chart specifications.

## Architecture

```
File Upload → Validation → Profiling → Type Refinement → Semantic Candidates
    → Schema Intelligence → Domain Classification → Category Classification
    → Hierarchy Inference → Business Rules → Quality Assessment
    → AI Readiness → Chart Generation → Persist Results → Cleanup
```

Every stage produces typed results. Non-critical failures do not destroy successful upstream results.

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 16 (or use Docker Compose)
- Docker & Docker Compose (optional)

### Local Development

```bash
# Clone and install
pip install -e ".[dev]"

# Copy env file
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000

# Run tests
python -m pytest tests/ -v
```

### Docker Compose

```bash
docker-compose up --build
# API at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/profile-runs` | Create profiling run |
| GET | `/api/v1/profile-runs/{id}` | Run summary |
| GET | `/api/v1/profile-runs/{id}/result` | Full result |
| GET | `/api/v1/profile-runs/{id}/columns` | Column profiles |
| GET | `/api/v1/profile-runs/{id}/quality` | Quality assessments |
| GET | `/api/v1/profile-runs/{id}/readiness` | AI readiness |
| GET | `/api/v1/profile-runs/{id}/hierarchy` | Hierarchy chain |
| GET | `/api/v1/profile-runs/{id}/charts` | Chart specs |
| POST | `/api/v1/profile-runs/{id}/charts/{cid}/drill-down` | Drill-down |
| GET | `/api/v1/rule-suggestions` | List suggestions |
| POST | `/api/v1/rule-suggestions/{id}/approve` | Approve rule |
| POST | `/api/v1/rule-suggestions/{id}/reject` | Reject rule |

## Example Usage

```bash
curl -X POST http://localhost:8000/api/v1/profile-runs \
  -F "file=@payments.csv" \
  -F "primary_domain=Payments" \
  -F 'schema_metadata={"columns":[{"column_name":"amount","description":"Payment amount","mandatory":true}]}'
```

## Supported Domains

| Primary | Secondary Domains |
|---------|-------------------|
| Payments | Authorization, Clearing, Settlement, Fraud |
| Customer | CRM, Customer Satisfaction, Loyalty |
| HR | Employee, Payroll, Recruitment |
| Finance | Revenue, P&L, Forecasting |

## Adding a New Domain

1. Create `config/domains/insurance.yaml` following the existing structure
2. Define secondary domains with keywords and semantic roles
3. Add hierarchy templates
4. Add chart templates
5. Add business rules

**No Python code changes required.** The engine loads configuration dynamically.

## Configuration

All domain-specific behavior is in `config/` YAML files:

- `config/domains/*.yaml` — domain definitions, secondary domains, templates, rules
- `config/quality_weights.yaml` — quality dimension weights
- `config/readiness_weights.yaml` — AI readiness weight profiles
- `config/hierarchy_thresholds.yaml` — FD validation thresholds
- `config/chart_policy.yaml` — chart generation policy
- `config/application.yaml` — global thresholds

## Key Design Principles

### Deterministic Before LLM
- Physical types: Pandas + parse ratios (never LLM)
- Statistics: NumPy/Pandas (never LLM)
- Identifier detection: cardinality analysis (never LLM)
- Rule enforcement: typed engine (never LLM)
- FD validation: groupby aggregation (never LLM)

### LLM Only For Semantic Reasoning
- Confirm/override semantic types
- Classify ambiguous secondary domains
- Propose business rule candidates
- Generate recommendation text

### Raw Data Lifecycle
- Uploaded file → temp directory (UUID-scoped)
- Loaded into DataFrame transiently
- Processed through pipeline
- Temp file deleted on success AND failure
- Only derived metadata persisted to PostgreSQL
- No raw rows in database

## Data Quality Dimensions

| Dimension | Formula | When Not Assessable |
|-----------|---------|---------------------|
| Completeness | 1 - null_count/total for mandatory cols | No mandatory columns defined |
| Uniqueness | 1 - dupes/total for expected-unique cols | No expected-unique columns |
| Validity | pass/checked for range/allowed rules | No validity rules configured |
| Conformity | pass/checked for regex rules | No conformity rules |
| Consistency | 1 - contradictions/checked | No cross-field rules |
| Business Rules | pass/total across all active rules | No rules evaluated |
| Timeliness | Requires SLA config | Always (v1) |
| Integrity | Requires reference data | Always (v1) |
| Accuracy | Requires trusted reference | Always (v1) |
| Semantic Quality | Weighted avg of confidences | No SI results |

**Overall score** = `Σ(weight × score) / Σ(weight)` for assessed dimensions only.

## AI Readiness

All three assessments reuse the same quality evidence with different weight profiles:

- **Analytics**: completeness, dimensions, metrics, grain, temporal fields
- **ML**: completeness, feature coverage, identifier contamination, row count
- **LLM**: description coverage, semantic quality, schema clarity

Thresholds: ≥80 ready, ≥60 partially_ready, <60 not_ready

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific phase
python -m pytest tests/unit/test_quality.py -v

# With coverage
python -m pytest tests/ --cov=app --cov-report=term-missing
```

## Running Migrations

```bash
# Apply all migrations
alembic upgrade head

# Generate new migration after model changes
alembic revision --autogenerate -m "description"

# Rollback one step
alembic downgrade -1
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | postgresql://... | PostgreSQL connection |
| MAX_UPLOAD_SIZE_MB | 25 | Max file size |
| MAX_DATASET_ROWS | 200000 | Max rows |
| MAX_DATASET_COLUMNS | 200 | Max columns |
| PROCESSING_TIMEOUT_SECONDS | 120 | Pipeline timeout |
| MIN_CUBE_GROUP_SIZE | 5 | Small-group suppression |
| LLM_PROVIDER | local | LLM backend |
| LLM_API_KEY | | OpenAI API key |
| LOG_LEVEL | INFO | Logging level |

## Known Limitations

- Drill-down cubes not yet persisted to PostgreSQL (in-memory for demo)
- LLM integration requires API key; without it, deterministic fallback is used
- No authentication/authorization in v1
- Single-worker synchronous processing (job abstraction ready for async migration)
- XLSX limited to single-sheet workbooks
