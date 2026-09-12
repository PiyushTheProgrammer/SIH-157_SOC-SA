"use client";

import React, { useMemo } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Legend,
  Cell,
} from "recharts";

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

interface Props {
  anomalies: SpeedAnomaly[];
}

const SEVERITY_X: Record<string, number> = {
  LOW: 1,
  MEDIUM: 2,
  HIGH: 3,
  CRITICAL: 4,
};

const SEVERITY_COLOR: Record<string, string> = {
  LOW:      "#10b981",
  MEDIUM:   "#fbbf24",
  HIGH:     "#f59e0b",
  CRITICAL: "#ef4444",
};

const SEVERITY_LABELS: Record<number, string> = {
  1: "LOW",
  2: "MEDIUM",
  3: "HIGH",
  4: "CRITICAL",
};

// Custom tooltip component
const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: any[] }) => {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;

  return (
    <div
      style={{
        background: "var(--bg-elevated)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: "12px 16px",
        minWidth: 220,
        boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
      }}
    >
      <div style={{ fontWeight: 700, color: "var(--text-primary)", marginBottom: 8, fontSize: 13 }}>
        {d.ticket_id}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {[
          ["Severity",    d.severity],
          ["Time to Close", `${d.time_to_close}s`],
          ["Alert Type",  d.alert_type],
          ["Analyst",     d.analyst],
          ["Escalated",   d.escalated ? "Yes" : "No"],
        ].map(([k, v]) => (
          <div key={k} style={{ display: "flex", justifyContent: "space-between", gap: 16, fontSize: 12 }}>
            <span style={{ color: "var(--text-muted)" }}>{k}</span>
            <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>{v}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default function SpeedScatterPlot({ anomalies }: Props) {
  const data = useMemo(
    () =>
      anomalies.map((a) => ({
        ...a,
        x: SEVERITY_X[a.severity] ?? 2,
        // Add slight jitter on X so dots don't completely overlap
        xJitter: (SEVERITY_X[a.severity] ?? 2) + (Math.random() - 0.5) * 0.4,
        y: a.time_to_close,
      })),
    [anomalies]
  );

  return (
    <div className="card" style={{ height: 380 }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
          </svg>
          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
            Resolution Speed Anomalies
          </span>
          <span
            style={{
              marginLeft: "auto",
              fontSize: 11,
              background: "var(--danger-dim)",
              color: "var(--danger)",
              border: "1px solid rgba(239,68,68,0.25)",
              borderRadius: 999,
              padding: "1px 8px",
              fontWeight: 600,
            }}
          >
            {anomalies.length} flagged
          </span>
        </div>
        <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
          Scatter plot of severity vs. time-to-close. Points below threshold lines indicate rubber-stamping.
        </p>
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <ScatterChart margin={{ top: 8, right: 24, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />

          <XAxis
            dataKey="xJitter"
            type="number"
            domain={[0.5, 4.5]}
            tickCount={4}
            tickFormatter={(v) => SEVERITY_LABELS[Math.round(v)] ?? ""}
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
            label={{
              value: "Alert Severity",
              position: "insideBottom",
              offset: -4,
              fill: "var(--text-muted)",
              fontSize: 11,
            }}
          />

          <YAxis
            dataKey="y"
            type="number"
            domain={[0, 130]}
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
            tickFormatter={(v) => `${v}s`}
            label={{
              value: "Time to Close (seconds)",
              angle: -90,
              position: "insideLeft",
              offset: 10,
              fill: "var(--text-muted)",
              fontSize: 11,
            }}
          />

          <Tooltip content={<CustomTooltip />} cursor={{ stroke: "var(--accent)", strokeWidth: 1, strokeDasharray: "4" }} />

          {/* CRITICAL threshold line at 120s */}
          <ReferenceLine
            y={120}
            stroke="var(--danger)"
            strokeDasharray="6 3"
            strokeOpacity={0.6}
            label={{ value: "CRITICAL threshold (120s)", fill: "var(--danger)", fontSize: 10, position: "right" }}
          />
          {/* HIGH threshold line at 60s */}
          <ReferenceLine
            y={60}
            stroke="var(--warning)"
            strokeDasharray="6 3"
            strokeOpacity={0.6}
            label={{ value: "HIGH threshold (60s)", fill: "var(--warning)", fontSize: 10, position: "right" }}
          />

          <Scatter
            data={data}
            fill="var(--accent)"
            opacity={0.85}
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={SEVERITY_COLOR[entry.severity] ?? "var(--accent)"}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
