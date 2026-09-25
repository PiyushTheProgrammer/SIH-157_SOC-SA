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
}

export function FindingsTrend({ anomalies = [] }: FindingsTrendProps) {
  const data = useMemo(() => {
    if (!anomalies || !anomalies.length) return [];

    const grouped = anomalies.reduce<Record<string, number>>((acc, item) => {
      const rawDate = item.timestamp || item.investigation_started || "";
      const date = String(rawDate).slice(0, 10);
      if (date) {
        acc[date] = (acc[date] || 0) + 1;
      }
      return acc;
    }, {});

    return Object.entries(grouped)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-10)
      .map(([date, count]) => ({
        date,
        shortDate: date.length >= 10 ? date.slice(5) : date,
        findings: count,
      }));
  }, [anomalies]);

  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-44 text-slate-400 text-sm">
        No findings trend data available
      </div>
    );
  }

  return (
    <div className="w-full h-44 pt-2">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 10, right: 12, left: -22, bottom: 4 }}
        >
          <defs>
            <linearGradient id="findingsTrendGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2563EB" stopOpacity={0.22} />
              <stop offset="95%" stopColor="#2563EB" stopOpacity={0.0} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#F1F5F9"
            vertical={false}
          />

          <XAxis
            dataKey="shortDate"
            tick={{ fontSize: 11, fill: "#64748B" }}
            axisLine={{ stroke: "#E2E8F0" }}
            tickLine={false}
          />

          <YAxis
            tick={{ fontSize: 11, fill: "#64748B" }}
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
