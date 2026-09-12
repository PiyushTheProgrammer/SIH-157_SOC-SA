"use client";

import React, { useState } from "react";
import ExplainModal from "./ExplainModal";

// ── Type definitions ────────────────────────────────────────

interface SpeedAnomaly {
  ticket_id: string;
  severity: string;
  time_to_close: number;
  time_to_acknowledge: number;
  escalated: boolean;
  analyst: string;
  alert_type: string;
  dest_asset: string;
  timestamp: string;
  explanation: string;
}

interface RepetitiveCluster {
  analyst: string;
  repeated_note_snippet: string;
  ticket_ids: string[];
  distinct_alert_types: string[];
  ticket_count: number;
  explanation: string;
}

interface BlindSpot {
  asset_id: string;
  criticality: string;
  asset_type: string;
  actual_alerts: number;
  expected_mean: number;
  expected_std: number;
  explanation: string;
}

interface Props {
  speedAnomalies: SpeedAnomaly[];
  repetitiveNotes: RepetitiveCluster[];
  blindSpots: BlindSpot[];
}

// ── Shared helpers ───────────────────────────────────────────

function SeverityChip({ severity }: { severity: string }) {
  const cls: Record<string, string> = {
    CRITICAL: "chip chip-critical",
    HIGH:     "chip chip-high",
    MEDIUM:   "chip chip-medium",
    LOW:      "chip chip-low",
  };
  return <span className={cls[severity] ?? "chip chip-low"}>{severity}</span>;
}

function EscalatedBadge({ escalated }: { escalated: boolean }) {
  return (
    <span
      style={{
        fontSize: 11,
        fontWeight: 600,
        color: escalated ? "var(--success)" : "var(--text-muted)",
        display: "flex",
        alignItems: "center",
        gap: 4,
      }}
    >
      {escalated ? "✓ Yes" : "✗ No"}
    </span>
  );
}

function formatTimestamp(ts: string) {
  try {
    return new Date(ts).toLocaleString("en-IN", {
      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return ts;
  }
}

// ── Tab: Speed Anomalies ─────────────────────────────────────

function SpeedAnomalyTab({
  data,
  onExplain,
}: {
  data: SpeedAnomaly[];
  onExplain: (row: object, type: string) => void;
}) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="sat-table">
        <thead>
          <tr>
            <th>Ticket ID</th>
            <th>Severity</th>
            <th>Alert Type</th>
            <th>Analyst</th>
            <th>Close Time</th>
            <th>Escalated</th>
            <th>Asset</th>
            <th>Date</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {data.slice(0, 200).map((row) => (
            <tr key={row.ticket_id}>
              <td style={{ fontFamily: "monospace", fontSize: 12, color: "var(--accent)" }}>
                {row.ticket_id}
              </td>
              <td><SeverityChip severity={row.severity} /></td>
              <td>{row.alert_type}</td>
              <td>{row.analyst}</td>
              <td>
                <span style={{ color: "var(--danger)", fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
                  {row.time_to_close}s
                </span>
              </td>
              <td><EscalatedBadge escalated={row.escalated} /></td>
              <td style={{ fontSize: 12, fontFamily: "monospace" }}>{row.dest_asset}</td>
              <td style={{ fontSize: 12 }}>{formatTimestamp(row.timestamp)}</td>
              <td>
                <button
                  className="btn btn-ghost"
                  onClick={() => onExplain(row, "speed_anomaly")}
                  id={`explain-speed-${row.ticket_id}`}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                  </svg>
                  Explain
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {data.length > 200 && (
        <div style={{ padding: "12px 14px", fontSize: 12, color: "var(--text-muted)" }}>
          Showing 200 of {data.length} flagged tickets.
        </div>
      )}
    </div>
  );
}

// ── Tab: Repetitive Notes ────────────────────────────────────

function RepetitiveNotesTab({
  data,
  onExplain,
}: {
  data: RepetitiveCluster[];
  onExplain: (row: object, type: string) => void;
}) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="sat-table">
        <thead>
          <tr>
            <th>Analyst</th>
            <th>Tickets</th>
            <th>Alert Types Spanned</th>
            <th>Note Snippet</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={`${row.analyst}-${i}`}>
              <td style={{ fontWeight: 600, color: "var(--text-primary)" }}>{row.analyst}</td>
              <td>
                <span
                  style={{
                    background: "var(--warning-dim)",
                    color: "var(--warning)",
                    border: "1px solid rgba(245,158,11,0.25)",
                    borderRadius: 999,
                    padding: "2px 10px",
                    fontSize: 12,
                    fontWeight: 700,
                  }}
                >
                  {row.ticket_count}
                </span>
              </td>
              <td>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {row.distinct_alert_types.slice(0, 5).map((t) => (
                    <span
                      key={t}
                      style={{
                        background: "var(--bg-elevated)",
                        border: "1px solid var(--border)",
                        borderRadius: 4,
                        padding: "1px 6px",
                        fontSize: 10,
                        color: "var(--text-secondary)",
                      }}
                    >
                      {t}
                    </span>
                  ))}
                  {row.distinct_alert_types.length > 5 && (
                    <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
                      +{row.distinct_alert_types.length - 5} more
                    </span>
                  )}
                </div>
              </td>
              <td
                style={{
                  maxWidth: 260,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  fontStyle: "italic",
                  fontSize: 12,
                  color: "var(--text-muted)",
                }}
                title={row.repeated_note_snippet}
              >
                &ldquo;{row.repeated_note_snippet}&rdquo;
              </td>
              <td>
                <button
                  className="btn btn-ghost"
                  onClick={() => onExplain(row, "repetitive_notes")}
                  id={`explain-rep-${row.analyst.replace(/\s/g, "-")}-${i}`}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                  </svg>
                  Explain
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Tab: Blind Spots ─────────────────────────────────────────

function BlindSpotTab({
  data,
  onExplain,
}: {
  data: BlindSpot[];
  onExplain: (row: object, type: string) => void;
}) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="sat-table">
        <thead>
          <tr>
            <th>Asset ID</th>
            <th>Criticality</th>
            <th>Type</th>
            <th>Actual Alerts</th>
            <th>Expected Mean</th>
            <th>Expected Std</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.asset_id}>
              <td style={{ fontFamily: "monospace", fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>
                {row.asset_id}
              </td>
              <td><SeverityChip severity={row.criticality} /></td>
              <td style={{ fontSize: 12 }}>{row.asset_type}</td>
              <td>
                {row.actual_alerts === 0 ? (
                  <span style={{ color: "var(--danger)", fontWeight: 700, display: "flex", alignItems: "center", gap: 4 }}>
                    <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--danger)", display: "inline-block" }} />
                    0 (SILENT)
                  </span>
                ) : (
                  <span style={{ color: "var(--warning)", fontWeight: 600 }}>{row.actual_alerts}</span>
                )}
              </td>
              <td style={{ color: "var(--text-secondary)", fontVariantNumeric: "tabular-nums" }}>
                {row.expected_mean.toFixed(1)}
              </td>
              <td style={{ color: "var(--text-muted)", fontVariantNumeric: "tabular-nums" }}>
                ±{row.expected_std.toFixed(1)}
              </td>
              <td>
                <button
                  className="btn btn-ghost"
                  onClick={() => onExplain(row, "blind_spot")}
                  id={`explain-blind-${row.asset_id}`}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                  </svg>
                  Explain
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main AnomalyTable ────────────────────────────────────────

export default function AnomalyTable({ speedAnomalies, repetitiveNotes, blindSpots }: Props) {
  const [activeTab, setActiveTab] = useState<"speed" | "notes" | "blind">("speed");
  const [modalData, setModalData] = useState<{ row: object; type: string } | null>(null);

  const handleExplain = (row: object, type: string) => {
    setModalData({ row, type });
  };

  const tabs = [
    { id: "speed", label: `Execution Gaps (${speedAnomalies.length})` },
    { id: "notes", label: `Repetitive Notes (${repetitiveNotes.length})` },
    { id: "blind", label: `Blind Spots (${blindSpots.length})` },
  ] as const;

  return (
    <div className="card" style={{ padding: 0 }}>
      {/* Card header */}
      <div
        style={{
          padding: "20px 24px 0",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 2 }}>Drill-Down Evidence Table</h3>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
            All flagged anomalies. Click &ldquo;Explain&rdquo; to generate an AI audit rationale.
          </p>
        </div>
        {/* Tabs */}
        <div style={{ display: "flex", gap: 0 }}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: "8px 20px",
                color: activeTab === tab.id ? "var(--accent)" : "var(--text-muted)",
                fontWeight: activeTab === tab.id ? 700 : 500,
                fontSize: 12,
                background: "none",
                border: "none",
                borderBottom: activeTab === tab.id ? "2px solid var(--accent)" : "2px solid transparent",
                cursor: "pointer",
                transition: "all 0.15s ease",
                letterSpacing: "0.02em",
              }}
              id={`tab-${tab.id}`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === "speed" && (
          <SpeedAnomalyTab data={speedAnomalies} onExplain={handleExplain} />
        )}
        {activeTab === "notes" && (
          <RepetitiveNotesTab data={repetitiveNotes} onExplain={handleExplain} />
        )}
        {activeTab === "blind" && (
          <BlindSpotTab data={blindSpots} onExplain={handleExplain} />
        )}
      </div>

      {/* Explain Modal */}
      {modalData && (
        <ExplainModal
          anomalyType={modalData.type}
          rowData={modalData.row}
          onClose={() => setModalData(null)}
        />
      )}
    </div>
  );
}
