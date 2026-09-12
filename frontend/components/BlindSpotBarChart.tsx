"use client";

import React, { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
  Legend,
} from "recharts";

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
  blindSpots: BlindSpot[];
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: any[]; label?: string }) => {
  if (!active || !payload?.length) return null;
  const isSilent = payload[0]?.payload?.isSilent;

  return (
    <div
      style={{
        background: "var(--bg-elevated)",
        border: `1px solid ${isSilent ? "rgba(239,68,68,0.4)" : "var(--border)"}`,
        borderRadius: 8,
        padding: "12px 16px",
        minWidth: 200,
        boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
      }}
    >
      <div style={{ fontWeight: 700, color: "var(--text-primary)", marginBottom: 8, fontSize: 13 }}>
        {label}
      </div>
      {isSilent && (
        <div
          style={{
            background: "var(--danger-dim)",
            border: "1px solid rgba(239,68,68,0.25)",
            borderRadius: 4,
            padding: "4px 8px",
            fontSize: 11,
            fontWeight: 700,
            color: "var(--danger)",
            marginBottom: 8,
            letterSpacing: "0.05em",
          }}
        >
          TELEMETRY BLIND SPOT
        </div>
      )}
      {payload.map((p: any) => (
        <div
          key={p.name}
          style={{ display: "flex", justifyContent: "space-between", gap: 16, fontSize: 12, marginBottom: 2 }}
        >
          <span style={{ color: "var(--text-muted)" }}>{p.name}</span>
          <span style={{ color: p.color, fontWeight: 600 }}>{p.value}</span>
        </div>
      ))}
      <div
        style={{
          marginTop: 8,
          fontSize: 11,
          color: "var(--text-muted)",
          borderTop: "1px solid var(--border-subtle)",
          paddingTop: 8,
        }}
      >
        {payload[0]?.payload?.asset_type}
      </div>
    </div>
  );
};

export default function BlindSpotBarChart({ blindSpots }: Props) {
  const data = useMemo(
    () =>
      blindSpots.map((b) => ({
        name:           b.asset_id.length > 14 ? b.asset_id.slice(0, 12) + "…" : b.asset_id,
        fullName:       b.asset_id,
        actual_alerts:  b.actual_alerts,
        expected_mean:  Math.round(b.expected_mean),
        isSilent:       b.actual_alerts === 0,
        criticality:    b.criticality,
        asset_type:     b.asset_type,
      })),
    [blindSpots]
  );

  const maxExpected = Math.max(...data.map((d) => d.expected_mean), 1);

  return (
    <div className="card" style={{ height: 380 }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--purple)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
            <line x1="1" y1="1" x2="23" y2="23"/>
          </svg>
          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
            Asset Telemetry — Negative Space
          </span>
          <span
            style={{
              marginLeft: "auto",
              fontSize: 11,
              background: "var(--purple-dim)",
              color: "var(--purple)",
              border: "1px solid rgba(139,92,246,0.25)",
              borderRadius: 999,
              padding: "1px 8px",
              fontWeight: 600,
            }}
          >
            {blindSpots.filter((b) => b.actual_alerts === 0).length} silent
          </span>
        </div>
        <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
          Actual vs. expected alert volume per flagged asset. Red bars indicate complete telemetry silence.
        </p>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 40, left: 0 }} barGap={4}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />

          <XAxis
            dataKey="name"
            tick={{ fill: "var(--text-muted)", fontSize: 10 }}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
            angle={-35}
            textAnchor="end"
            interval={0}
          />

          <YAxis
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
            domain={[0, Math.ceil(maxExpected * 1.2)]}
          />

          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(59,130,246,0.04)" }} />

          <Legend
            wrapperStyle={{ fontSize: 12, color: "var(--text-muted)", paddingTop: 4 }}
            formatter={(value) =>
              value === "actual_alerts" ? "Actual Alerts" : "Expected (mean)"
            }
          />

          {/* Expected mean — ghost bars */}
          <Bar dataKey="expected_mean" fill="var(--border)" radius={[4, 4, 0, 0]} opacity={0.5} name="expected_mean" />

          {/* Actual alerts — red for silent, blue otherwise */}
          <Bar dataKey="actual_alerts" radius={[4, 4, 0, 0]} name="actual_alerts">
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.isSilent ? "var(--danger)" : "var(--accent)"}
                opacity={entry.isSilent ? 0.9 : 0.75}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
