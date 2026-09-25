"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "";
type RecordValue = Record<string, any>;
let overviewAnalyticsData: { dashboard: RecordValue; assessment: RecordValue } | null = null;

async function request(path: string, options?: RequestInit) {
  const response = await fetch(`${API}${path}`, options);
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail ?? `Request failed (${response.status})`); }
  return response;
}
async function json(path: string) { return (await request(path)).json(); }

function Shell({ children, path, setPath }: { children: React.ReactNode; path: string; setPath: (p: string) => void }) {
  const navItem = (href: string, label: string) => (
    <a
      href="#"
      className={path === href ? "active" : ""}
      onClick={(e) => { e.preventDefault(); setPath(href); }}
    >
      {label}
    </a>
  );
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <strong>SAT-SA</strong>
          <span>Supervisory Analytics for SOC Assessment</span>
        </div>
        <nav className="nav" aria-label="Primary navigation">
          <span className="nav-section-label">Analytics</span>
          {navItem("/", "Dashboard Overview")}
          {navItem("/data-ingestion", "Data Ingestion")}
          <div className="nav-divider" />
          <span className="nav-section-label">Supervisory Views</span>
          {navItem("/execution-gaps", "Execution Gaps")}
          {navItem("/negative-space", "Negative Space")}
          {navItem("/peer-comparison", "Peer Comparison")}
          <div className="nav-divider" />
          <span className="nav-section-label">Records</span>
          {navItem("/audit-reports", "Audit Reports")}
        </nav>
      </aside>
      <section className="main">
        <header className="topbar">
          <h1>SAT&#8209;SA &nbsp;<span style={{ fontWeight: 400, color: "var(--text-secondary)", fontSize: 13 }}>Supervisory Analytics for SOC Assessment</span></h1>
          <div className="topbar-meta">
            <span className="system-status"><b />System Operational</span>
          </div>
        </header>
        <div className="main-scroll">
          {children}
          <footer className="footer">
            <span>SAT-SA Prototype</span>
            <span>Evidence-based supervisory assessment using synthetic local data.</span>
          </footer>
        </div>
      </section>
    </div>
  );
}

function Page({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  const statisticalSection = title === "Dashboard Overview" && overviewAnalyticsData
    ? <AnalyticsStatistics dashboard={overviewAnalyticsData.dashboard} assessment={overviewAnalyticsData.assessment} />
    : null;
  return (
    <main className="content">
      <h1 className="page-title">{title}</h1>
      <p className="subtitle">{subtitle}</p>
      {statisticalSection}
      {children}
    </main>
  );
}

function EmptyState({ setPath }: { setPath?: (p: string) => void }) {
  return (
    <div className="panel" style={{ textAlign: "center", padding: "60px 20px" }}>
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
        style={{ margin: "0 auto 16px", color: "var(--text-muted)" }}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
      </svg>
      <h2 style={{ fontSize: "20px", fontWeight: "600", color: "var(--text-primary)", margin: "0 0 8px" }}>No Assessment Data Loaded</h2>
      <p style={{ color: "var(--text-secondary)", marginBottom: "24px", maxWidth: "400px", margin: "0 auto 24px" }}>
        Upload a SOC alert dataset (.csv or .json) via the Data Ingestion tab to begin supervisory analysis.
      </p>
      {setPath && (
        <button className="btn-primary" onClick={() => setPath("/data-ingestion")}>
          Go to Data Ingestion
        </button>
      )}
    </div>
  );
}

function LoadState({ error, setPath }: { error: string | null; setPath?: (p: string) => void }) {
  if (error && (error.includes("404") || error.includes("connect") || error.includes("Not Found"))) {
    return <EmptyState setPath={setPath} />;
  }
  return error
    ? <div className="error">{error}</div>
    : <div className="panel">Loading local assessment data...</div>;
}

function Tag({ value }: { value: string }) {
  const tone = ["Adequate","Observed","LOW","RESOLVED","CLOSED"].includes(value) ? "green"
    : ["Attention","Missing","CRITICAL","URGENT"].includes(value) ? "red" : "amber";
  return <span className={`tag ${tone}`}>{value}</span>;
}

/* ------------------------------------------------------------------ */
/* Upload Progress Bar Component                                        */
/* ------------------------------------------------------------------ */
const UPLOAD_STAGES = [
  { label: "Uploading Data",                      from: 0,  to: 25  },
  { label: "Running Scikit-Learn Anomaly Detection", from: 25, to: 60  },
  { label: "Generating Local LLM Rationales",     from: 60, to: 90  },
  { label: "Finalizing Audit Records",            from: 90, to: 100 },
] as const;

function UploadProgressBar({ progress }: { progress: number }) {
  const pct = Math.min(100, Math.max(0, progress));
  const stageIdx = UPLOAD_STAGES.findIndex(s => pct < s.to) === -1
    ? UPLOAD_STAGES.length - 1
    : UPLOAD_STAGES.findIndex(s => pct < s.to);
  const currentLabel = pct >= 100 ? "Complete!" : UPLOAD_STAGES[stageIdx].label;

  return (
    <div className="upload-progress-wrap" aria-live="polite" aria-label={`Upload progress: ${pct}%`}>
      <div className="upload-progress-header">
        <span className="upload-progress-stage">{currentLabel}</span>
        <span className="upload-progress-pct">{pct}%</span>
      </div>
      <div className="upload-progress-track">
        <div className="upload-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="upload-progress-steps">
        {UPLOAD_STAGES.map((stage, i) => {
          const isDone = pct >= stage.to;
          const isActive = !isDone && pct >= stage.from;
          return (
            <div
              key={stage.label}
              className={`upload-progress-step${isDone ? " done" : isActive ? " active" : ""}`}
              title={stage.label}
            >
              {isDone ? "✓ " : isActive ? "⟳ " : ""}{stage.label}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Data Ingestion – single, centralised upload location                */
/* ------------------------------------------------------------------ */
function DataIngestion({ setPath }: { setPath: (p: string) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [dragOver, setDragOver] = useState(false);

  async function handleUpload(targetFile: File) {
    setFile(targetFile);
    setError("");
    setUploading(true);
    setProgress(0);

    // ── Stage 1: Uploading Data (0 → 25) ─────────────────────────────
    const advanceTo = (target: number, duration: number) =>
      new Promise<void>(resolve => {
        const start = Date.now();
        const startPct = progress ?? 0;
        function tick() {
          const elapsed = Date.now() - start;
          const fraction = Math.min(elapsed / duration, 1);
          const current = Math.round(startPct + (target - startPct) * fraction);
          setProgress(current);
          if (fraction < 1) requestAnimationFrame(tick);
          else resolve();
        }
        tick();
      });

    let currentPct = 0;
    const animate = async (target: number, duration: number) => {
      const start = Date.now();
      const from = currentPct;
      await new Promise<void>(resolve => {
        function tick() {
          const elapsed = Date.now() - start;
          const fraction = Math.min(elapsed / duration, 1);
          currentPct = Math.round(from + (target - from) * fraction);
          setProgress(currentPct);
          if (fraction < 1) requestAnimationFrame(tick);
          else resolve();
        }
        tick();
      });
    };

    try {
      // Fire actual upload while stage 1 animation plays
      const form = new FormData();
      form.append("file", targetFile);

      const uploadPromise = request("/api/upload", { method: "POST", body: form });

      // Stage 1: 0 → 25 (network upload)
      await animate(25, 900);

      // Stage 2: 25 → 60 (wait for backend + animate)
      await animate(60, 1400);

      // Stage 3: 60 → 90 (LLM rationale simulation)
      await animate(90, 1200);

      // Await actual API response before finalizing
      await uploadPromise;

      // Stage 4: 90 → 100 (finalize)
      await animate(100, 600);

      // Brief pause at 100% then navigate
      await new Promise(r => setTimeout(r, 800));
      setPath("/");
    } catch (err: any) {
      setProgress(null);
      setError(err.message || "Unable to connect to the local assessment API.");
    } finally {
      setUploading(false);
    }
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]; if (f) handleUpload(f);
  }
  function onDrop(e: React.DragEvent) {
    e.preventDefault(); setDragOver(false);
    const f = e.dataTransfer.files?.[0]; if (f) handleUpload(f);
  }

  return (
    <Page title="Data Ingestion" subtitle="Upload SOC alert data for supervisory analysis. Accepted formats: CSV and JSON.">
      <section className="panel" style={{ marginBottom: 20 }}>
        <div className="section-heading" style={{ marginBottom: 24 }}>
          <div>
            <h2>Upload Dataset</h2>
            <p className="chart-note">All processing is local. No data leaves the system.</p>
          </div>
          <span className="tag amber">LOCAL PROCESSING</span>
        </div>

        {/* Drop zone — single unbroken dashed border, fully centred content */}
        <label
          htmlFor="file-upload-input"
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            width: "100%",
            padding: "48px 32px",
            border: `2px dashed ${dragOver ? "var(--accent)" : "#cbd5e1"}`,
            borderRadius: 12,
            background: dragOver ? "var(--accent-dim)" : "#f8fafc",
            cursor: uploading ? "not-allowed" : "pointer",
            transition: "border-color 0.2s, background 0.2s",
            textAlign: "center",
            opacity: uploading ? 0.6 : 1,
            pointerEvents: uploading ? "none" : undefined,
          }}
        >
          <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
            style={{ color: dragOver ? "var(--accent)" : "var(--text-muted)", marginBottom: 14, transition: "color 0.2s" }}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
          <p style={{ margin: "0 0 6px", fontSize: 16, fontWeight: 600, color: "var(--text-primary)" }}>
            Drag &amp; drop your dataset here
          </p>
          <p style={{ margin: 0, fontSize: 14, color: "var(--text-secondary)" }}>
            or click to browse &mdash; accepts <strong>.csv</strong> and <strong>.json</strong>
          </p>
          <input id="file-upload-input" type="file" accept=".csv,.json" onChange={onFileChange} style={{ display: "none" }} />
        </label>

        <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 16 }}>
          {file
            ? <span className="file-badge">&#128196; {file.name} <span style={{ color: "var(--text-secondary)" }}>({(file.size / 1024).toFixed(1)} KB)</span></span>
            : <span className="file-badge" style={{ color: "var(--text-muted)" }}>No file selected</span>}
          <button className="btn-primary" onClick={() => file && handleUpload(file)} disabled={!file || uploading}>
            {uploading ? "Processing…" : "Submit for Analysis"}
          </button>
        </div>

        {/* Real-time progress bar — shown during upload */}
        {progress !== null && <UploadProgressBar progress={progress} />}

        {error && <div className="error" style={{ marginTop: 16 }}>{error}</div>}
      </section>

      <section className="panel">
        <h2>Format Reference</h2>
        <p className="chart-note">Your file must contain the following fields (CSV header row or JSON keys):</p>
        <table className="mini-table" style={{ marginTop: 8 }}>
          <thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead>
          <tbody>
            {[
              ["alert_id","string","Unique alert identifier (e.g. AL-1001)"],
              ["entity_id","string","Entity / organisation identifier (e.g. ENT-A)"],
              ["asset_name","string","Affected asset name (e.g. web-server-01)"],
              ["alert_category","string","Alert category (Malware, DDoS, Unauthorised Access)"],
              ["alert_severity","string","Severity level: Critical / High / Medium / Low"],
              ["time_to_close_seconds","integer","Resolution time in seconds"],
              ["escalated","boolean","Whether the alert was escalated (True / False)"],
              ["resolution_notes","string","Free-text analyst notes"],
            ].map(([field, type, desc]) => (
              <tr key={field}>
                <td><code style={{ color: "var(--accent)", fontSize: 11 }}>{field}</code></td>
                <td style={{ color: "var(--text-secondary)" }}>{type}</td>
                <td style={{ color: "var(--text-secondary)" }}>{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </Page>
  );
}

/* ------------------------------------------------------------------ */
/* Execution Gaps                                                       */
/* ------------------------------------------------------------------ */
function ExecutionGaps({ setPath }: { setPath: (p: string) => void }) {
  const [data, setData] = useState<RecordValue | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { json("/api/dashboard/summary").then(setData).catch(e => setError(e.message)); }, []);
  if (!data) return <Page title="Execution Gaps" subtitle="Rapid closures, template-driven notes, lack of escalation."><LoadState error={error} setPath={setPath} /></Page>;

  const speedCount = data.summary?.speed_anomalies_count ?? 0;
  const notesClusters = data.summary?.repetitive_notes_clusters ?? 0;
  const speedAnomalies: RecordValue[] = data.speed_anomalies ?? [];
  const hasData = speedCount > 0 || notesClusters > 0;

  return (
    <Page title="Execution Gaps" subtitle="Supervisory signals indicating shortcuts in alert resolution quality.">
      <div className="grid grid-2" style={{ marginBottom: 16 }}>
        <div className="panel">
          <div className="meta-label">Speed Anomalies</div>
          <div className="meta-value">{speedCount}</div>
          <p className="chart-note" style={{ marginTop: 8 }}>Alerts closed suspiciously fast relative to category norms.</p>
        </div>
        <div className="panel">
          <div className="meta-label">Repetitive Note Clusters</div>
          <div className="meta-value">{notesClusters}</div>
          <p className="chart-note" style={{ marginTop: 8 }}>Template-driven or copy-paste resolution notes detected.</p>
        </div>
      </div>
      <section className="panel">
        <div className="section-heading" style={{ marginBottom: 16 }}>
          <h2>Speed Anomaly Records</h2>
          <span className="muted-note">Alerts flagged for unusually fast closure</span>
        </div>
        {!hasData || speedAnomalies.length === 0 ? (
          <div style={{ padding: "32px 0", textAlign: "center" }}>
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
              style={{ margin: "0 auto 12px", display: "block", color: "var(--text-muted)" }}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 12h-15m0 0l6.75 6.75M4.5 12l6.75-6.75" />
            </svg>
            <p style={{ color: "var(--text-secondary)", margin: 0, fontSize: 14 }}>
              No execution gaps detected. Please upload logs in the Data Ingestion tab.
            </p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr>{["Alert ID","Entity","Asset","Category","Severity","Closed (s)","Escalated","Notes"].map(h => <th key={h}>{h}</th>)}</tr></thead>
              <tbody>
                {speedAnomalies.slice(0, 50).map((row: RecordValue, i: number) => (
                  <tr key={row.alert_id ?? i}>
                    <td>{row.alert_id}</td><td>{row.entity_id}</td><td>{row.asset_name}</td>
                    <td>{row.alert_category}</td>
                    <td><Tag value={(row.alert_severity ?? "").toUpperCase()} /></td>
                    <td><strong style={{ color: "var(--danger)" }}>{row.time_to_close_seconds}</strong></td>
                    <td>{row.escalated ? <Tag value="YES" /> : <span style={{ color: "var(--text-muted)" }}>No</span>}</td>
                    <td style={{ maxWidth: 280, whiteSpace: "normal" }}>{row.resolution_notes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </Page>
  );
}

/* ------------------------------------------------------------------ */
/* Negative Space                                                       */
/* ------------------------------------------------------------------ */
function NegativeSpace({ setPath }: { setPath: (p: string) => void }) {
  const [data, setData] = useState<RecordValue | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { json("/api/dashboard/summary").then(setData).catch(e => setError(e.message)); }, []);
  if (!data) return <Page title="Negative Space" subtitle="Missing telemetry and monitoring blind spots."><LoadState error={error} setPath={setPath} /></Page>;

  const blindCount = data.summary?.blind_spots_count ?? 0;
  const blindSpots: RecordValue[] = data.blind_spots ?? [];

  return (
    <Page title="Negative Space" subtitle="Assets and time windows with absent telemetry or monitoring coverage.">
      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="meta-label">Telemetry Blind Spots Detected</div>
        <div className="meta-value">{blindCount}</div>
      </div>
      <section className="panel">
        <div className="section-heading" style={{ marginBottom: 16 }}>
          <h2>Blind Spot Records</h2>
          <span className="muted-note">Assets or time windows with no monitoring signal</span>
        </div>
        {blindCount === 0 || blindSpots.length === 0 ? (
          <div style={{ padding: "32px 0", textAlign: "center" }}>
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
              style={{ margin: "0 auto 12px", display: "block", color: "var(--text-muted)" }}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <p style={{ color: "var(--text-secondary)", margin: 0, fontSize: 14 }}>
              No telemetry blind spots detected. Upload SOC records to run coverage analysis.
            </p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr>{["Entity","Asset","Window / Period","Signal Type","Status"].map(h => <th key={h}>{h}</th>)}</tr></thead>
              <tbody>
                {blindSpots.slice(0, 50).map((row: RecordValue, i: number) => (
                  <tr key={i}>
                    <td>{row.entity_id ?? "–"}</td>
                    <td>{row.asset_name ?? row.asset ?? "–"}</td>
                    <td>{row.window ?? row.period ?? "–"}</td>
                    <td>{row.signal_type ?? "Telemetry"}</td>
                    <td><Tag value="Missing" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </Page>
  );
}

/* ------------------------------------------------------------------ */
/* Peer Comparison                                                      */
/* ------------------------------------------------------------------ */
function PeerComparison({ setPath }: { setPath: (p: string) => void }) {
  const [data, setData] = useState<RecordValue | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { json("/api/assets").then(setData).catch(e => setError(e.message)); }, []);
  if (!data) return <Page title="Peer Comparison" subtitle="Entity benchmarking risk indicators."><LoadState error={error} setPath={setPath} /></Page>;
  const assets: RecordValue[] = data.assets ?? [];
  const sorted = [...assets].sort((a, b) => Math.abs(b.deviation ?? 0) - Math.abs(a.deviation ?? 0));
  return (
    <Page title="Peer Comparison" subtitle="Alert volume deviation relative to peer asset group norms.">
      <section className="panel">
        <div className="section-heading" style={{ marginBottom: 16 }}>
          <h2>Asset Risk Benchmarking</h2>
          <span className="muted-note">{assets.length} assets assessed</span>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr>{["Asset","Type","Dept","Alert Volume","Peer Expected","Deviation","Status"].map(h => <th key={h}>{h}</th>)}</tr></thead>
            <tbody>
              {sorted.map((asset: RecordValue, i: number) => (
                <tr key={asset.asset ?? i}>
                  <td><strong>{asset.asset}</strong></td>
                  <td>{asset.type}</td><td>{asset.department}</td>
                  <td>{asset.alert_volume}</td><td>{asset.expected_peer_volume}</td>
                  <td style={{ color: (asset.deviation ?? 0) > 0 ? "var(--danger)" : "var(--success)", fontWeight: 700 }}>
                    {(asset.deviation ?? 0) > 0 ? "+" : ""}{asset.deviation}
                  </td>
                  <td><Tag value={asset.monitoring_status === "Observed" ? "Observed" : "Attention"} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </Page>
  );
}

/* ------------------------------------------------------------------ */
/* Audit Reports                                                        */
/* ------------------------------------------------------------------ */
function AuditReports() {
  const [scope, setScope] = useState("assessment");
  const [format, setFormat] = useState("pdf");
  const [ticket, setTicket] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [download, setDownload] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  async function generate() {
    try {
      setError(null); setDownload(null); setGenerating(true);
      const res = await request("/api/reports/export", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scope, format, ticket_id: scope === "single_case" ? ticket : null }),
      });
      const blob = await res.blob();
      setDownload(URL.createObjectURL(blob));
    } catch (e: any) { setError(e.message); }
    finally { setGenerating(false); }
  }

  return (
    <Page title="Audit Reports" subtitle="Immutable logs of supervisory decisions. Generate and export assessment records.">
      <section className="panel" style={{ marginBottom: 16 }}>
        <h2 style={{ marginBottom: 18 }}>Generate Report</h2>
        <div className="report-builder">
          <label>Scope
            <select value={scope} onChange={e => setScope(e.target.value)}>
              <option value="assessment">Complete Assessment</option>
              <option value="findings">Findings</option>
              <option value="analytics">Analytics Signals</option>
              <option value="assets">Asset Monitoring</option>
              <option value="single_case">Single Case</option>
              <option value="custom">Custom Report</option>
            </select>
          </label>
          {scope === "single_case" && (
            <label>Ticket ID<input value={ticket} onChange={e => setTicket(e.target.value)} placeholder="TKT-000001" /></label>
          )}
          <label>Format
            <select value={format} onChange={e => setFormat(e.target.value)}>
              <option value="pdf">PDF</option><option value="json">JSON</option>
              <option value="csv">CSV</option><option value="txt">TXT</option>
            </select>
          </label>
          <button className="btn-primary" onClick={generate} disabled={generating || (scope === "single_case" && !ticket)}>
            {generating ? "Generating…" : "Generate Report"}
          </button>
          {download && <a className="download" href={download} download={`sat-sa-${scope}.${format}`}>↓ Download report</a>}
        </div>
        {error && <div className="error" style={{ marginTop: 16 }}>{error}</div>}
      </section>
      <div className="notice">
        Reports are generated locally from synthetic demonstration data. No official classification, affiliation, or external integration is implied.
      </div>
    </Page>
  );
}

/* ------------------------------------------------------------------ */
/* Charts                                                               */
/* ------------------------------------------------------------------ */
function SeverityDonut({ counts }: { counts: Record<string, number> }) {
  const total = Object.values(counts).reduce((s, v) => s + v, 0);
  const radius = 42; const circ = 2 * Math.PI * radius; let off = 0;
  const colors: Record<string, string> = { CRITICAL: "#f85149", HIGH: "#1f6feb", MEDIUM: "#e3b341", LOW: "#3fb950" };
  return (
    <div className="donut-wrap">
      <div className="donut-chart">
        <svg viewBox="0 0 112 112" role="img" aria-label={`Findings by severity, ${total} total`}>
          <circle cx="56" cy="56" r={radius} fill="none" stroke="#21262d" strokeWidth="14" />
          {["CRITICAL","HIGH","MEDIUM","LOW"].map(sev => {
            const len = total ? (counts[sev] / total) * circ : 0;
            const seg = <circle key={sev} cx="56" cy="56" r={radius} fill="none" stroke={colors[sev]}
              strokeWidth="14" strokeDasharray={`${len} ${circ - len}`} strokeDashoffset={-off} transform="rotate(-90 56 56)" />;
            off += len; return seg;
          })}
          <text x="56" y="53" textAnchor="middle" fill="#8b949e" fontSize="10">TOTAL</text>
          <text x="56" y="67" textAnchor="middle" fill="#e6edf3" fontSize="16" fontWeight="700">{total.toLocaleString()}</text>
        </svg>
      </div>
      <div className="severity-legend">
        {["CRITICAL","HIGH","MEDIUM","LOW"].map(sev => (
          <div key={sev}>
            <span className={`legend-mark ${sev.toLowerCase()}`} />
            <span>{sev}</span>
            <strong>{counts[sev].toLocaleString()}</strong>
            <small>{total ? `${Math.round((counts[sev] / total) * 100)}%` : "0%"}</small>
          </div>
        ))}
      </div>
    </div>
  );
}

function FindingsTrend({ anomalies }: { anomalies: RecordValue[] }) {
  const grouped = anomalies.reduce<Record<string, number>>((r, item) => {
    const date = String(item.timestamp || "").slice(0, 10);
    if (date) r[date] = (r[date] || 0) + 1; return r;
  }, {});
  const points = Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).slice(-10);
  const max = Math.max(...points.map(([, c]) => c), 1);
  const poly = points.map(([, c], i) =>
    `${10 + (i * 180) / Math.max(points.length - 1, 1)},${92 - (c / max) * 70}`).join(" ");
  return (
    <div className="trend-chart">
      <svg viewBox="0 0 200 112" role="img" aria-label="Findings trend">
        <line x1="10" y1="92" x2="190" y2="92" stroke="#30363d" strokeWidth="1" />
        <line x1="10" y1="22" x2="10" y2="92" stroke="#30363d" strokeWidth="1" />
        <polyline points={poly} fill="none" stroke="#1f6feb" strokeWidth="2.5" />
        {points.map(([date, c], i) => (
          <circle key={date} cx={10 + (i * 180) / Math.max(points.length - 1, 1)}
            cy={92 - (c / max) * 70} r="3" fill="#1f6feb"><title>{date}: {c}</title></circle>
        ))}
      </svg>
      <div className="trend-labels">
        {points.map(([date, c]) => <span key={date}>{date.slice(5)}<b>{c}</b></span>)}
      </div>
    </div>
  );
}

function AnalyticsStatistics({ dashboard, assessment }: { dashboard: RecordValue; assessment: RecordValue }) {
  const counts = ["CRITICAL","HIGH","MEDIUM","LOW"].reduce<Record<string, number>>((r, sev) => {
    r[sev] = assessment.findings.filter((f: RecordValue) => f.severity === sev).length; return r;
  }, {});
  const signals = [
    ["Speed anomalies", dashboard.summary.speed_anomalies_count, "red"],
    ["Repetitive-note clusters", dashboard.summary.repetitive_notes_clusters, "blue"],
    ["Telemetry blind spots", dashboard.summary.blind_spots_count, "black"],
  ];
  const assets = [...assessment.assets].sort((a: RecordValue, b: RecordValue) =>
    Math.abs(b.deviation) - Math.abs(a.deviation)).slice(0, 5);
  return (
    <>
      <section className="panel statistical-summary">
        <div className="section-heading">
          <h2>Statistical Assessment</h2>
          <span className="muted-note">Calculated from supplied operational evidence</span>
        </div>
        <div className="stat-grid">
          {[
            ["Analytics Signals", dashboard.summary.total_flagged_anomalies],
            ["Speed Anomalies", dashboard.summary.speed_anomalies_count],
            ["Repetitive Resolution Patterns", dashboard.summary.repetitive_notes_clusters],
            ["Telemetry Blind Spots", dashboard.summary.blind_spots_count],
            ["Records Assessed", assessment.lifecycle.records_assessed],
            ["Assets Monitored", assessment.assets.length],
          ].map(([label, value]) => (
            <div className="stat-block" key={label}>
              <strong>{Number(value).toLocaleString()}</strong>
              <span>{label}</span>
            </div>
          ))}
        </div>
      </section>
      <div className="analytics-grid">
        <section className="panel"><h2>Findings by Severity</h2><SeverityDonut counts={counts} /></section>
        <section className="panel">
          <h2>Findings Trend</h2>
          <p className="chart-note">Closure-speed signals by observed ticket date.</p>
          <FindingsTrend anomalies={dashboard.speed_anomalies} />
        </section>
      </div>
      <div className="analytics-grid">
        <section className="panel">
          <h2>Analytics Signal Breakdown</h2>
          <div className="signal-bars">
            {signals.map(([label, value, tone]) => (
              <div className="signal-bar" key={label}>
                <div><span>{label}</span><strong>{Number(value).toLocaleString()}</strong></div>
                <i className={tone} style={{ width: `${Math.min((Number(value) / Math.max(dashboard.summary.total_flagged_anomalies, 1)) * 100, 100)}%` }} />
              </div>
            ))}
          </div>
        </section>
        <section className="panel">
          <h2>Top Assets by Deviation</h2>
          <p className="chart-note">Largest observed departures from peer volume.</p>
          <table className="mini-table">
            <thead><tr><th>Asset</th><th>Deviation</th><th>Status</th></tr></thead>
            <tbody>
              {assets.map((asset: RecordValue) => (
                <tr key={asset.asset}>
                  <td>{asset.asset}</td>
                  <td>{asset.deviation > 0 ? "+" : ""}{asset.deviation}</td>
                  <td><Tag value={asset.monitoring_status === "Observed" ? "Observed" : "Attention"} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Dashboard Overview                                                   */
/* ------------------------------------------------------------------ */
function Overview({ setPath }: { setPath: (p: string) => void }) {
  const [data, setData] = useState<RecordValue | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    Promise.all([json("/api/assessment"), json("/api/dashboard/summary"), json("/api/priorities")])
      .then(([assessment, dashboard, priority]) => setData({ assessment, dashboard, priority }))
      .catch(e => setError(e.message));
  }, []);
  if (!data) return <Page title="Dashboard Overview" subtitle="Operational effectiveness based on available alert, process, and evidence records."><LoadState error={error} setPath={setPath} /></Page>;
  const { assessment, dashboard, priority } = data;
  overviewAnalyticsData = { assessment, dashboard };
  return (
    <Page title="Dashboard Overview" subtitle="High-level risk scores, analytics signals, and assessment dimensions.">
      <div className="grid grid-5">
        {[
          ["Records assessed", assessment.lifecycle.records_assessed.toLocaleString()],
          ["Findings requiring attention", assessment.findings.length],
          ["Analytics signals", dashboard.summary.total_flagged_anomalies],
          ["Assets monitored", assessment.assets.length],
          ["System status", "Operational"],
        ].map(([label, value]) => (
          <div className="panel" key={label}>
            <div className="meta-label">{label}</div>
            <div className="meta-value">{value}</div>
          </div>
        ))}
      </div>
      <div className="grid grid-2" style={{ marginTop: 16 }}>
        <section className="panel">
          <h2>Supervisory Assessment Summary</h2>
          <div style={{ fontSize: 30, margin: "12px 0" }}>
            {assessment.overall_score} <small style={{ color: "var(--text-secondary)", fontSize: 14 }}>/ 100</small>
          </div>
          <div className="bar"><span style={{ width: `${assessment.overall_score}%` }} /></div>
          <p className="subtitle" style={{ margin: "10px 0 0" }}>Weighted result across seven dimensions.</p>
        </section>
        <section className="panel">
          <h2>Findings by Severity</h2>
          <div className="severity-list">
            {["CRITICAL","HIGH","MEDIUM","LOW"].map(sev => (
              <div key={sev}>
                <Tag value={sev} />
                <strong>{assessment.findings.filter((f: RecordValue) => f.severity === sev).length}</strong>
              </div>
            ))}
          </div>
        </section>
      </div>
      <section className="panel" style={{ marginTop: 16 }}>
        <div className="section-heading">
          <h2>AI-Assisted Review Priority</h2>
          <span className="muted-note">Recommendation only. Analyst retains decision authority.</span>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>#</th><th>Case</th><th>Priority</th><th>Severity</th><th>Asset</th><th>Analyst</th><th>Reasons</th></tr></thead>
            <tbody>
              {priority.priorities.slice(0, 8).map((item: RecordValue) => (
                <tr key={item.ticket_id}>
                  <td>{item.rank}</td>
                  <td><a href={`/evidence?ticket=${item.ticket_id}`}>{item.ticket_id}</a></td>
                  <td><strong>{item.priority_score}</strong> <Tag value={item.priority} /></td>
                  <td><Tag value={item.severity} /></td>
                  <td>{item.asset}</td><td>{item.analyst}</td>
                  <td>{item.reasons.join("; ") || "Review recommended from available evidence."}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel" style={{ marginTop: 16 }}>
        <h2>Assessment Dimensions</h2>
        {assessment.dimensions.map((d: RecordValue) => (
          <div className="score-row" key={d.dimension}>
            <strong>{d.dimension}</strong>
            <span className="score-number">{d.score}</span>
            <div className="bar"><span style={{ width: `${d.score}%` }} /></div>
            <Tag value={d.status} />
            <small>{d.finding_count} findings</small>
          </div>
        ))}
      </section>
    </Page>
  );
}

/* ------------------------------------------------------------------ */
/* Legacy pages kept for existing API links                             */
/* ------------------------------------------------------------------ */
function Assessment() {
  const [data, setData] = useState<RecordValue | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { json("/api/assessment").then(setData).catch(e => setError(e.message)); }, []);
  return (
    <Page title="Assessment" subtitle="Transparent dimension scores and assessment logic.">
      {!data ? <LoadState error={error} /> : (
        <div className="grid grid-2">
          {data.dimensions.map((d: RecordValue) => (
            <section className="panel" key={d.dimension}>
              <div className="section-heading"><h2>{d.dimension}</h2><Tag value={d.status} /></div>
              <div style={{ fontSize: 28 }}>{d.score} <small className="muted-note">/ 100 | {d.weight * 100}% weight</small></div>
              <div className="bar" style={{ margin: "10px 0 16px" }}><span style={{ width: `${d.score}%` }} /></div>
              <p className="subtitle">Records assessed: {d.records_assessed} | Missing evidence: {d.records_missing_evidence}</p>
              <p className="logic">{d.assessment_logic}</p>
            </section>
          ))}
        </div>
      )}
    </Page>
  );
}

function Findings() {
  const [data, setData] = useState<RecordValue | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { json("/api/findings").then(setData).catch(e => setError(e.message)); }, []);
  return (
    <Page title="Findings" subtitle="Supervisory work queue. Automated findings are review signals, not final conclusions.">
      {!data ? <LoadState error={error} /> : (
        <section className="panel">
          <div className="filters">
            <select aria-label="Severity"><option>All severities</option></select>
            <select aria-label="Status"><option>All statuses</option><option>Open</option><option>Under Review</option></select>
            <select aria-label="Finding type"><option>All finding types</option></select>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr>{["Priority","Severity","Case ID","Finding","Asset","Analyst","Status"].map(x => <th key={x}>{x}</th>)}</tr></thead>
              <tbody>
                {data.findings.map((f: RecordValue) => (
                  <tr key={f.finding_id}>
                    <td><a href={`/prioritizer?ticket=${f.entity}`}>Review</a></td>
                    <td><Tag value={f.severity} /></td>
                    <td>{f.entity}</td><td>{f.observation}</td><td>{f.asset}</td>
                    <td>{f.analyst || "Not available"}</td>
                    <td><Tag value={f.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </Page>
  );
}

function PriorityWorkspace() {
  const [data, setData] = useState<RecordValue | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("ALL");
  const [classification, setClassification] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [sort, setSort] = useState("score");
  const [selected, setSelected] = useState<RecordValue | null>(null);
  useEffect(() => { json("/api/priorities").then(setData).catch(e => setError(e.message)); }, []);

  async function updateStatus(ticketId: string, nextStatus: string) {
    try {
      await request(`/api/priorities/${ticketId}/status`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus }),
      });
      setData(cur => cur ? { ...cur, priorities: cur.priorities.map((item: RecordValue) =>
        item.ticket_id === ticketId ? { ...item, status: nextStatus } : item) } : cur);
      setSelected(cur => cur ? { ...cur, status: nextStatus } : cur);
    } catch (err: any) { setError(err.message); }
  }

  if (!data) return <Page title="AI-Assisted Prioritization" subtitle="Decision-support recommendation. Final review remains with the analyst."><LoadState error={error} /></Page>;
  const visible = [...data.priorities]
    .filter((item: RecordValue) =>
      (severity === "ALL" || item.severity === severity) &&
      (classification === "ALL" || item.priority === classification) &&
      (statusFilter === "ALL" || item.status === statusFilter) &&
      [item.ticket_id, item.asset, item.analyst, item.alert_type].join(" ").toLowerCase().includes(query.toLowerCase()))
    .sort((a: RecordValue, b: RecordValue) =>
      sort === "rank" ? a.rank - b.rank :
      sort === "timestamp" ? String(b.timestamp).localeCompare(String(a.timestamp)) :
      b.priority_score - a.priority_score);

  return (
    <Page title="AI-Assisted Prioritization" subtitle="Recommendation only. Analyst retains decision authority.">
      <div className="filters">
        <input aria-label="Search cases" placeholder="Search case, asset, analyst..." value={query} onChange={e => setQuery(e.target.value)} />
        <select aria-label="Severity filter" value={severity} onChange={e => setSeverity(e.target.value)}>
          <option value="ALL">All severities</option>
          {["CRITICAL","HIGH","MEDIUM","LOW"].map(v => <option key={v}>{v}</option>)}
        </select>
        <select aria-label="Classification filter" value={classification} onChange={e => setClassification(e.target.value)}>
          <option value="ALL">All classifications</option>
          {["URGENT","HIGH","MEDIUM","LOW"].map(v => <option key={v}>{v}</option>)}
        </select>
        <select aria-label="Status filter" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="ALL">All statuses</option>
          {["NEW","UNDER_REVIEW","ASSIGNED","INVESTIGATING","ESCALATED","RESOLVED","CLOSED"].map(v => <option key={v}>{v}</option>)}
        </select>
        <select aria-label="Sort" value={sort} onChange={e => setSort(e.target.value)}>
          <option value="score">Sort by score</option>
          <option value="rank">Sort by rank</option>
          <option value="timestamp">Sort by newest</option>
        </select>
      </div>
      <section className="panel">
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Rank</th><th>Case</th><th>Score</th><th>Severity</th><th>Asset</th><th>Analyst</th><th>Timestamp</th><th>Status</th><th>Reasons</th></tr></thead>
            <tbody>
              {visible.map((item: RecordValue) => (
                <tr className="link-row" onClick={() => setSelected(item)} key={item.ticket_id}>
                  <td>{item.rank}</td><td>{item.ticket_id}</td>
                  <td><strong>{item.priority_score}</strong> <Tag value={item.priority_classification ?? item.priority} /></td>
                  <td><Tag value={item.severity} /></td>
                  <td>{item.asset}</td><td>{item.analyst}</td>
                  <td>{item.timestamp ? new Date(item.timestamp).toLocaleString() : "Not available"}</td>
                  <td>{item.status}</td>
                  <td>{item.reasons.join("; ") || "Review recommended from available evidence."}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {selected && (
        <aside className="detail">
          <div className="detail-header">
            <h2>{selected.ticket_id}</h2>
            <button className="close" aria-label="Close" onClick={() => setSelected(null)}>✕</button>
          </div>
          <p className="subtitle">Priority {selected.priority_score} | {selected.severity} | {selected.asset}</p>
          <label className="detail-status">Review status
            <select aria-label="Update status" value={selected.status} onChange={e => updateStatus(selected.ticket_id, e.target.value)}>
              {["NEW","UNDER_REVIEW","ASSIGNED","INVESTIGATING","ESCALATED","RESOLVED","CLOSED"].map(v => <option key={v}>{v}</option>)}
            </select>
          </label>
          <h3>Review reasons</h3>
          <ul>{selected.reasons.map((r: string) => <li key={r}>{r}</li>)}</ul>
          <p className="logic">Recommendation only. Final review remains with the analyst.</p>
        </aside>
      )}
    </Page>
  );
}

function SimpleDataPage({ endpoint, title, subtitle, columns }: { endpoint: string; title: string; subtitle: string; columns: string[] }) {
  const [data, setData] = useState<RecordValue | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { json(endpoint).then(setData).catch(e => setError(e.message)); }, [endpoint]);
  const rows = data?.evidence ?? data?.assets ?? [];
  return (
    <Page title={title} subtitle={subtitle}>
      {!data ? <LoadState error={error} /> : (
        <section className="panel">
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr>{columns.map(c => <th key={c}>{c.replaceAll("_", " ")}</th>)}</tr></thead>
              <tbody>
                {rows.slice(0, 200).map((row: RecordValue, i: number) => (
                  <tr key={row.ticket_id ?? row.asset ?? i}>
                    {columns.map(col => <td key={col}>{String(row[col] ?? "")}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </Page>
  );
}

function DataSystem() {
  const [data, setData] = useState<RecordValue | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { json("/api/data-quality").then(setData).catch(e => setError(e.message)); }, []);
  return (
    <Page title="Data &amp; System" subtitle="Dataset provenance, quality checks, and local processing status.">
      {!data ? <LoadState error={error} /> : (
        <div className="grid grid-2">
          {["dataset","data_quality","processing"].map(section => (
            <section className="panel" key={section}>
              <h2>{section.replaceAll("_", " ")}</h2>
              {Object.entries(data[section]).map(([key, value]) => (
                <div className="score-row" key={key}>
                  <span>{key.replaceAll("_", " ")}</span>
                  <strong>{String(value)}</strong>
                </div>
              ))}
            </section>
          ))}
        </div>
      )}
    </Page>
  );
}

function Evidence() {
  return <SimpleDataPage endpoint="/api/evidence" title="Evidence Review"
    subtitle="Lifecycle evidence review. Missing means not observed in the supplied records."
    columns={["ticket_id","severity","alert_type","analyst","asset","assessment"]} />;
}
function Assets() {
  return <SimpleDataPage endpoint="/api/assets" title="Asset Monitoring"
    subtitle="Peer comparison of observed alert volume and telemetry coverage."
    columns={["asset","criticality","type","department","alert_volume","expected_peer_volume","monitoring_status"]} />;
}

/* ------------------------------------------------------------------ */
/* App Router                                                           */
/* ------------------------------------------------------------------ */
export default function App() {
  const [path, setPath] = useState("/");

  const page =
    path === "/data-ingestion"  ? <DataIngestion setPath={setPath} /> :
    path === "/execution-gaps"  ? <ExecutionGaps setPath={setPath} /> :
    path === "/negative-space"  ? <NegativeSpace setPath={setPath} /> :
    path === "/peer-comparison" ? <PeerComparison setPath={setPath} /> :
    path === "/audit-reports"   ? <AuditReports /> :
    <Overview setPath={setPath} />;

  return <Shell path={path} setPath={setPath}>{page}</Shell>;
}

