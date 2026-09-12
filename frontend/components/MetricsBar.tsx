"use client";

import React from "react";

interface MetricCardProps {
  label: string;
  value: number | string;
  subtext?: string;
  color?: "accent" | "danger" | "warning" | "success" | "purple";
  icon: React.ReactNode;
}

function MetricCard({ label, value, subtext, color = "accent", icon }: MetricCardProps) {
  const colorMap: Record<string, string> = {
    accent:  "var(--accent)",
    danger:  "var(--danger)",
    warning: "var(--warning)",
    success: "var(--success)",
    purple:  "var(--purple)",
  };
  const dimMap: Record<string, string> = {
    accent:  "var(--accent-glow)",
    danger:  "var(--danger-dim)",
    warning: "var(--warning-dim)",
    success: "var(--success-dim)",
    purple:  "var(--purple-dim)",
  };

  return (
    <div
      className="card"
      style={{ display: "flex", alignItems: "flex-start", gap: 16, flex: 1, minWidth: 160 }}
    >
      {/* Icon */}
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: 10,
          background: dimMap[color],
          border: `1px solid ${colorMap[color]}33`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: colorMap[color],
          flexShrink: 0,
        }}
      >
        {icon}
      </div>

      {/* Text */}
      <div style={{ flex: 1 }}>
        <div
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            color: "var(--text-muted)",
            marginBottom: 4,
          }}
        >
          {label}
        </div>
        <div
          style={{
            fontSize: 28,
            fontWeight: 700,
            color: colorMap[color],
            lineHeight: 1,
            marginBottom: 4,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {typeof value === "number" ? value.toLocaleString() : value}
        </div>
        {subtext && (
          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{subtext}</div>
        )}
      </div>
    </div>
  );
}

interface MetricsBarProps {
  summary: {
    total_alerts: number;
    speed_anomalies_count: number;
    repetitive_notes_clusters: number;
    repetitive_notes_tickets: number;
    blind_spots_count: number;
    overall_risk_score: number;
  };
}

export default function MetricsBar({ summary }: MetricsBarProps) {
  return (
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>

      {/* Total Alerts */}
      <MetricCard
        label="Total Alerts Processed"
        value={summary.total_alerts}
        subtext="30-day analysis window"
        color="accent"
        icon={
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
        }
      />

      {/* Execution Gaps */}
      <MetricCard
        label="Execution Gaps"
        value={summary.speed_anomalies_count}
        subtext="Improbably fast closures"
        color="danger"
        icon={
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
          </svg>
        }
      />

      {/* Repetitive Notes */}
      <MetricCard
        label="Repetitive Note Clusters"
        value={summary.repetitive_notes_clusters}
        subtext={`${summary.repetitive_notes_tickets} tickets affected`}
        color="warning"
        icon={
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
          </svg>
        }
      />

      {/* Blind Spots */}
      <MetricCard
        label="Telemetry Blind Spots"
        value={summary.blind_spots_count}
        subtext="Silent critical assets"
        color="purple"
        icon={
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>
          </svg>
        }
      />

      {/* Risk Score */}
      <MetricCard
        label="Overall Risk Score"
        value={`${summary.overall_risk_score}/100`}
        subtext={
          summary.overall_risk_score > 70 ? "CRITICAL — Immediate review required" :
          summary.overall_risk_score > 40 ? "HIGH — Supervisor attention needed" :
          "Moderate — Routine audit"
        }
        color={
          summary.overall_risk_score > 70 ? "danger" :
          summary.overall_risk_score > 40 ? "warning" : "success"
        }
        icon={
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
        }
      />
    </div>
  );
}
