"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import MetricsBar from "@/components/MetricsBar";
import SpeedScatterPlot from "@/components/SpeedScatterPlot";
import BlindSpotBarChart from "@/components/BlindSpotBarChart";
import AnomalyTable from "@/components/AnomalyTable";
import RiskScoreBadge from "@/components/RiskScoreBadge";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types ────────────────────────────────────────────────────

interface Summary {
  total_alerts: number;
  total_flagged_anomalies: number;
  speed_anomalies_count: number;
  repetitive_notes_clusters: number;
  repetitive_notes_tickets: number;
  blind_spots_count: number;
  overall_risk_score: number;
  entity_risk: EntityRisk[];
}

interface EntityRisk {
  entity: string;
  risk_score: number;
  speed_anomalies?: number;
  repetitive_notes?: number;
  blind_spot?: boolean;
}

interface DashboardData {
  summary: Summary;
  speed_anomalies: any[];
  repetitive_notes: any[];
  blind_spots: any[];
}

// ── Loading skeleton ─────────────────────────────────────────

function Skeleton({ height = 200 }: { height?: number }) {
  return <div className="skeleton" style={{ height, borderRadius: 12, width: "100%" }} />;
}

// ── Upload component ─────────────────────────────────────────

function UploadZone({ onUploaded }: { onUploaded: () => void }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    if (!file.name.endsWith(".csv")) {
      setError("Only CSV files are accepted.");
      return;
    }
    setUploading(true);
    setMessage(null);
    setError(null);

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await axios.post(`${API_BASE}/api/upload`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setMessage(res.data.message);
      // Wait 3s for engine to process then refresh
      setTimeout(onUploaded, 3000);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div
      className={`upload-zone ${dragging ? "drag-over" : ""}`}
      onDragEnter={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
      }}
      onClick={() => inputRef.current?.click()}
      id="upload-zone"
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        style={{ display: "none" }}
        id="csv-file-input"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />

      <svg
        width="32"
        height="32"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--accent)"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ marginBottom: 12, opacity: 0.7 }}
      >
        <polyline points="16 16 12 12 8 16" />
        <line x1="12" y1="12" x2="12" y2="21" />
        <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
      </svg>

      {uploading ? (
        <div style={{ color: "var(--accent)", fontSize: 13 }}>Uploading and analysing&hellip;</div>
      ) : (
        <>
          <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
            Drop a SOC Alerts CSV here
          </div>
          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
            or click to browse — replaces current dataset
          </div>
        </>
      )}

      {message && (
        <div
          style={{
            marginTop: 12,
            padding: "8px 16px",
            background: "var(--success-dim)",
            border: "1px solid rgba(16,185,129,0.25)",
            borderRadius: 6,
            fontSize: 12,
            color: "var(--success)",
          }}
        >
          {message}
        </div>
      )}
      {error && (
        <div
          style={{
            marginTop: 12,
            padding: "8px 16px",
            background: "var(--danger-dim)",
            border: "1px solid rgba(239,68,68,0.25)",
            borderRadius: 6,
            fontSize: 12,
            color: "var(--danger)",
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}

// ── Entity Risk Table ─────────────────────────────────────────

function EntityRiskTable({ entities }: { entities: EntityRisk[] }) {
  const top = [...entities].sort((a, b) => b.risk_score - a.risk_score).slice(0, 10);

  return (
    <div className="card">
      <div style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 2 }}>Top Entity Risk Scores</h3>
        <p style={{ fontSize: 12, color: "var(--text-muted)" }}>Analysts and assets ranked by composite risk.</p>
      </div>
      <table className="sat-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Entity</th>
            <th>Speed Anomalies</th>
            <th>Rep. Notes</th>
            <th>Risk Score</th>
          </tr>
        </thead>
        <tbody>
          {top.map((e, i) => {
            const barW = Math.round(e.risk_score);
            const color =
              e.risk_score > 70 ? "var(--danger)" :
              e.risk_score > 40 ? "var(--warning)" :
              "var(--success)";
            return (
              <tr key={e.entity}>
                <td style={{ color: "var(--text-muted)", width: 32 }}>{i + 1}</td>
                <td style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: 13 }}>
                  {e.blind_spot ? (
                    <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span className="chip chip-blind" style={{ fontSize: 9 }}>ASSET</span>
                      {e.entity}
                    </span>
                  ) : e.entity}
                </td>
                <td style={{ color: "var(--text-secondary)" }}>{e.speed_anomalies ?? 0}</td>
                <td style={{ color: "var(--text-secondary)" }}>{e.repetitive_notes ?? 0}</td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div
                      style={{
                        flex: 1,
                        height: 4,
                        background: "var(--bg-elevated)",
                        borderRadius: 2,
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          width: `${barW}%`,
                          height: "100%",
                          background: color,
                          borderRadius: 2,
                          transition: "width 0.6s ease",
                        }}
                      />
                    </div>
                    <span
                      style={{
                        fontSize: 12,
                        fontWeight: 700,
                        color,
                        width: 36,
                        textAlign: "right",
                        fontVariantNumeric: "tabular-nums",
                      }}
                    >
                      {e.risk_score}
                    </span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get<DashboardData>(`${API_BASE}/api/dashboard/summary`, {
        timeout: 10_000,
      });
      setData(res.data);
      setLastRefresh(new Date());
    } catch (err: any) {
      setError(
        err?.response?.status === 503
          ? "No data loaded yet. The analytics engine is warming up or no CSV has been uploaded."
          : `Could not connect to backend at ${API_BASE}. Is uvicorn running?`
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1400, margin: "0 auto" }}>

      {/* ── Page header ── */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          marginBottom: 28,
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 4, letterSpacing: "-0.03em" }}>
            SOC Audit Dashboard
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
            Automated anomaly detection for supervisory review.{" "}
            {lastRefresh && (
              <span>Last updated: {lastRefresh.toLocaleTimeString("en-IN")}</span>
            )}
          </p>
        </div>

        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {data && (
            <RiskScoreBadge score={data.summary.overall_risk_score} size={72} />
          )}
          <button
            className="btn btn-ghost"
            onClick={fetchData}
            id="refresh-btn"
            title="Refresh data"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ transform: loading ? "rotate(360deg)" : "none", transition: "transform 0.5s" }}
            >
              <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* ── Error state ── */}
      {error && (
        <div
          style={{
            background: "var(--danger-dim)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 10,
            padding: "16px 20px",
            marginBottom: 24,
            color: "var(--danger)",
            fontSize: 13,
          }}
        >
          <strong>Connection Error:</strong> {error}
        </div>
      )}

      {/* ── Loading skeleton ── */}
      {loading && !data && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ display: "flex", gap: 16 }}>
            {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} height={100} />)}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            <Skeleton height={360} />
            <Skeleton height={360} />
          </div>
          <Skeleton height={400} />
        </div>
      )}

      {/* ── Dashboard content ── */}
      {data && (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>

          {/* Metrics bar */}
          <MetricsBar summary={data.summary} />

          <div className="glow-line" />

          {/* Charts row */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            <SpeedScatterPlot anomalies={data.speed_anomalies} />
            <BlindSpotBarChart blindSpots={data.blind_spots} />
          </div>

          {/* Entity risk + upload row */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 380px", gap: 20 }}>
            <EntityRiskTable entities={data.summary.entity_risk} />

            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {/* Upload zone */}
              <div className="card" style={{ padding: 0 }}>
                <div style={{ padding: "16px 20px 12px", borderBottom: "1px solid var(--border)" }}>
                  <h3 style={{ fontSize: 13, fontWeight: 700 }}>Upload New Dataset</h3>
                  <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                    Replace the current CSV to re-run analysis.
                  </p>
                </div>
                <div style={{ padding: 20 }}>
                  <UploadZone onUploaded={fetchData} />
                </div>
              </div>

              {/* Quick stats */}
              <div className="card">
                <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>Analysis Summary</h3>
                {[
                  ["Total Tickets Analysed", data.summary.total_alerts.toLocaleString(), "var(--accent)"],
                  ["Total Flagged Items", data.summary.total_flagged_anomalies.toLocaleString(), "var(--danger)"],
                  ["Speed Anomalies", data.summary.speed_anomalies_count.toString(), "var(--danger)"],
                  ["Note Clusters", data.summary.repetitive_notes_clusters.toString(), "var(--warning)"],
                  ["Affected Tickets (Notes)", data.summary.repetitive_notes_tickets.toString(), "var(--warning)"],
                  ["Silent Critical Assets", data.summary.blind_spots_count.toString(), "var(--purple)"],
                ].map(([label, val, color]) => (
                  <div
                    key={label}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "7px 0",
                      borderBottom: "1px solid var(--border-subtle)",
                    }}
                  >
                    <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{label}</span>
                    <span style={{ fontSize: 13, fontWeight: 700, color, fontVariantNumeric: "tabular-nums" }}>
                      {val}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="glow-line" />

          {/* Full drill-down table */}
          <AnomalyTable
            speedAnomalies={data.speed_anomalies}
            repetitiveNotes={data.repetitive_notes}
            blindSpots={data.blind_spots}
          />

          {/* Footer */}
          <div
            style={{
              padding: "16px 0",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              borderTop: "1px solid var(--border-subtle)",
              fontSize: 11,
              color: "var(--text-muted)",
            }}
          >
            <span>SAT-SA v1.0 — Air-Gapped SOC Analytics Tool</span>
            <span>All processing is local. Zero network egress.</span>
          </div>
        </div>
      )}
    </div>
  );
}
