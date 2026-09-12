"use client";

import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Props {
  anomalyType: string;
  rowData: Record<string, any>;
  onClose: () => void;
}

interface ExplainResponse {
  explanation: string;
  source: "ollama" | "rule_engine";
  model: string | null;
}

function Spinner() {
  return (
    <div
      style={{
        width: 20,
        height: 20,
        border: "2px solid var(--border)",
        borderTopColor: "var(--accent)",
        borderRadius: "50%",
      }}
      className="animate-spin"
    />
  );
}

function typeLabel(type: string): string {
  return (
    {
      speed_anomaly:    "Execution Gap — Speed Anomaly",
      repetitive_notes: "Process Violation — Repetitive Notes",
      blind_spot:       "Telemetry Failure — Blind Spot",
    }[type] ?? type
  );
}

function typeColor(type: string): string {
  return (
    {
      speed_anomaly:    "var(--danger)",
      repetitive_notes: "var(--warning)",
      blind_spot:       "var(--purple)",
    }[type] ?? "var(--accent)"
  );
}

function buildPayload(anomalyType: string, rowData: Record<string, any>) {
  // Map row data to the API's expected payload shape
  if (anomalyType === "speed_anomaly") {
    return {
      anomaly_type:    "speed_anomaly",
      ticket_id:       rowData.ticket_id,
      severity:        rowData.severity,
      time_to_close:   rowData.time_to_close,
      analyst:         rowData.analyst,
      alert_type:      rowData.alert_type,
      escalated:       rowData.escalated,
      explanation:     rowData.explanation,
    };
  }
  if (anomalyType === "repetitive_notes") {
    return {
      anomaly_type:    "repetitive_notes",
      analyst:         rowData.analyst,
      alert_type:      (rowData.distinct_alert_types ?? []).join(", "),
      explanation:     rowData.explanation,
    };
  }
  // blind_spot
  return {
    anomaly_type:    "blind_spot",
    asset_id:        rowData.asset_id,
    actual_alerts:   rowData.actual_alerts,
    expected_mean:   rowData.expected_mean,
    explanation:     rowData.explanation,
  };
}

export default function ExplainModal({ anomalyType, rowData, onClose }: Props) {
  const [status, setStatus] = useState<"loading" | "done" | "error">("loading");
  const [response, setResponse] = useState<ExplainResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>("");

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  // Fetch explanation
  const fetchExplanation = useCallback(async () => {
    setStatus("loading");
    setResponse(null);
    setErrorMsg("");
    try {
      const payload = buildPayload(anomalyType, rowData);
      const res = await axios.post<ExplainResponse>(
        `${API_BASE}/api/explain-anomaly`,
        payload,
        { timeout: 120_000 }  // Ollama can be slow — give it 2 minutes
      );
      setResponse(res.data);
      setStatus("done");
    } catch (err: any) {
      setErrorMsg(err?.message ?? "Unknown error");
      setStatus("error");
    }
  }, [anomalyType, rowData]);

  useEffect(() => {
    fetchExplanation();
  }, [fetchExplanation]);

  const color = typeColor(anomalyType);

  return (
    <div
      className="modal-overlay"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div className="modal-box">
        {/* ── Header ── */}
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {/* Type indicator */}
            <div
              style={{
                width: 4,
                height: 28,
                background: color,
                borderRadius: 2,
                boxShadow: `0 0 8px ${color}`,
              }}
            />
            <div>
              <div
                id="modal-title"
                style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", marginBottom: 2 }}
              >
                {typeLabel(anomalyType)}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                {rowData.ticket_id && `Ticket: ${rowData.ticket_id}`}
                {rowData.analyst && !rowData.ticket_id && `Analyst: ${rowData.analyst}`}
                {rowData.asset_id && !rowData.ticket_id && !rowData.analyst && `Asset: ${rowData.asset_id}`}
              </div>
            </div>
          </div>

          {/* Close button */}
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--text-muted)",
              padding: 6,
              borderRadius: 6,
              display: "flex",
              alignItems: "center",
            }}
            id="modal-close"
            aria-label="Close"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {/* ── Body ── */}
        <div className="modal-body">
          {/* Anomaly metadata strip */}
          <div
            style={{
              background: "var(--bg-elevated)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "12px 16px",
              marginBottom: 20,
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
              gap: "8px 16px",
            }}
          >
            {Object.entries(rowData)
              .filter(([k]) => !["explanation", "ticket_ids", "distinct_alert_types"].includes(k))
              .slice(0, 8)
              .map(([k, v]) => (
                <div key={k}>
                  <div style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 2 }}>
                    {k.replace(/_/g, " ")}
                  </div>
                  <div
                    style={{
                      fontSize: 12,
                      color: "var(--text-secondary)",
                      fontWeight: 600,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {typeof v === "boolean" ? (v ? "Yes" : "No") : String(v ?? "N/A")}
                  </div>
                </div>
              ))}
          </div>

          {/* AI Explanation section */}
          <div
            style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--text-muted)",
              marginBottom: 12,
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-1H1a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"/>
            </svg>
            AI Audit Finding
          </div>

          {/* Loading state */}
          {status === "loading" && (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 12,
                padding: "32px 0",
                color: "var(--text-muted)",
                fontSize: 13,
              }}
            >
              <Spinner />
              <span>Querying local Ollama instance&hellip;</span>
              <span style={{ fontSize: 11, opacity: 0.6 }}>
                This may take 10–30 seconds depending on your hardware.
              </span>
            </div>
          )}

          {/* Error state */}
          {status === "error" && (
            <div
              style={{
                background: "var(--danger-dim)",
                border: "1px solid rgba(239,68,68,0.3)",
                borderRadius: 8,
                padding: "16px",
                fontSize: 13,
                color: "var(--danger)",
                marginBottom: 12,
              }}
            >
              <strong>Could not reach backend:</strong> {errorMsg}
              <div style={{ marginTop: 8 }}>
                <button className="btn btn-ghost" onClick={fetchExplanation} style={{ fontSize: 12 }}>
                  Retry
                </button>
              </div>
            </div>
          )}

          {/* Result */}
          {status === "done" && response && (
            <div>
              <div
                style={{
                  background: "var(--bg-elevated)",
                  border: `1px solid ${color}33`,
                  borderLeft: `3px solid ${color}`,
                  borderRadius: 8,
                  padding: "16px 20px",
                  fontSize: 14,
                  color: "var(--text-primary)",
                  lineHeight: 1.7,
                  marginBottom: 12,
                }}
              >
                {response.explanation}
              </div>

              {/* Source badge */}
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 5,
                    fontSize: 11,
                    fontWeight: 600,
                    padding: "3px 10px",
                    borderRadius: 999,
                    background:
                      response.source === "ollama"
                        ? "rgba(16,185,129,0.12)"
                        : "rgba(100,116,139,0.15)",
                    color:
                      response.source === "ollama"
                        ? "var(--success)"
                        : "var(--text-muted)",
                    border: `1px solid ${
                      response.source === "ollama"
                        ? "rgba(16,185,129,0.25)"
                        : "rgba(100,116,139,0.2)"
                    }`,
                  }}
                >
                  {response.source === "ollama" ? (
                    <>
                      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--success)" }} />
                      AI — {response.model ?? "Ollama"}
                    </>
                  ) : (
                    <>
                      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--text-muted)" }} />
                      Rule Engine (Ollama unavailable)
                    </>
                  )}
                </span>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  All inference runs locally. No data left this machine.
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
