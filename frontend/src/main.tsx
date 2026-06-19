import React from "react";
import { createRoot } from "react-dom/client";
import {
  BarChart3,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Copy,
  Database,
  Download,
  Eye,
  FileJson,
  Loader2,
  PencilRuler,
  Play,
  XCircle,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8002";
const AUDIT_PAGE_SIZE = 8;

type ModelCatalog = {
  mock_models: Array<{ id: string; label: string; supports: string[] }>;
  ollama: { base_url: string; available: boolean; models: string[] };
  suggested_models: string[];
};

type SchemasResponse = { schemas: string[] };

type RawAttempt = {
  attempt: number;
  raw: string;
  extracted: Record<string, unknown> | null;
  repaired: Record<string, unknown> | null;
  extraction_strategy: string;
  failure: string | null;
  fields: string[];
  repairs: string[];
  latency_ms: number;
  error: string | null;
};

type GenerationResponse = {
  result_id: number | null;
  success: boolean;
  schema_name: string;
  model: string;
  attempts: number;
  output: Record<string, unknown> | null;
  raw_attempts: RawAttempt[];
  latency_ms: number;
};

type BenchmarkJob = {
  run_id: string;
  status: string;
  schemas: string[];
  models: string[];
  total: number;
  completed: number;
  error: string | null;
};

type RunSummary = {
  run_id: string;
  started_at: string;
  last_result_at: string;
  total: number;
  passed: number;
  model_count: number;
  schema_count: number;
  pass_rate: number;
};

type AnalysisTables = {
  table1_model_comparison: Array<Record<string, string | number>>;
  table2_failure_breakdown: Array<Record<string, string | number>>;
  table3_schema_complexity: Array<Record<string, string | number>>;
};

type ResultSummary = {
  id: number;
  created_at: string;
  run_id: string | null;
  case_id: string | null;
  input_text?: string | null;
  schema_name: string;
  model: string;
  success: boolean;
  attempts: number;
  latency_ms: number;
  failure_type: string | null;
  failure_message: string | null;
  failure_fields: string[];
};

type ResultDetail = ResultSummary & {
  output: Record<string, unknown> | null;
  raw_attempts: RawAttempt[];
};

type AppData = {
  catalog: ModelCatalog | null;
  schemas: string[];
  runs: RunSummary[];
  tables: AnalysisTables | null;
  results: ResultSummary[];
};

type LiveDemoState = {
  inputText: string;
  schemaName: string;
  model: string;
  maxAttempts: number;
  useFewShots: boolean;
  result: GenerationResponse | null;
};

type ViewName = "live" | "benchmarks" | "audit" | "schema";

const defaultInput =
  "Production checkout button fails in Chrome after valid payment details are entered. Severity high.";

const fallbackModels = ["ollama/llama3.2:3b", "mock/incident-json", "mock/wrapped-json"];

const initialLiveDemoState: LiveDemoState = {
  inputText: defaultInput,
  schemaName: "bug_template",
  model: "ollama/llama3.2:3b",
  maxAttempts: 3,
  useFewShots: true,
  result: null,
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function App() {
  const [activeView, setActiveView] = React.useState<ViewName>("live");
  const [data, setData] = React.useState<AppData>({ catalog: null, schemas: [], runs: [], tables: null, results: [] });
  const [selectedRunId, setSelectedRunId] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [liveDemoState, setLiveDemoState] = React.useState<LiveDemoState>(initialLiveDemoState);

  const loadData = React.useCallback(async (runId = selectedRunId) => {
    setLoading(true);
    setError(null);
    try {
      const [catalog, schemas, runsResponse, resultsResponse] = await Promise.all([
        api<ModelCatalog>("/models"),
        api<SchemasResponse>("/schemas"),
        api<{ runs: RunSummary[] }>("/results/runs"),
        api<{ results: ResultSummary[] }>("/results?limit=200"),
      ]);
      const availableRunIds = new Set(runsResponse.runs.map((run) => run.run_id));
      const effectiveRunId = runId && availableRunIds.has(runId) ? runId : runsResponse.runs[0]?.run_id ?? "";
      const tables = await api<AnalysisTables>(`/analysis/tables${effectiveRunId ? `?run_id=${encodeURIComponent(effectiveRunId)}` : ""}`);
      setSelectedRunId(effectiveRunId);
      setData({ catalog, schemas: schemas.schemas, runs: runsResponse.runs, tables, results: resultsResponse.results });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load backend data.");
    } finally {
      setLoading(false);
    }
  }, [selectedRunId]);

  React.useEffect(() => {
    void loadData();
  }, [loadData]);

  const allModels = React.useMemo(() => {
    const mock = data.catalog?.mock_models.map((model) => model.id) ?? [];
    const ollama = data.catalog?.ollama.models ?? [];
    return Array.from(new Set([...(ollama.length ? ollama : ["ollama/llama3.2:3b"]), ...mock, ...fallbackModels]));
  }, [data.catalog]);

  const refreshForRun = (runId: string) => {
    setSelectedRunId(runId);
    void loadData(runId);
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <h1>StructGuard</h1>
        </div>
        <nav className="view-tabs" aria-label="Views">
          <button className={activeView === "live" ? "active" : ""} onClick={() => setActiveView("live")}>
            <FileJson aria-hidden="true" /> Live Demo
          </button>
          <button className={activeView === "benchmarks" ? "active" : ""} onClick={() => setActiveView("benchmarks")}>
            <BarChart3 aria-hidden="true" /> Benchmark
          </button>
          <button className={activeView === "audit" ? "active" : ""} onClick={() => setActiveView("audit")}>
            <Database aria-hidden="true" /> History
          </button>
          <button className={activeView === "schema" ? "active" : ""} onClick={() => setActiveView("schema")}>
            <PencilRuler aria-hidden="true" /> Schema Editor
          </button>
        </nav>
        <div className="topbar-spacer" aria-hidden="true" />
      </header>

      {error && <div className="status-banner error"><XCircle aria-hidden="true" />{error}</div>}
      {loading && <div className="status-banner"><Loader2 className="spin" aria-hidden="true" />Loading backend data</div>}

      {activeView !== "live" && <DashboardStrip catalog={data.catalog} runs={data.runs} tables={data.tables} />}

      {activeView === "live" && (
        <LiveDemo
          schemas={data.schemas}
          models={allModels}
          state={liveDemoState}
          onStateChange={setLiveDemoState}
          onGenerated={() => loadData(selectedRunId)}
        />
      )}
      {activeView === "benchmarks" && (
        <>
          <BenchmarkPanel
            schemas={data.schemas}
            models={allModels}
            onRunComplete={(runId) => refreshForRun(runId)}
          />
          <ResultsPanel
            runs={data.runs}
            tables={data.tables}
            selectedRunId={selectedRunId}
            onSelectRun={refreshForRun}
          />
        </>
      )}
      {activeView === "audit" && (
        <AuditLogPanel results={data.results} />
      )}
      {activeView === "schema" && (
        <SchemaEditorPanel schemas={data.schemas} />
      )}
    </main>
  );
}

function DashboardStrip({ catalog, runs, tables }: { catalog: ModelCatalog | null; runs: RunSummary[]; tables: AnalysisTables | null }) {
  const latestRun = runs[0];
  const modelCount = (catalog?.mock_models.length ?? 0) + (catalog?.ollama.models.length ?? 0);
  const resultCount = tables?.table1_model_comparison.reduce((sum, row) => sum + Number(row.total ?? 0), 0) ?? 0;
  const failures = tables?.table2_failure_breakdown.reduce((sum, row) => sum + Number(row.count ?? 0), 0) ?? 0;

  return (
    <section className="metric-grid" aria-label="Backend metrics">
      <Metric label="Ollama" value={catalog?.ollama.available ? "Online" : "Offline"} tone={catalog?.ollama.available ? "good" : "warn"} />
      <Metric label="Models" value={String(modelCount)} />
      <Metric label="Latest run" value={latestRun?.run_id ?? "None"} />
      <Metric label="Rows" value={String(resultCount)} />
      <Metric label="Failures" value={String(failures)} tone={failures ? "warn" : "good"} />
    </section>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "good" | "warn" }) {
  return (
    <div className={`metric ${tone ?? ""}`}>
      <span className="metric-label">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function LiveDemo({
  schemas,
  models,
  state,
  onStateChange,
  onGenerated,
}: {
  schemas: string[];
  models: string[];
  state: LiveDemoState;
  onStateChange: React.Dispatch<React.SetStateAction<LiveDemoState>>;
  onGenerated: () => void;
}) {
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [copyStatus, setCopyStatus] = React.useState<"idle" | "copied" | "failed">("idle");
  const copyTimer = React.useRef<number | null>(null);
  const { inputText, schemaName, model, maxAttempts, useFewShots, result } = state;
  const lastAttempt = result?.raw_attempts.at(-1) ?? null;
  const visibleOutput = result?.output ?? lastAttempt?.repaired ?? lastAttempt?.extracted ?? null;
  const outputEmpty = result && !result.success ? "No parseable JSON returned" : "No output yet";
  const outputJson = visibleOutput ? JSON.stringify(visibleOutput, null, 2) : "";

  const updateLiveState = React.useCallback((patch: Partial<LiveDemoState>) => {
    onStateChange((current) => ({ ...current, ...patch }));
  }, [onStateChange]);

  React.useEffect(() => {
    if (models.length && !models.includes(model)) {
      updateLiveState({ model: models[0] });
    }
  }, [model, models, updateLiveState]);

  React.useEffect(() => {
    return () => {
      if (copyTimer.current !== null) {
        window.clearTimeout(copyTimer.current);
      }
    };
  }, []);

  async function generate() {
    setBusy(true);
    setError(null);
    setCopyStatus("idle");
    try {
      const response = await api<GenerationResponse>("/generate", {
        method: "POST",
        body: JSON.stringify({
          input_text: inputText,
          schema_name: schemaName,
          model,
          use_few_shots: useFewShots,
          max_attempts: maxAttempts,
          run_id: "frontend_live",
          case_id: `${schemaName}_manual`,
        }),
      });
      updateLiveState({ result: response });
      onGenerated();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Generation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function copyOutput() {
    if (!outputJson) {
      return;
    }
    try {
      await copyText(outputJson);
      setCopyStatus("copied");
    } catch {
      setCopyStatus("failed");
    }

    if (copyTimer.current !== null) {
      window.clearTimeout(copyTimer.current);
    }
    copyTimer.current = window.setTimeout(() => setCopyStatus("idle"), 1800);
  }

  return (
    <section className="workspace live-grid">
      <div className="live-column">
        <div className="view-heading">
          <h2>Natural Language Input</h2>
          <p>Describe the event to extract structured data using the active schema.</p>
        </div>
        <div className="tool-panel input-console">
          <label>
            Source text
            <textarea value={inputText} onChange={(event) => updateLiveState({ inputText: event.target.value })} />
          </label>

          <div className="control-grid">
            <label>
              Schema
              <select value={schemaName} onChange={(event) => updateLiveState({ schemaName: event.target.value })}>
                {(schemas.length ? schemas : ["incident_report", "bug_template", "change_request"]).map((schema) => (
                  <option key={schema} value={schema}>{schema}</option>
                ))}
              </select>
            </label>
            <label>
              Model
              <select value={model} onChange={(event) => updateLiveState({ model: event.target.value })}>
                {(models.length ? models : fallbackModels).map((modelId) => (
                  <option key={modelId} value={modelId}>{modelId}</option>
                ))}
              </select>
            </label>
            <label>
              Attempts
              <input type="number" min={1} max={5} value={maxAttempts} onChange={(event) => updateLiveState({ maxAttempts: Number(event.target.value) })} />
            </label>
            <label className="toggle-row">
              <input type="checkbox" checked={useFewShots} onChange={(event) => updateLiveState({ useFewShots: event.target.checked })} />
              Few-shot
            </label>
          </div>

          <button className="primary-button generate-button" onClick={generate} disabled={busy || !inputText.trim()}>
            {busy ? <Loader2 className="spin" aria-hidden="true" /> : <Play aria-hidden="true" />}
            Generate JSON
          </button>
          <div className="generation-meta">
            <span>Temperature: <strong>0.1</strong></span>
            <span>Max tokens: <strong>1000</strong></span>
          </div>
          {model.startsWith("mock/") && (
            <div className="inline-warning">
              Mock models return canned fixture JSON and ignore the source text. Choose an `ollama/...` model for real extraction.
            </div>
          )}

          {error && <div className="inline-error"><XCircle aria-hidden="true" />{error}</div>}
        </div>
      </div>

      <div className="live-column">
        <div className="view-heading output-heading">
          <div>
            <h2>Structured Output</h2>
            <p>{result ? `${result.latency_ms}ms latency - ${result.attempts} attempt${result.attempts === 1 ? "" : "s"}` : "Waiting for generation"}</p>
          </div>
          <div className="output-actions">
            {result && <StatusPill success={result.success} />}
            <button
              className={`icon-button ${copyStatus === "copied" ? "success" : copyStatus === "failed" ? "failed" : ""}`}
              onClick={copyOutput}
              disabled={!visibleOutput}
              title={copyStatus === "copied" ? "Copied" : copyStatus === "failed" ? "Copy failed" : "Copy JSON"}
              aria-label="Copy output JSON"
            >
              {copyStatus === "copied" ? <CheckCircle2 aria-hidden="true" /> : <Copy aria-hidden="true" />}
            </button>
          </div>
        </div>
        <div className="tool-panel result-panel">
          {result && !result.success && lastAttempt && (
            <FailureSummary attempt={lastAttempt} schemaName={result.schema_name} />
          )}
          <JsonViewer value={visibleOutput} empty={outputEmpty} />
          <AttemptTimeline attempts={result?.raw_attempts ?? []} />
        </div>
      </div>
    </section>
  );
}

function BenchmarkPanel({ schemas, models, onRunComplete }: { schemas: string[]; models: string[]; onRunComplete: (runId: string) => void }) {
  const availableSchemas = schemas.length ? schemas : ["incident_report", "bug_template", "change_request"];
  const availableModels = models.length ? models : fallbackModels;
  const [selectedSchemas, setSelectedSchemas] = React.useState<string[]>(() => defaultBenchmarkSchemas(availableSchemas));
  const [selectedModels, setSelectedModels] = React.useState<string[]>(["ollama/llama3.2:3b"]);
  const [runId, setRunId] = React.useState("frontend_run");
  const [maxAttempts, setMaxAttempts] = React.useState(3);
  const [job, setJob] = React.useState<BenchmarkJob | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setSelectedSchemas((current) => {
      const stillAvailable = current.filter((schema) => availableSchemas.includes(schema));
      return stillAvailable.length ? stillAvailable : defaultBenchmarkSchemas(availableSchemas);
    });
  }, [availableSchemas.join("|")]);

  React.useEffect(() => {
    setSelectedModels((current) => {
      const stillAvailable = current.filter((modelId) => availableModels.includes(modelId));
      if (stillAvailable.length) {
        return stillAvailable;
      }
      const ollamaModels = availableModels.filter((modelId) => modelId.startsWith("ollama/"));
      return ollamaModels.length ? [ollamaModels[0]] : availableModels.slice(0, 1);
    });
  }, [availableModels.join("|")]);

  async function startRun() {
    setBusy(true);
    setError(null);
    try {
      const response = await api<BenchmarkJob>("/benchmarks/run", {
        method: "POST",
        body: JSON.stringify({
          schema_names: selectedSchemas,
          models: selectedModels,
          run_id: runId,
          max_attempts: maxAttempts,
        }),
      });
      setJob(response);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Benchmark failed to start.");
    } finally {
      setBusy(false);
    }
  }

  React.useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) {
      return;
    }
    const interval = window.setInterval(async () => {
      const updated = await api<BenchmarkJob>(`/benchmarks/${encodeURIComponent(job.run_id)}`);
      setJob(updated);
      if (updated.status === "completed") {
        onRunComplete(updated.run_id);
      }
    }, 1000);
    return () => window.clearInterval(interval);
  }, [job, onRunComplete]);

  return (
    <section className="workspace benchmark-grid">
      <div className="tool-panel benchmark-config">
        <div className="panel-heading">
          <h2>Benchmark Run</h2>
          <button className="primary-button" onClick={startRun} disabled={busy || !selectedSchemas.length || !selectedModels.length}>
            {busy ? <Loader2 className="spin" aria-hidden="true" /> : <Play aria-hidden="true" />}
            Start
          </button>
        </div>

        <div className="control-grid">
          <label>
            Run ID
            <input value={runId} onChange={(event) => setRunId(event.target.value)} />
          </label>
          <label>
            Attempts
            <input type="number" min={1} max={5} value={maxAttempts} onChange={(event) => setMaxAttempts(Number(event.target.value))} />
          </label>
        </div>

        <CheckboxGroup title="Schemas" values={availableSchemas} selected={selectedSchemas} onChange={setSelectedSchemas} />
        <CheckboxGroup title="Models" values={availableModels} selected={selectedModels} onChange={setSelectedModels} />
        {error && <div className="inline-error"><XCircle aria-hidden="true" />{error}</div>}
      </div>

      <div className="tool-panel benchmark-status">
        <div className="panel-heading">
          <h2>Status</h2>
          {job && <span className={`job-state ${job.status}`}>{job.status}</span>}
        </div>
        {job ? (
          <>
            <div className="progress-track">
              <span style={{ width: `${job.total ? (job.completed / job.total) * 100 : 0}%` }} />
            </div>
            <div className="job-grid">
              <Metric label="Completed" value={`${job.completed}/${job.total}`} />
              <Metric label="Schemas" value={String(job.schemas.length)} />
              <Metric label="Models" value={String(job.models.length)} />
            </div>
            {job.error && <div className="inline-error"><XCircle aria-hidden="true" />{job.error}</div>}
          </>
        ) : (
          <div className="empty-state">No active run</div>
        )}
      </div>
    </section>
  );
}

function defaultBenchmarkSchemas(availableSchemas: string[]): string[] {
  if (availableSchemas.includes("incident_report")) {
    return ["incident_report"];
  }
  return availableSchemas.slice(0, 1);
}

function uniqueSorted(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean))).sort((left, right) => left.localeCompare(right));
}

function ResultsPanel({ runs, tables, selectedRunId, onSelectRun }: { runs: RunSummary[]; tables: AnalysisTables | null; selectedRunId: string; onSelectRun: (runId: string) => void }) {
  const passRows = tables?.table1_model_comparison ?? [];
  const failureRows = tables?.table2_failure_breakdown ?? [];
  const schemaRows = tables?.table3_schema_complexity ?? [];
  const chartRows = passRows.map((row) => ({ model: String(row.model), pass_rate: parsePercent(row.pass_rate) }));

  return (
    <section className="workspace results-layout">
      <div className="tool-panel runs-panel">
        <div className="panel-heading">
          <h2>Runs</h2>
        </div>
        <div className="run-list">
          {runs.length ? (
            runs.map((run) => (
              <button key={run.run_id} className={run.run_id === selectedRunId ? "selected" : ""} onClick={() => onSelectRun(run.run_id)}>
                <span>{run.run_id}</span>
                <strong>{Math.round(run.pass_rate * 100)}%</strong>
              </button>
            ))
          ) : (
            <div className="empty-state compact">No saved runs</div>
          )}
        </div>
      </div>

      <div className="tool-panel chart-panel">
        <div className="panel-heading">
          <h2>Pass Rate</h2>
          <span className="run-chip">{selectedRunId || "No run selected"}</span>
        </div>
        {chartRows.length ? (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartRows} margin={{ top: 8, right: 8, left: 0, bottom: 44 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="model" angle={-18} textAnchor="end" interval={0} height={58} tick={{ fontSize: 12 }} />
              <YAxis domain={[0, 100]} tickFormatter={(value) => `${value}%`} />
              <Tooltip formatter={(value) => `${value}%`} />
              <Bar dataKey="pass_rate" radius={[4, 4, 0, 0]}>
                {chartRows.map((row) => (
                  <Cell key={row.model} fill={row.pass_rate >= 70 ? "#1f8a70" : row.pass_rate >= 40 ? "#b57918" : "#b83b5e"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty-state chart-empty">Run a benchmark to populate pass-rate data</div>
        )}
      </div>

      <DataTable title="Model Comparison" rows={passRows} />
      <DataTable title="Failure Breakdown" rows={failureRows} />
      <DataTable title="Schema Complexity" rows={schemaRows} />
    </section>
  );
}

function AuditLogPanel({ results }: { results: ResultSummary[] }) {
  const [selected, setSelected] = React.useState<ResultSummary | null>(results[0] ?? null);
  const [detail, setDetail] = React.useState<ResultDetail | null>(null);
  const [detailLoading, setDetailLoading] = React.useState(false);
  const [detailError, setDetailError] = React.useState<string | null>(null);
  const [query, setQuery] = React.useState("");
  const [modelFilter, setModelFilter] = React.useState("all");
  const [schemaFilter, setSchemaFilter] = React.useState("all");
  const [statusFilter, setStatusFilter] = React.useState("all");
  const [page, setPage] = React.useState(1);

  const modelOptions = React.useMemo(() => uniqueSorted(results.map((result) => result.model)), [results]);
  const schemaOptions = React.useMemo(() => uniqueSorted(results.map((result) => result.schema_name)), [results]);
  const filteredResults = React.useMemo(() => {
    const needle = query.trim().toLowerCase();
    return results.filter((result) => {
      const searchableText = [
        `trace-${result.id}`,
        String(result.id),
        result.created_at,
        result.run_id ?? "",
        result.case_id ?? "",
        result.input_text ?? "",
        result.schema_name,
        result.model,
        result.success ? "valid passed success" : "failed failure invalid",
        result.failure_type ?? "",
        result.failure_message ?? "",
        ...(result.failure_fields ?? []),
      ]
        .join(" ")
        .toLowerCase();
      const matchesQuery =
        !needle || searchableText.includes(needle);
      const matchesModel = modelFilter === "all" || result.model === modelFilter;
      const matchesSchema = schemaFilter === "all" || result.schema_name === schemaFilter;
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "valid" && result.success) ||
        (statusFilter === "failed" && !result.success);
      return matchesQuery && matchesModel && matchesSchema && matchesStatus;
    });
  }, [modelFilter, query, results, schemaFilter, statusFilter]);
  const pageCount = Math.max(1, Math.ceil(filteredResults.length / AUDIT_PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const pageStart = (currentPage - 1) * AUDIT_PAGE_SIZE;
  const pagedResults = filteredResults.slice(pageStart, pageStart + AUDIT_PAGE_SIZE);
  const firstVisible = filteredResults.length ? pageStart + 1 : 0;
  const lastVisible = Math.min(pageStart + AUDIT_PAGE_SIZE, filteredResults.length);
  const pageNumbers = React.useMemo(() => Array.from({ length: pageCount }, (_, index) => index + 1), [pageCount]);

  React.useEffect(() => {
    setPage(1);
  }, [modelFilter, query, results, schemaFilter, statusFilter]);

  React.useEffect(() => {
    setPage((current) => Math.min(current, pageCount));
  }, [pageCount]);

  React.useEffect(() => {
    setSelected((current) => {
      if (current && filteredResults.some((result) => result.id === current.id)) {
        return current;
      }
      return filteredResults[0] ?? null;
    });
  }, [filteredResults]);

  React.useEffect(() => {
    if (!selected) {
      setDetail(null);
      setDetailError(null);
      return;
    }

    let cancelled = false;
    setDetailLoading(true);
    setDetailError(null);
    void api<ResultDetail>(`/results/${selected.id}`)
      .then((response) => {
        if (!cancelled) {
          setDetail(response);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setDetail(null);
          setDetailError(caught instanceof Error ? caught.message : "Failed to load trace.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setDetailLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selected]);

  function exportCsv() {
    if (!filteredResults.length) {
      return;
    }
    const csv = toCsv(
      filteredResults.map((result) => ({
        id: result.id,
        created_at: result.created_at,
        run_id: result.run_id ?? "",
        case_id: result.case_id ?? "",
        schema_name: result.schema_name,
        model: result.model,
        success: result.success,
        attempts: result.attempts,
        latency_ms: result.latency_ms,
        failure_type: result.failure_type ?? "",
        failure_message: result.failure_message ?? "",
        input_text: result.input_text ?? "",
      })),
    );
    downloadText(`audit-results-${new Date().toISOString().slice(0, 10)}.csv`, csv, "text/csv;charset=utf-8");
  }

  return (
    <section className="workspace audit-layout">
      <div className="tool-panel audit-main">
        <div className="audit-filters">
          <div className="search-box">
            <Database aria-hidden="true" />
            <input
              aria-label="Search audit results"
              placeholder="Search trace, run, case, model, or input"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <select value={modelFilter} onChange={(event) => setModelFilter(event.target.value)} aria-label="Filter by model">
            <option value="all">All Models</option>
            {modelOptions.map((model) => (
              <option key={model} value={model}>{model}</option>
            ))}
          </select>
          <select value={schemaFilter} onChange={(event) => setSchemaFilter(event.target.value)} aria-label="Filter by schema">
            <option value="all">All Schemas</option>
            {schemaOptions.map((schema) => (
              <option key={schema} value={schema}>{schema}</option>
            ))}
          </select>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="Filter by status">
            <option value="all">All Statuses</option>
            <option value="valid">Valid</option>
            <option value="failed">Failed</option>
          </select>
          <button className="secondary-button" onClick={exportCsv} disabled={!filteredResults.length}>
            <Download aria-hidden="true" /> Export CSV
          </button>
        </div>

        {filteredResults.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Model</th>
                  <th>Schema</th>
                  <th>Status</th>
                  <th>Attempts</th>
                  <th>Latency</th>
                  <th>Trace</th>
                </tr>
              </thead>
              <tbody>
                {pagedResults.map((result) => (
                  <tr key={result.id} className={selected?.id === result.id ? "selected-row" : ""}>
                    <td className="mono">{result.created_at}</td>
                    <td>{result.model}</td>
                    <td><span className="mono-chip">{result.schema_name}</span></td>
                    <td><StatusPill success={result.success} /></td>
                    <td className="mono">{result.attempts}</td>
                    <td className="mono">{result.latency_ms}ms</td>
                    <td>
                      <button className="row-action" onClick={() => setSelected(result)} title="View trace">
                        <Eye aria-hidden="true" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="pagination-bar">
              <span className="pagination-summary">
                Showing {firstVisible}-{lastVisible} of {filteredResults.length}
              </span>
              <div className="pagination-pages" aria-label="Audit result pages">
                <button className="page-button icon" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={currentPage === 1} aria-label="Previous page">
                  <ChevronLeft aria-hidden="true" />
                </button>
                {pageNumbers.map((pageNumber) => (
                  <button
                    key={pageNumber}
                    className={pageNumber === currentPage ? "page-button active" : "page-button"}
                    onClick={() => setPage(pageNumber)}
                    aria-current={pageNumber === currentPage ? "page" : undefined}
                  >
                    {pageNumber}
                  </button>
                ))}
                <button className="page-button icon" onClick={() => setPage((value) => Math.min(pageCount, value + 1))} disabled={currentPage === pageCount} aria-label="Next page">
                  <ChevronRight aria-hidden="true" />
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="empty-state">No matching audit results</div>
        )}
      </div>

      <aside className="tool-panel trace-panel">
        <div className="panel-heading">
          <div>
            <h2>Trace Details</h2>
            <p className="muted">{selected ? `trace-${selected.id}` : "No trace selected"}</p>
          </div>
        </div>
        {selected ? (
          <>
            <div className={`trace-alert ${selected.success ? "success" : "failed"}`}>
              <strong>{selected.success ? "Validation passed" : "Validation failed"}</strong>
              <p>{selected.success ? "The model output passed schema validation and was persisted." : selected.failure_message ?? "The model output exhausted retries or failed validation."}</p>
            </div>
            <div className="trace-grid">
              <TraceStat label="Model" value={selected.model} />
              <TraceStat label="Schema" value={selected.schema_name} />
              <TraceStat label="Attempts" value={String(selected.attempts)} />
              <TraceStat label="Latency" value={`${selected.latency_ms}ms`} />
            </div>
            {detailLoading && <div className="empty-state compact">Loading trace</div>}
            {detailError && <div className="inline-error"><XCircle aria-hidden="true" />{detailError}</div>}
            {!detailLoading && !detailError && (
              <JsonViewer value={detail ?? selected} empty="No trace selected" />
            )}
          </>
        ) : (
          <div className="empty-state">No trace selected</div>
        )}
      </aside>
    </section>
  );
}

function TraceStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="trace-stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function SchemaEditorPanel({ schemas }: { schemas: string[] }) {
  const schemaOptions = schemas.length ? schemas : ["incident_report", "bug_template", "change_request"];
  const [schemaName, setSchemaName] = React.useState(schemaOptions[0] ?? "incident_report");
  const [schema, setSchema] = React.useState<Record<string, unknown> | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    async function loadSchema() {
      setError(null);
      try {
        const response = await api<Record<string, unknown>>(`/schemas/${encodeURIComponent(schemaName)}`);
        if (!cancelled) {
          setSchema(response);
        }
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "Failed to load schema.");
        }
      }
    }
    void loadSchema();
    return () => {
      cancelled = true;
    };
  }, [schemaName]);

  const fields = React.useMemo(() => summarizeFields(schema), [schema]);

  return (
    <section className="workspace schema-layout">
      <aside className="schema-list tool-panel">
        <h2>Schema Library</h2>
        <div className="schema-stack">
          {schemaOptions.map((schemaOption) => (
            <button
              key={schemaOption}
              className={schemaOption === schemaName ? "selected" : ""}
              onClick={() => setSchemaName(schemaOption)}
            >
              <span>{labelize(schemaOption)}</span>
              <strong>v1.0.0</strong>
            </button>
          ))}
        </div>
      </aside>

      <div className="schema-editor-main">
        <div className="schema-title-row">
          <div>
            <h2>{labelize(schemaName)}</h2>
          </div>
        </div>
        {error && <div className="inline-error"><XCircle aria-hidden="true" />{error}</div>}
        <JsonViewer value={schema} empty="Loading schema" filename={`${schemaName}.json`} className="schema-code-shell" />
        <div className="field-summary tool-panel">
          <div className="panel-heading">
            <h2>Field Summary</h2>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Field name</th>
                  <th>Type</th>
                  <th>Constraints</th>
                  <th>Required</th>
                </tr>
              </thead>
              <tbody>
                {fields.map((field) => (
                  <tr key={field.name}>
                    <td className="mono">{field.name}</td>
                    <td><span className="mono-chip">{field.type}</span></td>
                    <td>{field.constraints}</td>
                    <td>{field.required ? <CheckCircle2 className="table-check" aria-hidden="true" /> : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}

function CheckboxGroup({ title, values, selected, onChange }: { title: string; values: string[]; selected: string[]; onChange: (values: string[]) => void }) {
  function toggle(value: string) {
    onChange(selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value]);
  }

  return (
    <fieldset className="check-group">
      <legend>{title}</legend>
      {values.map((value) => (
        <label key={value}>
          <input type="checkbox" checked={selected.includes(value)} onChange={() => toggle(value)} />
          {value}
        </label>
      ))}
    </fieldset>
  );
}

function StatusPill({ success }: { success: boolean }) {
  return (
    <span className={`status-pill ${success ? "success" : "failed"}`}>
      {success ? <CheckCircle2 aria-hidden="true" /> : <XCircle aria-hidden="true" />}
      {success ? "Valid" : "Failed"}
    </span>
  );
}

async function copyText(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  document.body.removeChild(textarea);
  if (!copied) {
    throw new Error("Copy command failed.");
  }
}

function toCsv(rows: Array<Record<string, unknown>>): string {
  const headers = Object.keys(rows[0] ?? {});
  const lines = [
    headers.join(","),
    ...rows.map((row) => headers.map((header) => csvCell(row[header])).join(",")),
  ];
  return `${lines.join("\n")}\n`;
}

function csvCell(value: unknown): string {
  const text = value === null || value === undefined ? "" : String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

function downloadText(filename: string, text: string, type: string): void {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function JsonViewer({ value, empty, filename = "output.json", className }: { value: unknown; empty: string; filename?: string; className?: string }) {
  if (!value) {
    return <div className="empty-state">{empty}</div>;
  }
  return (
    <div className={className ? `code-shell ${className}` : "code-shell"}>
      <div className="code-header">
        <span>{filename}</span>
      </div>
      <pre className="json-view">{JSON.stringify(value, null, 2)}</pre>
    </div>
  );
}

function FailureSummary({ attempt, schemaName }: { attempt: RawAttempt; schemaName: string }) {
  const fields = attempt.fields.length ? attempt.fields.join(", ") : "output";
  const repairs = attempt.repairs.length ? attempt.repairs.join(", ") : "none";

  return (
    <div className="failure-summary" role="alert">
      <div>
        <strong>{attempt.failure ?? "Generation failed"}</strong>
        <span>{schemaName} validation failed on {fields}</span>
      </div>
      {attempt.error && <p>{attempt.error}</p>}
      <small>Repairs applied: {repairs}</small>
    </div>
  );
}

function AttemptTimeline({ attempts }: { attempts: RawAttempt[] }) {
  if (!attempts.length) {
    return null;
  }
  return (
    <div className="timeline">
      {attempts.map((attempt) => (
        <div key={attempt.attempt} className={attempt.failure ? "attempt failed" : "attempt passed"}>
          <span>{attempt.attempt}</span>
          <div>
            <strong>{attempt.failure ?? "VALID"}</strong>
            <small>{attempt.extraction_strategy} - {attempt.latency_ms}ms</small>
            {attempt.fields.length > 0 && (
              <p className="attempt-detail"><b>Fields:</b> {attempt.fields.join(", ")}</p>
            )}
            {attempt.error && (
              <p className="attempt-detail"><b>Error:</b> {attempt.error}</p>
            )}
            {attempt.repairs.length > 0 && (
              <p className="attempt-detail"><b>Repairs:</b> {attempt.repairs.join(", ")}</p>
            )}
            {attempt.failure && (attempt.repaired || attempt.extracted || attempt.raw) && (
              <details className="attempt-json">
                <summary>Attempt payload</summary>
                <pre>{JSON.stringify(attempt.repaired ?? attempt.extracted ?? attempt.raw, null, 2)}</pre>
              </details>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function DataTable({ title, rows }: { title: string; rows: Array<Record<string, string | number>> }) {
  const headers = rows[0] ? Object.keys(rows[0]) : [];
  return (
    <div className="tool-panel table-panel">
      <div className="panel-heading">
        <h2>{title}</h2>
      </div>
      {rows.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index}>
                  {headers.map((header) => <td key={header}>{row[header]}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">No rows</div>
      )}
    </div>
  );
}

function parsePercent(value: unknown): number {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value !== "string") {
    return 0;
  }
  return Number(value.replace("%", "")) || 0;
}

function labelize(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function summarizeFields(schema: Record<string, unknown> | null): Array<{ name: string; type: string; constraints: string; required: boolean }> {
  if (!schema || typeof schema.properties !== "object" || schema.properties === null) {
    return [];
  }
  const properties = schema.properties as Record<string, Record<string, unknown>>;
  const required = Array.isArray(schema.required) ? new Set(schema.required.map(String)) : new Set<string>();

  return Object.entries(properties).map(([name, definition]) => {
    const constraints: string[] = [];
    if (Array.isArray(definition.enum)) {
      constraints.push(definition.enum.join(", "));
    }
    if (definition.format) {
      constraints.push(`format: ${definition.format}`);
    }
    if (definition.minLength || definition.maxLength) {
      constraints.push(`length: ${definition.minLength ?? 0}-${definition.maxLength ?? "∞"}`);
    }
    if (definition.minimum !== undefined) {
      constraints.push(`min: ${definition.minimum}`);
    }
    if (definition.pattern) {
      constraints.push(`regex: ${definition.pattern}`);
    }
    return {
      name,
      type: String(definition.type ?? "object").toUpperCase(),
      constraints: constraints.join(" - ") || "--",
      required: required.has(name),
    };
  });
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
