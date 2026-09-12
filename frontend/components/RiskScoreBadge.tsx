"use client";

import React from "react";

interface Props {
  score: number; // 0–100
  size?: number;
}

export default function RiskScoreBadge({ score, size = 80 }: Props) {
  // SVG circle parameters
  const r = (size / 2) * 0.8;
  const circumference = 2 * Math.PI * r;
  const progress = Math.min(Math.max(score, 0), 100) / 100;
  const strokeDashoffset = circumference * (1 - progress);

  const color =
    score > 70 ? "var(--danger)" :
    score > 40 ? "var(--warning)" :
    "var(--success)";

  const label =
    score > 70 ? "CRITICAL" :
    score > 40 ? "HIGH" :
    "MODERATE";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 6,
      }}
    >
      <div className="risk-ring" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="var(--border)"
            strokeWidth={6}
          />
          {/* Progress */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={6}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
            style={{ transition: "stroke-dashoffset 0.8s ease, stroke 0.4s ease" }}
          />
        </svg>

        {/* Score in centre */}
        <div
          style={{
            position: "absolute",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            lineHeight: 1,
          }}
        >
          <span
            style={{
              fontSize: size * 0.22,
              fontWeight: 800,
              color,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {score}
          </span>
          <span style={{ fontSize: size * 0.1, color: "var(--text-muted)", fontWeight: 600 }}>
            /100
          </span>
        </div>
      </div>

      {/* Label */}
      <span
        style={{
          fontSize: 10,
          fontWeight: 700,
          color,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
        }}
      >
        {label}
      </span>
    </div>
  );
}
