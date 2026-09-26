"use client";

import React, { useMemo } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

interface FindingsTrendProps {
  anomalies?: Record<string, any>[];
  trend?: Record<string, any>[];
}

export function FindingsTrend({ anomalies = [], trend = [] }: FindingsTrendProps) {
  const data = useMemo(() => {
    // 1. If backend summary provided pre-computed trend data, plot directly
    if (trend && trend.length > 0) {
      return trend
        .filter(item => item && (item.date || item.shortDate))
        .map(item => {
          const dateStr = String(item.date || item.shortDate || "");
          return {
            date: dateStr,
            shortDate: String(item.shortDate || (dateStr.length >= 10 ? dateStr.slice(5) : dateStr)),
            findings: Number(item.findings ?? item.count ?? 1),
          };
        })
        .sort((a, b) => a.date.localeCompare(b.date))
        .slice(-15);
    }

    // 2. Otherwise dynamically group anomalies by timestamp
    if (!anomalies || !anomalies.length) return [];

    const grouped = anomalies.reduce<Record<string, number>>((acc, item) => {
      const rawDate = item.timestamp || item.investigation_started || item.date || "";
      const date = String(rawDate).slice(0, 10);
      if (date && date !== "None" && date !== "null" && date !== "undefined") {
        acc[date] = (acc[date] || 0) + 1;
      }
      return acc;
    }, {});

    return Object.entries(grouped)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-15)
      .map(([date, count]) => ({
        date,
        shortDate: date.length >= 10 ? date.slice(5) : date,
        findings: count,
      }));
  }, [anomalies, trend]);

  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-44 text-slate-400 text-sm text-center px-4">
        No temporal data available. Ensure your dataset includes a 'timestamp' or 'date' column to view trend analysis.
      </div>
    );
  }

  return (
    <div className="w-full pt-1" style={{ height: 236 }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 12, right: 12, left: -20, bottom: 4 }}
        >
          <defs>
            <linearGradient id="findingsTrendGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2563EB" stopOpacity={0.18} />
              <stop offset="95%" stopColor="#2563EB" stopOpacity={0.0} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#d8e8e1"
            vertical={false}
          />

          <XAxis
            dataKey="shortDate"
            tick={{ fontSize: 11, fill: "#475569" }}
            axisLine={{ stroke: "#bfe5d6" }}
            tickLine={false}
          />

          <YAxis
            tick={{ fontSize: 11, fill: "#475569" }}
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
          />

          <Tooltip
            isAnimationActive={false}
            cursor={{
              stroke: "#2563EB",
              strokeWidth: 1.5,
              strokeDasharray: "3 3",
            }}
            content={({ active, payload }) => {
              if (!active || !payload || !payload.length) return null;
              const point = payload[0].payload;
              return (
                <div className="bg-slate-900 text-slate-100 px-3 py-2 rounded-lg text-xs shadow-xl border border-slate-700/60 pointer-events-none whitespace-nowrap">
                  <div className="text-slate-400 text-[11px] font-medium mb-1">
                    {point.date}
                  </div>
                  <div className="flex items-center gap-1.5 font-semibold text-white">
                    <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />
                    <span>{point.findings}</span>
                    <span className="text-slate-300 font-normal">
                      finding{point.findings !== 1 ? "s" : ""}
                    </span>
                  </div>
                </div>
              );
            }}
          />

          <Area
            type="monotone"
            dataKey="findings"
            stroke="#2563EB"
            strokeWidth={2.5}
            fillOpacity={1}
            fill="url(#findingsTrendGradient)"
            dot={{ r: 3.5, fill: "#2563EB", stroke: "#FFFFFF", strokeWidth: 1.5 }}
            activeDot={{
              r: 6,
              fill: "#2563EB",
              stroke: "#FFFFFF",
              strokeWidth: 2,
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export default FindingsTrend;
