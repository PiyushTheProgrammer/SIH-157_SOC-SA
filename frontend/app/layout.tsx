import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SAT-SA | SOC Supervisory Analytics Tool",
  description:
    "Air-gapped anomaly detection dashboard for NCIIPC SOC supervisors. " +
    "Detect execution gaps, repetitive operator behaviour, and telemetry blind spots.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        {/* ── Top navigation bar ── */}
        <header
          style={{
            background: "var(--bg-surface)",
            borderBottom: "1px solid var(--border)",
            padding: "0 32px",
            height: 56,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            position: "sticky",
            top: 0,
            zIndex: 40,
          }}
        >
          {/* Brand */}
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {/* Shield icon (inline SVG — no external resource) */}
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--accent)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <polyline points="9 12 11 14 15 10" />
            </svg>
            <div>
              <span
                style={{
                  fontWeight: 700,
                  fontSize: 15,
                  color: "var(--text-primary)",
                  letterSpacing: "-0.02em",
                }}
              >
                SAT-SA
              </span>
              <span
                style={{
                  marginLeft: 8,
                  fontSize: 11,
                  color: "var(--text-muted)",
                  fontWeight: 500,
                  letterSpacing: "0.06em",
                  textTransform: "uppercase",
                }}
              >
                SOC Supervisory Analytics
              </span>
            </div>
          </div>

          {/* Classification banner */}
          <div
            style={{
              background: "var(--danger-dim)",
              border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: 6,
              padding: "3px 12px",
              fontSize: 11,
              fontWeight: 700,
              color: "var(--danger)",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Restricted — Air-Gapped
          </div>

          {/* Right cluster */}
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <span
              style={{
                fontSize: 12,
                color: "var(--text-muted)",
              }}
            >
              NCIIPC SOC Audit Console
            </span>
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: "var(--success)",
                boxShadow: "0 0 8px var(--success)",
              }}
              title="System Online"
            />
          </div>
        </header>

        {/* ── Main content ── */}
        <main
          style={{
            minHeight: "calc(100vh - 56px)",
            background: "var(--bg-base)",
          }}
        >
          {children}
        </main>
      </body>
    </html>
  );
}
