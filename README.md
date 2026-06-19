# Guardrails for Structured Outputs

Research scaffold for benchmarking how local and hosted LLMs produce schema-conformant JSON for form-like workflows such as incident reports, bug tickets, and change requests.

The first implementation slice focuses on the backend:

- JSON Schema validation with structured failure taxonomy
- pre-validation JSON extraction and lightweight repair
- local Ollama-compatible LLM routing
- FastAPI `/generate` endpoint
- mock model path for development before Ollama is installed

## Local LLM Setup

Install Ollama from https://ollama.com, then pull a local instruction model:

```powershell
ollama pull llama3.1:8b
ollama serve
```

On Windows, if PowerShell says `ollama` is not recognized, call the CLI directly:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" --version
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull llama3.1:8b
```

Or add it to the current session:

```powershell
$env:Path += ";$env:LOCALAPPDATA\Programs\Ollama"
ollama --version
```

The backend talks to Ollama at `http://localhost:11434` by default. Override it with:

```powershell
$env:OLLAMA_BASE_URL="http://localhost:11434"
```

Until Ollama is installed, use `model: "mock/incident-json"` to exercise the validation pipeline without calling a real LLM.

Installed local models are addressed by prefixing the Ollama model name with `ollama/`:

- `ollama/llama3.2:3b` - fastest local smoke-test model
- `ollama/mistral:latest`
- `ollama/llama3.1:8b`
- `ollama/gemma2:latest`

## Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Try a local smoke request:

```powershell
python -m app.cli.generate `
  --input "Checkout was down at 3:14am, severity critical, 500 users affected" `
  --schema incident_report `
  --model ollama/llama3.2:3b
```

Use Ollama once installed:

```powershell
python -m app.cli.generate `
  --input "Checkout was down at 3:14am, severity critical, 500 users affected" `
  --schema incident_report `
  --model ollama/llama3.1:8b
```

## API Results

`POST /generate` persists results by default and returns a `result_id`. Send `"persist": false` to run without writing to SQLite.

Useful endpoints:

- `GET /models`
- `GET /schemas`
- `POST /generate`
- `GET /results`
- `GET /results/runs`
- `GET /results/{result_id}`
- `GET /results/summary?run_id=your_run`
- `POST /benchmarks/run`
- `GET /benchmarks/{run_id}`
- `GET /analysis/tables?run_id=your_run`

The default database path is `backend/data/results.db`.

Frontend smoke flow:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8002/models

Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8002/generate `
  -ContentType 'application/json' `
  -Body '{"input_text":"Production checkout button fails in Chrome","schema_name":"bug_template","model":"ollama/llama3.2:3b","run_id":"frontend_smoke"}'

Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8002/benchmarks/run `
  -ContentType 'application/json' `
  -Body '{"schema_names":["incident_report"],"models":["ollama/llama3.2:3b"],"run_id":"frontend_api_smoke","max_attempts":1}'

Invoke-RestMethod -Uri 'http://127.0.0.1:8002/analysis/tables?run_id=frontend_api_smoke'
```

## Benchmark Runner

Benchmark CSVs live in `benchmark/test_cases/` and full expected JSON answers live in `benchmark/test_cases/answer_keys/`.

Each schema currently has 10 labeled test cases:

- `incident_report_cases.csv` + `answer_keys/incident_report_answers.json`
- `bug_template_cases.csv` + `answer_keys/bug_template_answers.json`
- `change_request_cases.csv` + `answer_keys/change_request_answers.json`

Run a smoke benchmark with the fastest local Ollama model:

```powershell
python benchmark\runner.py `
  --schema incident_report `
  --models ollama/llama3.2:3b `
  --cases benchmark\test_cases\incident_report_cases.csv `
  --output benchmark\results\ollama_smoke.db `
  --run-id ollama_smoke
```

Run against a local Ollama model after installing Ollama:

```powershell
python benchmark\runner.py `
  --schema incident_report `
  --models ollama/llama3.2:3b ollama/mistral:latest ollama/llama3.1:8b ollama/gemma2:latest `
  --cases benchmark\test_cases\incident_report_cases.csv `
  --output benchmark\results\ollama_models.db `
  --run-id ollama_models
```

## Analysis Tables

Generate the paper tables from any benchmark SQLite database:

```powershell
python -m benchmark.analysis.generate_tables `
  --db benchmark\results\smoke.db `
  --out benchmark\results\smoke_tables `
  --run-id smoke
```

This writes CSV and Markdown versions of:

- Table 1: overall success rate by model
- Table 2: failure type breakdown by model
- Table 3: schema complexity effect

## Frontend

```powershell
cd frontend
npm install
npm run dev -- --port 5173
```

Open:

`http://127.0.0.1:5173`

The frontend reads `VITE_API_BASE_URL`, defaulting to `http://127.0.0.1:8002` in local development. Copy `frontend/.env.example` to `frontend/.env` if you want to point it at a different backend.
