"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  ScatterChart, Scatter, XAxis, YAxis, Tooltip,
  PieChart, Pie, Cell, ResponsiveContainer, Line, ComposedChart,
} from "recharts";
import {
  apiFetch, apiPost,
  type HealthResponse, type Incident, type IncidentState, type MemoryStats,
} from "@/lib/api";

// ── colours ──────────────────────────────────────────────────────────────────

const C = {
  bg:       "#0D1117",
  surface:  "#161B22",
  low:      "#141c24",
  mid:      "#182028",
  high:     "#222b33",
  border:   "#21262D",
  borderSoft:"#414752",
  text:     "#dae3ee",
  muted:    "#c0c7d4",
  faint:    "#8b919d",
  primary:  "#a2c9ff",
  bright:   "#58a6ff",
  secondary:"#d8baff",
  tertiary: "#ffba42",
  success:  "#4ade80",
  error:    "#ffb4ab",
  errorOn:  "#690005",
};

const SEV_STYLE: Record<string, React.CSSProperties> = {
  P1: { background: C.error, color: C.errorOn },
  P2: { border: `1px solid ${C.tertiary}`, color: C.tertiary },
  P3: { border: `1px solid #da9600`, color: "#da9600" },
  P4: { border: `1px solid ${C.faint}`, color: C.faint },
};

const CAT_COLORS = ["#ffb4ab","#a2c9ff","#ffba42","#d8baff","#4ade80","#8b919d"];
const SVC_COLORS = ["#ffb4ab","#ffba42","#a2c9ff","#d8baff","#4ade80"];

const STEPS = [
  "ingesting","triaging","recalling","investigating",
  "planning","awaiting_approval","executing","verifying",
  "writing_postmortem","complete",
];
const STEP_LABELS = ["INGEST","TRIAGE","RECALL","INVEST","PLAN","APPROVE","EXEC","VERIFY","PM","DONE"];

const STATUS_COLORS: Record<string, string> = {
  complete: "#4ade80",
  escalated: "#ffb4ab",
  investigating: "#a2c9ff",
  recalling: "#a2c9ff",
  awaiting_approval: "#ffba42",
  executing: "#ffba42",
  planning: "#ffba42",
  triaging: "#c0c7d4",
  verifying: "#c0c7d4",
  writing_postmortem: "#4ade80",
};

const TIER_ICON: Record<string, string> = {
  READ: "👁",
  REVERSIBLE: "🔄",
  DESTRUCTIVE: "💥",
};

// ── helpers ───────────────────────────────────────────────────────────────────

function SevBadge({ sev }: { sev: string }) {
  const s = SEV_STYLE[sev] || {};
  return (
    <span style={{
      ...s, padding: "1px 8px", borderRadius: 4,
      fontSize: 11, fontWeight: 600, fontFamily: "JetBrains Mono, monospace",
    }}>
      {sev}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || C.muted;
  const label = status.replace(/_/g, " ").toUpperCase();
  const pulse = ["awaiting_approval","executing","investigating","triaging","recalling"].includes(status);
  return (
    <span className={pulse ? "blink" : ""} style={{ color, fontSize: 11, fontFamily: "JetBrains Mono, monospace" }}>
      {label}
    </span>
  );
}

function mttrOf(inc: Incident) {
  if (!inc.resolved_at || !inc.created_at) return null;
  return ((new Date(inc.resolved_at).getTime() - new Date(inc.created_at).getTime()) / 60000).toFixed(1);
}

function computeTrend(pts: { x: number; y: number }[]) {
  const n = pts.length;
  if (n < 2) return [] as { x: number; trend: number }[];
  const sx = pts.reduce((s, p) => s + p.x, 0);
  const sy = pts.reduce((s, p) => s + p.y, 0);
  const sxy = pts.reduce((s, p) => s + p.x * p.y, 0);
  const sxx = pts.reduce((s, p) => s + p.x * p.x, 0);
  const slope = (n * sxy - sx * sy) / (n * sxx - sx * sx);
  const intercept = (sy - slope * sx) / n;
  return pts.map(p => ({ x: p.x, trend: slope * p.x + intercept }));
}

// ── Stepper ───────────────────────────────────────────────────────────────────

function Stepper({ status }: { status: string }) {
  const cur = STEPS.indexOf(status);
  return (
    <div style={{ display: "flex", alignItems: "center", width: "100%", overflowX: "auto", paddingBottom: 6 }}>
      {STEPS.map((step, i) => {
        const done = i < cur || status === "complete";
        const active = i === cur && status !== "complete";
        return (
          <div key={step} style={{ display: "contents" }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3, flexShrink: 0, minWidth: 34 }}>
              <div className={`stepper-node${done ? " done" : active ? " active" : ""}`} />
              <span style={{
                fontSize: 8, fontFamily: "JetBrains Mono, monospace",
                color: done ? C.success : active ? C.tertiary : C.faint,
                textAlign: "center", lineHeight: "11px",
              }}>
                {STEP_LABELS[i]}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`stepper-line${done ? " done" : ""}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Detail Panel ──────────────────────────────────────────────────────────────

function DetailPanel({
  incidentId, onClose, onApprove,
}: {
  incidentId: string | null;
  onClose: () => void;
  onApprove: (id: string, approved: boolean) => void;
}) {
  const [state, setState] = useState<IncidentState | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!incidentId) { setState(null); return; }
    let alive = true;
    async function load() {
      setLoading(true);
      const s = await apiFetch<IncidentState>(`/api/incidents/${incidentId}`);
      if (alive) { setState(s); setLoading(false); }
    }
    load();
    const t = setInterval(load, 4000);
    return () => { alive = false; clearInterval(t); };
  }, [incidentId]);

  if (!incidentId) {
    return (
      <div className="panel" style={{ padding: 24, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 10, opacity: 0.4 }}>
        <span style={{ fontSize: 36 }}>←</span>
        <span style={{ fontSize: 12, color: C.muted }}>Click an incident to inspect</span>
      </div>
    );
  }

  if (loading && !state) {
    return (
      <div className="panel" style={{ display: "flex", alignItems: "center", justifyContent: "center", color: C.muted, fontSize: 13 }}>
        Loading…
      </div>
    );
  }

  if (!state) {
    return (
      <div className="panel" style={{ padding: 20, color: C.muted, fontSize: 13 }}>
        Initializing… (may take up to 30s for first run)
      </div>
    );
  }

  const conf = state.root_cause_confidence || 0;
  const plan = state.action_plan || [];
  const idx = state.current_action_index || 0;
  const awaitingApproval = state.workflow_status === "awaiting_approval";

  return (
    <div className="panel" style={{ padding: 18, display: "flex", flexDirection: "column", gap: 14, overflowY: "auto" }}>
      {/* header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <SevBadge sev={state.severity} />
            <span style={{ fontSize: 10, color: C.muted, fontFamily: "JetBrains Mono, monospace" }}>
              {state.incident_id.slice(0, 20)}…
            </span>
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, color: C.text, lineHeight: "20px" }}>
            {(state.incident_summary || "Incident").slice(0, 65)}
          </div>
        </div>
        <button onClick={onClose} style={{ background: "none", border: "none", color: C.faint, cursor: "pointer", fontSize: 16, lineHeight: 1, padding: 2 }}>✕</button>
      </div>

      {/* confidence bar */}
      {state.root_cause && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 5 }}>
            <span style={{ color: C.muted }}>Root-cause confidence</span>
            <span style={{ color: C.primary }}>{(conf * 100).toFixed(0)}%</span>
          </div>
          <div style={{ background: C.border, height: 4, borderRadius: 4, overflow: "hidden" }}>
            <div style={{ background: C.bright, height: "100%", width: `${(conf * 100).toFixed(0)}%`, borderRadius: 4 }} />
          </div>
          <div style={{ marginTop: 5, fontSize: 11, color: C.muted, lineHeight: "15px" }}>
            {state.root_cause.slice(0, 110)}
          </div>
        </div>
      )}

      {/* pipeline */}
      <div>
        <div style={{ fontSize: 10, color: C.muted, marginBottom: 6, fontFamily: "JetBrains Mono, monospace", letterSpacing: "0.06em" }}>PIPELINE</div>
        <Stepper status={state.workflow_status} />
      </div>

      {/* action plan */}
      <div style={{ flexGrow: 1, overflowY: "auto" }}>
        <div style={{ fontSize: 10, color: C.muted, marginBottom: 6, fontFamily: "JetBrains Mono, monospace", letterSpacing: "0.06em" }}>ACTION PLAN</div>
        {plan.length === 0 ? (
          <div style={{ color: C.muted, fontSize: 12 }}>No actions planned yet.</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            {plan.map((a, i) => {
              let dot = "⬜"; let textColor = C.muted;
              let bg = C.low; let borderColor = C.border;
              if (a.approved === true)         { dot = "✅"; textColor = C.success; }
              else if (a.approved === false)    { dot = "❌"; textColor = C.error; }
              else if (i < idx)                 { dot = "✅"; textColor = C.success; }
              else if (i === idx && awaitingApproval) {
                dot = "⏳"; textColor = C.tertiary;
                bg = "rgba(255,186,66,0.07)"; borderColor = C.tertiary;
              }
              return (
                <div key={i} style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "6px 10px", borderRadius: 4,
                  background: bg, border: `1px solid ${borderColor}`, fontSize: 11,
                }}>
                  <span>{dot}</span>
                  <span style={{ fontFamily: "JetBrains Mono, monospace", color: textColor, flexGrow: 1, fontSize: 10 }}>{a.tool_name}</span>
                  <span title={a.classification}>{TIER_ICON[a.classification] || "❓"}</span>
                </div>
              );
            })}
          </div>
        )}

        {awaitingApproval && (
          <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
            <button
              onClick={() => onApprove(state.incident_id, true)}
              style={{
                flex: 1, padding: "8px 0", borderRadius: 4, cursor: "pointer",
                background: "rgba(74,222,128,0.1)", border: `1px solid ${C.success}`,
                color: C.success, fontSize: 12, fontWeight: 600,
              }}
            >
              ✓ APPROVE
            </button>
            <button
              onClick={() => onApprove(state.incident_id, false)}
              style={{
                flex: 1, padding: "8px 0", borderRadius: 4, cursor: "pointer",
                background: "rgba(255,180,171,0.1)", border: `1px solid ${C.error}`,
                color: C.error, fontSize: 12, fontWeight: 600,
              }}
            >
              ✕ REJECT
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Stat Card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, subColor, accent }: {
  label: string; value: string | number; sub: string; subColor: string; accent?: string;
}) {
  return (
    <div className="panel" style={{ padding: "14px 16px", display: "flex", flexDirection: "column", justifyContent: "space-between", position: "relative", overflow: "hidden" }}>
      {accent && <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 3, background: accent }} />}
      <div style={{ fontSize: 10, color: C.muted, fontFamily: "JetBrains Mono, monospace", letterSpacing: "0.06em", paddingLeft: accent ? 12 : 0 }}>
        {label.toUpperCase()}
      </div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 10, paddingLeft: accent ? 12 : 0 }}>
        <div style={{ fontSize: 28, fontWeight: 700, color: accent || C.text, lineHeight: "36px" }}>{value}</div>
        <div style={{ fontSize: 11, color: subColor, background: `${subColor}1a`, padding: "2px 8px", borderRadius: 4, marginBottom: 4, whiteSpace: "nowrap" }}>
          {sub}
        </div>
      </div>
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [memStats, setMemStats] = useState<MemoryStats | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [fireStatus, setFireStatus] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdated, setLastUpdated] = useState("");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    const [h, inc, mem] = await Promise.all([
      apiFetch<HealthResponse>("/health"),
      apiFetch<Incident[]>("/api/incidents?limit=30"),
      apiFetch<MemoryStats>("/api/memory/stats"),
    ]);
    if (h) setHealth(h);
    if (inc) setIncidents(inc);
    if (mem) setMemStats(mem);
    setLastUpdated(new Date().toUTCString().split(" ")[4] + " UTC");
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (!autoRefresh) return;
    timerRef.current = setInterval(refresh, 8000);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [autoRefresh, refresh]);

  async function fireIncident() {
    setFireStatus("Firing…");
    const data = await apiPost<{ incident_id: string }>("/webhook/alert", {
      source: "custom", alert_name: "RedisOOM", severity: "P1", service: "payments-api",
      description: "Redis out of memory — OOM command not allowed when used memory > maxmemory. payments-api error rate 45%, p99 latency 8.4s. Restart count: 3.",
      labels: { env: "production", region: "us-east-1", team: "payments" },
    });
    if (data) { setFireStatus(data.incident_id); setSelected(data.incident_id); setTimeout(refresh, 800); }
    else setFireStatus("Error — is the API running on port 8000?");
  }

  async function handleApprove(id: string, approved: boolean) {
    await apiPost(`/api/incidents/${id}/approve?approved=${approved}`);
    setTimeout(refresh, 1200);
  }

  // ── derived stats ─────────────────────────────────────────────────────────

  const active = incidents.filter(i => !["complete","escalated"].includes(i.workflow_status));
  const resolved = incidents.filter(i => i.workflow_status === "complete");
  const p1Active = active.filter(i => i.severity === "P1");
  const total = incidents.length;
  const resolvedPct = total > 0 ? Math.round((resolved.length / total) * 100) : 0;

  const series = (memStats?.mttr_series || []).sort((a, b) =>
    new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );
  const avgMttr = series.length > 0
    ? (series.reduce((s, x) => s + x.mttr, 0) / series.length).toFixed(1)
    : null;

  let mttrDelta: string | null = null;
  let mttrGood = true;
  if (series.length >= 4) {
    const half = Math.floor(series.length / 2);
    const first = series.slice(0, half).reduce((s, x) => s + x.mttr, 0) / half;
    const last = series.slice(-half).reduce((s, x) => s + x.mttr, 0) / half;
    const pct = first > 0 ? ((first - last) / first * 100) : 0;
    mttrGood = pct >= 0;
    mttrDelta = `${Math.abs(pct).toFixed(0)}% ${pct >= 0 ? "faster" : "slower"} vs first half`;
  }

  // ── chart data ────────────────────────────────────────────────────────────

  const scatterData = series.map((p, i) => ({ x: i + 1, y: Number(p.mttr.toFixed(2)) }));
  const trendPts = computeTrend(scatterData);
  const combinedData = scatterData.map((pt, i) => ({ ...pt, trend: trendPts[i]?.trend }));

  const catEntries = Object.entries(memStats?.categories || {}).sort((a, b) => b[1] - a[1]);
  const donutData = catEntries.map(([name, value], i) => ({ name, value, fill: CAT_COLORS[i % CAT_COLORS.length] }));
  const svcEntries = Object.entries(memStats?.services || {}).sort((a, b) => b[1] - a[1]).slice(0, 6);
  const maxSvc = Math.max(...svcEntries.map(([, v]) => v), 1);

  // ─────────────────────────────────────────────────────────────────────────

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: C.bg, overflow: "hidden" }}>

      {/* Nav */}
      <nav style={{
        background: C.mid, borderBottom: `1px solid ${C.border}`,
        height: 54, flexShrink: 0, display: "flex", alignItems: "center",
        justifyContent: "space-between", padding: "0 24px",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 18 }}>🚨</span>
          <span style={{ fontSize: 15, fontWeight: 700, color: C.text }}>SIREN</span>
          <span style={{ fontSize: 12, color: C.muted, marginLeft: 4 }}>Self-Improving Incident Response Engine</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 20, fontSize: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, color: health ? C.success : C.error }}>
            <div className={`live-dot${health ? " green" : ""}`} />
            {health ? "API Online" : "API Offline"}
          </div>
          {health && (
            <span style={{ color: C.muted }}>
              🗄 Qdrant: <strong style={{ color: C.secondary }}>{health.qdrant_incidents}</strong>
            </span>
          )}
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "3px 10px", background: C.high, border: `1px solid ${C.borderSoft}`, borderRadius: 20, fontSize: 11,
          }}>
            <div className="live-dot" />
            <span style={{ color: C.error }}>SYSTEM ACTIVE</span>
          </div>
        </div>
      </nav>

      {/* Main */}
      <main style={{ flexGrow: 1, overflow: "auto", padding: "14px 24px", display: "flex", flexDirection: "column", gap: 12 }}>

        {/* Stat cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, flexShrink: 0 }}>
          <StatCard accent={C.error} label="Active Incidents" value={active.length}
            sub={p1Active.length > 0 ? `${p1Active.length} P1 CRITICAL` : active.length > 0 ? "IN PROGRESS" : "ALL CLEAR"}
            subColor={C.error} />
          <StatCard label="Avg MTTR" value={avgMttr !== null ? `${avgMttr} min` : "—"}
            sub={mttrDelta || "Not enough data"} subColor={mttrGood ? C.success : C.error} />
          <StatCard accent={C.secondary} label="Incidents in Memory" value={memStats?.total ?? "—"}
            sub="🗄 Qdrant" subColor={C.secondary} />
          <StatCard label="Resolved" value={`${resolved.length}/${total}`}
            sub={`${resolvedPct}% resolved`} subColor={C.success} />
        </div>

        {/* Incident table + detail */}
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12, flexShrink: 0, height: 356 }}>

          {/* Table */}
          <div className="panel" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <div style={{
              padding: "10px 16px", borderBottom: `1px solid ${C.border}`,
              background: C.low, display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div className="live-dot" />
                <span style={{ fontSize: 14, fontWeight: 600 }}>Live Incidents</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <button onClick={fireIncident} style={{
                  background: C.error, color: C.errorOn, border: "none", cursor: "pointer",
                  padding: "5px 14px", borderRadius: 4, fontSize: 12, fontWeight: 700,
                  boxShadow: `0 2px 12px rgba(255,180,171,0.25)`,
                }}>
                  🔥 Fire Demo
                </button>
                {fireStatus && (
                  <span style={{ fontSize: 11, color: C.muted, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {fireStatus}
                  </span>
                )}
              </div>
            </div>

            <div style={{ overflowY: "auto", flexGrow: 1 }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: C.high, position: "sticky", top: 0, zIndex: 1 }}>
                    {["Sev","Incident ID","Service","Status","Root Cause","MTTR"].map(h => (
                      <th key={h} style={{
                        padding: "7px 12px", textAlign: "left", fontSize: 10, fontWeight: 500,
                        color: C.muted, fontFamily: "JetBrains Mono, monospace", letterSpacing: "0.06em",
                        borderBottom: `1px solid ${C.border}`,
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {incidents.length === 0 ? (
                    <tr>
                      <td colSpan={6} style={{ padding: "24px 12px", textAlign: "center", color: C.muted, fontSize: 13 }}>
                        No incidents yet — click <strong>Fire Demo</strong> to start.
                      </td>
                    </tr>
                  ) : incidents.map(inc => {
                    const isSelected = selected === inc.incident_id;
                    const mttr = mttrOf(inc);
                    return (
                      <tr key={inc.incident_id} onClick={() => setSelected(isSelected ? null : inc.incident_id)}
                        style={{
                          cursor: "pointer",
                          background: isSelected ? C.high : "transparent",
                          borderLeft: isSelected ? `2px solid ${C.bright}` : "2px solid transparent",
                          transition: "background 0.1s",
                        }}
                        onMouseEnter={e => { if (!isSelected) (e.currentTarget as HTMLTableRowElement).style.background = C.mid; }}
                        onMouseLeave={e => { if (!isSelected) (e.currentTarget as HTMLTableRowElement).style.background = "transparent"; }}
                      >
                        <td style={{ padding: "8px 12px" }}><SevBadge sev={inc.severity} /></td>
                        <td style={{ padding: "8px 12px", fontSize: 11, fontFamily: "JetBrains Mono, monospace", color: C.text }}>
                          {inc.incident_id.slice(0, 22)}…
                        </td>
                        <td style={{ padding: "8px 12px", fontSize: 12, color: C.muted }}>{inc.affected_service}</td>
                        <td style={{ padding: "8px 12px" }}><StatusBadge status={inc.workflow_status} /></td>
                        <td style={{ padding: "8px 12px", fontSize: 12, color: C.muted, maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {inc.root_cause?.slice(0, 55) || "—"}
                        </td>
                        <td style={{ padding: "8px 12px", fontSize: 11, fontFamily: "JetBrains Mono, monospace", color: mttr ? C.text : C.faint }}>
                          {mttr ? `${mttr}m` : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Detail */}
          <DetailPanel incidentId={selected} onClose={() => setSelected(null)} onApprove={handleApprove} />
        </div>

        {/* Charts row */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, flexGrow: 1, minHeight: 240 }}>

          {/* MTTR scatter */}
          <div className="panel" style={{ padding: 16, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <span style={{ fontSize: 10, color: C.muted, fontFamily: "JetBrains Mono, monospace", letterSpacing: "0.06em" }}>
                MTTR SELF-IMPROVEMENT — QDRANT MEMORY EFFECT
              </span>
              {mttrDelta && mttrGood && (
                <span style={{ background: C.high, border: `1px solid ${C.border}`, padding: "2px 10px", borderRadius: 4, fontSize: 11, color: C.success }}>
                  📉 {mttrDelta}
                </span>
              )}
            </div>
            <div style={{ flexGrow: 1, minHeight: 0 }}>
              {combinedData.length === 0 ? (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: C.muted, fontSize: 12 }}>
                  No data — run <code style={{ background: C.high, padding: "1px 6px", borderRadius: 3, margin: "0 4px" }}>python scripts/seed_qdrant.py</code>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={combinedData} margin={{ top: 4, right: 10, bottom: 20, left: 0 }}>
                    <XAxis dataKey="x" type="number" name="Incident #" tick={{ fill: C.faint, fontSize: 10 }}
                      label={{ value: "Incident #", position: "insideBottom", offset: -8, fill: C.faint, fontSize: 10 }} />
                    <YAxis tick={{ fill: C.faint, fontSize: 10 }}
                      label={{ value: "MTTR (min)", angle: -90, position: "insideLeft", offset: 8, fill: C.faint, fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 11 }}
                      formatter={(val: unknown, name: unknown) => [`${(val as number).toFixed(2)} min`, name === "y" ? "MTTR" : "Trend"]} />
                    <Scatter dataKey="y" fill={C.primary} opacity={0.85} />
                    <Line dataKey="trend" dot={false} stroke={C.success} strokeWidth={1.5} strokeDasharray="5 3" />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Memory breakdown */}
          <div className="panel" style={{ padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>
            <span style={{ fontSize: 10, color: C.muted, fontFamily: "JetBrains Mono, monospace", letterSpacing: "0.06em" }}>
              INCIDENT MEMORY (QDRANT) — {memStats?.total ?? 0} TOTAL
            </span>
            {(memStats?.total ?? 0) === 0 ? (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flexGrow: 1, color: C.muted, fontSize: 12 }}>
                Empty — run <code style={{ background: C.high, padding: "1px 6px", borderRadius: 3, margin: "0 4px" }}>python scripts/seed_qdrant.py</code>
              </div>
            ) : (
              <div style={{ display: "flex", gap: 16, flexGrow: 1, alignItems: "center", minHeight: 0 }}>
                {/* Donut */}
                <div style={{ width: "46%", position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <ResponsiveContainer width="100%" height={180}>
                    <PieChart>
                      <Pie data={donutData} cx="50%" cy="50%" innerRadius="60%" outerRadius="85%" dataKey="value" paddingAngle={2}>
                        {donutData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                      </Pie>
                      <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 11 }} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div style={{ position: "absolute", textAlign: "center", pointerEvents: "none" }}>
                    <div style={{ fontSize: 22, fontWeight: 700, color: C.text }}>{memStats?.total}</div>
                    <div style={{ fontSize: 10, color: C.faint }}>Total</div>
                  </div>
                </div>

                {/* Service bars */}
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 9, justifyContent: "center" }}>
                  {svcEntries.map(([svc, cnt], i) => (
                    <div key={svc}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 3 }}>
                        <span style={{ color: C.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 110 }}>{svc}</span>
                        <span style={{ color: C.faint, marginLeft: 6 }}>{cnt}</span>
                      </div>
                      <div style={{ background: C.border, height: 4, borderRadius: 3, overflow: "hidden" }}>
                        <div style={{ background: SVC_COLORS[i % SVC_COLORS.length], height: "100%", width: `${(cnt / maxSvc * 100).toFixed(0)}%`, borderRadius: 3 }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div style={{ borderTop: `1px solid ${C.border}`, paddingTop: 8, display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: C.muted, cursor: "pointer" }}>
            <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} style={{ accentColor: C.bright }} />
            Auto-refresh every 8s
          </label>
          <span style={{ fontSize: 11, color: C.faint, fontFamily: "JetBrains Mono, monospace" }}>
            {lastUpdated || "—"}
          </span>
        </div>
      </main>
    </div>
  );
}
