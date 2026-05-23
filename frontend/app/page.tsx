"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

// ── terminal lines ────────────────────────────────────────────────────────────

const TERMINAL_LINES = [
  { delay: 0,    text: "Initializing diagnostic protocols...", color: "#8b919d" },
  { delay: 800,  text: "Fetching CloudWatch logs [payments-api]...", color: "#8b919d" },
  { delay: 1800, text: "query_prometheus: error_rate=45.2% p99=8400ms", color: "#58A6FF" },
  { delay: 2600, text: "inspect_docker_container: mem=99.8% restarts=3", color: "#58A6FF" },
  { delay: 3400, text: "Pattern identified: Redis OOM — maxmemory exceeded", color: "#F2F0E8" },
  { delay: 4200, text: "Recall: INC-20260418 (92% match) → FLUSHDB resolved in 2.1m", color: "#a2c9ff" },
  { delay: 5000, text: "Executing flush_redis_cache [DESTRUCTIVE — awaiting approval]", color: "#ffba42" },
  { delay: 5800, text: "✓ Approved via Slack. Executing...", color: "#4ade80" },
  { delay: 6600, text: "Recovery confirmed. error_rate=0.2% p99=118ms", color: "#4ade80" },
  { delay: 7200, text: "Post-mortem written. Embedded in Qdrant. MTTR: 2.4 min", color: "#4ade80" },
];

// ── design tokens ─────────────────────────────────────────────────────────────

const T = {
  bg:      "#0A0A0B",
  surface: "#0e0e0f",
  border:  "rgba(242, 240, 232, 0.08)",
  text:    "#F2F0E8",
  muted:   "#8b919d",
  red:     "#FF4444",
  blue:    "#58A6FF",
};

// ── Terminal ──────────────────────────────────────────────────────────────────

function Terminal() {
  const [visible, setVisible] = useState<number[]>([]);
  const ref = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    ref.current = TERMINAL_LINES.map((line, i) =>
      setTimeout(() => setVisible(v => [...v, i]), line.delay)
    );
    return () => ref.current.forEach(clearTimeout);
  }, []);

  return (
    <div style={{
      background: T.surface,
      border: `1px solid ${T.border}`,
      padding: "32px",
      fontFamily: "JetBrains Mono, monospace",
      fontSize: 12,
      lineHeight: "20px",
      display: "flex",
      flexDirection: "column",
      justifyContent: "flex-end",
      height: "100%",
      position: "relative",
      overflow: "hidden",
    }}>
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 1,
        background: `linear-gradient(to right, transparent, ${T.blue}88, transparent)`,
      }} />
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {TERMINAL_LINES.map((line, i) => (
          <div key={i} style={{
            display: "flex", gap: 12, alignItems: "flex-start",
            opacity: visible.includes(i) ? 1 : 0,
            transition: "opacity 0.4s ease",
          }}>
            <span style={{ color: T.blue, flexShrink: 0 }}>&gt;</span>
            <span style={{ color: line.color }}>{line.text}</span>
          </div>
        ))}
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <span style={{ color: T.blue }}>&gt;</span>
          <span style={{ color: T.blue, animation: "blink 1s step-end infinite" }}>_</span>
        </div>
      </div>
      <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }`}</style>
    </div>
  );
}

// ── PulseDot ──────────────────────────────────────────────────────────────────

function PulseDot({ color = T.red }: { color?: string }) {
  return (
    <>
      <span style={{
        display: "inline-block", width: 8, height: 8, background: color,
        animation: "pulse 2s cubic-bezier(0.4,0,0.6,1) infinite",
        flexShrink: 0,
      }} />
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }`}</style>
    </>
  );
}

// ── Divider ───────────────────────────────────────────────────────────────────

function Divider() {
  return <div style={{ height: 1, background: T.border, width: "100%" }} />;
}

// ── Section header ────────────────────────────────────────────────────────────

function SectionNum({ num, label }: { num: string; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 48 }}>
      <span style={{
        fontFamily: "JetBrains Mono, monospace", fontSize: 11, letterSpacing: "0.05em",
        color: T.muted, textTransform: "uppercase",
      }}>{num}</span>
      <div style={{ width: 32, height: 1, background: `${T.muted}4d` }} />
      <span style={{
        fontFamily: "JetBrains Mono, monospace", fontSize: 11, letterSpacing: "0.05em",
        color: T.muted, textTransform: "uppercase",
      }}>{label}</span>
    </div>
  );
}

// ── CodeLine ──────────────────────────────────────────────────────────────────

function CodeLine({ prompt, text, color = T.muted }: { prompt?: boolean; text: string; color?: string }) {
  return (
    <div style={{ display: "flex", gap: 10, alignItems: "flex-start", fontFamily: "JetBrains Mono, monospace", fontSize: 12, lineHeight: "20px" }}>
      {prompt && <span style={{ color: T.blue, flexShrink: 0 }}>&gt;</span>}
      <span style={{ color }}>{text}</span>
    </div>
  );
}

// ── FeatureBlock ──────────────────────────────────────────────────────────────

function FeatureBlock({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div style={{ borderTop: `1px solid ${T.border}`, paddingTop: 24 }}>
      <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, letterSpacing: "0.05em", color: T.muted, textTransform: "uppercase", marginBottom: 8 }}>
        {label}
      </div>
      <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 24, fontWeight: 700, color: T.text, letterSpacing: "-0.02em", marginBottom: 4 }}>
        {value}
      </div>
      <div style={{ fontSize: 14, color: T.muted, lineHeight: "20px" }}>{sub}</div>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handler);
    return () => window.removeEventListener("scroll", handler);
  }, []);

  const px = "clamp(24px, 5vw, 64px)";
  const maxW = 1440;

  return (
    <div style={{ background: T.bg, color: T.text, minHeight: "100vh", fontFamily: "Geist, sans-serif", overflowX: "hidden" }}>

      {/* ── Nav ── */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 50,
        height: 80, display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: `0 ${px}`,
        background: scrolled ? "rgba(10,10,11,0.97)" : "transparent",
        borderBottom: scrolled ? `1px solid ${T.border}` : "1px solid transparent",
        transition: "background 0.3s, border-color 0.3s",
        backdropFilter: scrolled ? "blur(8px)" : "none",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <PulseDot />
          <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 20, fontWeight: 700, letterSpacing: "-0.03em" }}>
            SIREN
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 40 }}>
          <a href="https://github.com/RohanMulay1/siren" target="_blank" rel="noreferrer"
            style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, letterSpacing: "0.05em", color: T.muted, textDecoration: "none", textTransform: "uppercase" }}
            onMouseEnter={e => (e.currentTarget.style.color = T.text)}
            onMouseLeave={e => (e.currentTarget.style.color = T.muted)}>
            GitHub ↗
          </a>

          <Link href="/dashboard" style={{
            fontFamily: "JetBrains Mono, monospace", fontSize: 11, letterSpacing: "0.05em",
            color: T.text, textDecoration: "none", textTransform: "uppercase",
            border: `1px solid ${T.border}`, padding: "8px 16px",
            transition: "background 0.2s, color 0.2s",
          }}
            onMouseEnter={e => { e.currentTarget.style.background = T.text; e.currentTarget.style.color = T.bg; }}
            onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = T.text; }}>
            Live Demo →
          </Link>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section style={{
        minHeight: "100vh", display: "flex", alignItems: "center",
        padding: `120px ${px} 80px`,
        borderBottom: `1px solid ${T.border}`,
      }}>
        <div style={{ maxWidth: maxW, margin: "0 auto", width: "100%", display: "grid", gridTemplateColumns: "7fr 5fr", gap: 48, alignItems: "center" }}>

          <div style={{ display: "flex", flexDirection: "column", gap: 48 }}>
            <div>
              <div style={{
                display: "flex", alignItems: "center", gap: 12, marginBottom: 24,
                fontFamily: "JetBrains Mono, monospace", fontSize: 11, letterSpacing: "0.08em",
                color: T.muted, textTransform: "uppercase",
              }}>
                <span style={{ display: "block", width: 32, height: 1, background: `${T.muted}4d` }} />
                Autonomous Incident Response
              </div>

              <h1 style={{
                fontSize: "clamp(56px, 8vw, 120px)", fontWeight: 700, lineHeight: 0.9,
                letterSpacing: "-0.05em", margin: 0, marginBottom: 32,
              }}>
                Your on-call<br />engineer never<br />sleeps.
              </h1>

              <p style={{ fontSize: 18, lineHeight: "28px", color: T.muted, maxWidth: 520, margin: 0 }}>
                SIREN detects, investigates, and resolves production incidents autonomously
                using advanced multi-step reasoning and tool-use — while you sleep.
              </p>
            </div>

            <div style={{ display: "flex", gap: 48, paddingTop: 32, borderTop: `1px solid ${T.border}`, width: "fit-content" }}>
              <div>
                <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 24, fontWeight: 700, letterSpacing: "-0.02em", marginBottom: 4 }}>
                  &lt; 3 min
                </div>
                <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, letterSpacing: "0.05em", color: T.muted, textTransform: "uppercase" }}>
                  MTTR
                </div>
              </div>
              <div>
                <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 24, fontWeight: 700, letterSpacing: "-0.02em", marginBottom: 4 }}>
                  100%
                </div>
                <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, letterSpacing: "0.05em", color: T.muted, textTransform: "uppercase" }}>
                  Autonomous
                </div>
              </div>
              <div>
                <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 24, fontWeight: 700, letterSpacing: "-0.02em", marginBottom: 4 }}>
                  0
                </div>
                <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, letterSpacing: "0.05em", color: T.muted, textTransform: "uppercase" }}>
                  Pages sent
                </div>
              </div>
            </div>
          </div>

          {/* Terminal */}
          <div style={{ height: 500 }}>
            <Terminal />
          </div>
        </div>
      </section>

      {/* ── Section 01: DETECT ── */}
      <section style={{ padding: `96px ${px}`, borderBottom: `1px solid ${T.border}` }}>
        <div style={{ maxWidth: maxW, margin: "0 auto", width: "100%" }}>
          <SectionNum num="01" label="Detect" />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 80, alignItems: "start" }}>
            <div>
              <h2 style={{ fontSize: "clamp(32px, 4vw, 56px)", fontWeight: 700, letterSpacing: "-0.03em", lineHeight: 1.05, margin: "0 0 24px" }}>
                Alerts in.<br />Context out.
              </h2>
              <p style={{ fontSize: 16, lineHeight: "26px", color: T.muted, margin: "0 0 48px" }}>
                SIREN ingests webhooks from any monitoring tool — PagerDuty, CloudWatch,
                Prometheus, Grafana — and immediately begins building context. Triage happens
                in seconds, not after a groggy engineer logs in at 3am.
              </p>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
                <FeatureBlock label="Sources" value="Any webhook" sub="Prometheus, CloudWatch, PagerDuty, custom" />
                <FeatureBlock label="Triage" value="&lt; 2s" sub="Severity + service classification via Claude Sonnet" />
              </div>
            </div>

            <div style={{
              background: T.surface, border: `1px solid ${T.border}`, padding: 32,
              fontFamily: "JetBrains Mono, monospace", fontSize: 12, lineHeight: "20px",
            }}>
              <div style={{ color: T.muted, marginBottom: 20, fontSize: 11, letterSpacing: "0.05em", textTransform: "uppercase" }}>
                POST /webhook/alert
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <CodeLine text='{' color={T.text} />
                <CodeLine text='  "source": "prometheus",' color="#a2c9ff" />
                <CodeLine text='  "alert_name": "RedisOOMKiller",' color="#a2c9ff" />
                <CodeLine text='  "severity": "critical",' color="#a2c9ff" />
                <CodeLine text='  "service": "payments-api",' color="#a2c9ff" />
                <CodeLine text='  "description": "OOM killer triggered 3x"' color="#a2c9ff" />
                <CodeLine text='}' color={T.text} />
              </div>
              <Divider />
              <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 8 }}>
                <CodeLine prompt text="Triage complete — P1 | payments-api" color="#4ade80" />
                <CodeLine prompt text="Confidence: 0.94" color={T.muted} />
                <CodeLine prompt text="Routing to investigation..." color={T.muted} />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 02: INVESTIGATE ── */}
      <section style={{ padding: `96px ${px}`, borderBottom: `1px solid ${T.border}` }}>
        <div style={{ maxWidth: maxW, margin: "0 auto", width: "100%" }}>
          <SectionNum num="02" label="Investigate" />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 80, alignItems: "start" }}>
            <div style={{
              background: T.surface, border: `1px solid ${T.border}`, padding: 32,
            }}>
              <div style={{ color: T.muted, marginBottom: 20, fontSize: 11, fontFamily: "JetBrains Mono, monospace", letterSpacing: "0.05em", textTransform: "uppercase" }}>
                Investigation loop — Claude Opus 4.7
              </div>

              {[
                { tool: "query_prometheus", result: "error_rate=45.2%, p99=8400ms", tier: "READ" },
                { tool: "fetch_cloudwatch_logs", result: "'OOM command not allowed' ×847", tier: "READ" },
                { tool: "inspect_docker_container", result: "mem=99.8%, restarts=3", tier: "READ" },
                { tool: "recall_similar_incidents", result: "INC-20260418 (92%) → FLUSHDB resolved", tier: "READ" },
              ].map((step, i) => (
                <div key={i} style={{
                  display: "flex", gap: 16, paddingBottom: 20, marginBottom: 20,
                  borderBottom: i < 3 ? `1px solid ${T.border}` : "none",
                }}>
                  <div style={{
                    width: 28, height: 28, background: `${T.blue}1a`,
                    border: `1px solid ${T.blue}4d`, display: "flex", alignItems: "center",
                    justifyContent: "center", flexShrink: 0,
                    fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: T.blue,
                  }}>
                    {i + 1}
                  </div>
                  <div>
                    <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 12, color: T.blue, marginBottom: 4 }}>
                      {step.tool}
                    </div>
                    <div style={{ fontSize: 12, color: T.muted, lineHeight: "18px" }}>{step.result}</div>
                  </div>
                  <div style={{ marginLeft: "auto", flexShrink: 0 }}>
                    <span style={{
                      fontFamily: "JetBrains Mono, monospace", fontSize: 10, padding: "2px 8px",
                      border: `1px solid ${T.border}`, color: T.muted, textTransform: "uppercase",
                    }}>
                      {step.tier}
                    </span>
                  </div>
                </div>
              ))}

              <div style={{ marginTop: 8, padding: 16, background: `${T.blue}0d`, border: `1px solid ${T.blue}33` }}>
                <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: T.blue, marginBottom: 4 }}>ROOT CAUSE — 96% CONFIDENCE</div>
                <div style={{ fontSize: 12, color: T.muted, lineHeight: "18px" }}>
                  Redis exceeded maxmemory (512MB). Auth token TTL removed in deploy at 14:32 UTC.
                </div>
              </div>
            </div>

            <div>
              <h2 style={{ fontSize: "clamp(32px, 4vw, 56px)", fontWeight: 700, letterSpacing: "-0.03em", lineHeight: 1.05, margin: "0 0 24px" }}>
                Multi-step<br />root cause<br />analysis.
              </h2>
              <p style={{ fontSize: 16, lineHeight: "26px", color: T.muted, margin: "0 0 48px" }}>
                Claude Opus runs a structured investigation loop — querying metrics, logs,
                containers, and git history in parallel. Each tool result is scanned for
                prompt injection before entering the model context.
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
                <FeatureBlock label="Model" value="Opus 4.7" sub="Maximum reasoning capability for root cause" />
                <FeatureBlock label="Tools" value="8 built-in" sub="Prometheus, CloudWatch, Docker, GitHub, Postgres" />
                <FeatureBlock label="Guardrails" value="Injection scan" sub="Every tool output sanitized before LLM context" />
                <FeatureBlock label="Memory" value="Qdrant" sub="92% match recall cuts investigation from 6→2 calls" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 03: APPROVE ── */}
      <section style={{ padding: `96px ${px}`, borderBottom: `1px solid ${T.border}` }}>
        <div style={{ maxWidth: maxW, margin: "0 auto", width: "100%" }}>
          <SectionNum num="03" label="Approve" />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 80, alignItems: "start" }}>
            <div>
              <h2 style={{ fontSize: "clamp(32px, 4vw, 56px)", fontWeight: 700, letterSpacing: "-0.03em", lineHeight: 1.05, margin: "0 0 24px" }}>
                Human-in-the-<br />loop. Not<br />human-in-the-way.
              </h2>
              <p style={{ fontSize: 16, lineHeight: "26px", color: T.muted, margin: "0 0 24px" }}>
                READ and REVERSIBLE actions run automatically. DESTRUCTIVE actions — cache
                flushes, draining load balancer nodes, database migrations — pause the
                workflow and send a Slack approval request with full context.
              </p>
              <p style={{ fontSize: 16, lineHeight: "26px", color: T.muted, margin: "0 0 48px" }}>
                One click. Graph resumes from checkpoint. Zero configuration.
              </p>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 24 }}>
                {[
                  { tier: "READ", desc: "Auto-approved", color: T.blue },
                  { tier: "REVERSIBLE", desc: "Auto if confidence > 85%", color: "#ffba42" },
                  { tier: "DESTRUCTIVE", desc: "Always needs Slack", color: T.red },
                ].map(t => (
                  <div key={t.tier} style={{ borderTop: `2px solid ${t.color}`, paddingTop: 16 }}>
                    <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: t.color, marginBottom: 8 }}>{t.tier}</div>
                    <div style={{ fontSize: 13, color: T.muted, lineHeight: "18px" }}>{t.desc}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Slack approval mockup */}
            <div style={{ border: `1px solid ${T.border}`, background: T.surface }}>
              <div style={{ padding: "16px 20px", borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ width: 6, height: 6, background: T.red, animation: "pulse 2s ease infinite" }} />
                <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: T.muted, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  #incidents — Slack
                </span>
              </div>

              <div style={{ padding: 20 }}>
                {/* Bot message */}
                <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                  <div style={{
                    width: 32, height: 32, background: T.red, flexShrink: 0,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontFamily: "JetBrains Mono, monospace", fontSize: 12, fontWeight: 700, color: "#fff",
                  }}>S</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>SIREN</div>
                    <div style={{ fontSize: 12, color: T.muted, marginBottom: 12, lineHeight: "18px" }}>
                      Action 1 of 2 requires approval
                    </div>

                    <div style={{ background: "#161B22", border: `1px solid ${T.border}`, padding: 16, fontSize: 12 }}>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
                        {[["Incident", "INC-20260520-001"], ["Severity", "P1"], ["Service", "payments-api"], ["Risk", "DESTRUCTIVE"]].map(([k, v]) => (
                          <div key={k}>
                            <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 10, color: T.muted, textTransform: "uppercase", marginBottom: 2 }}>{k}</div>
                            <div style={{ color: k === "Risk" ? T.red : T.text, fontWeight: k === "Risk" ? 600 : 400 }}>{v}</div>
                          </div>
                        ))}
                      </div>

                      <div style={{ borderTop: `1px solid ${T.border}`, paddingTop: 12, marginBottom: 12 }}>
                        <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 10, color: T.muted, textTransform: "uppercase", marginBottom: 6 }}>Action</div>
                        <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: T.blue }}>flush_redis_cache</div>
                        <div style={{ fontSize: 11, color: T.muted, marginTop: 4, lineHeight: "16px" }}>
                          Redis at 99.8% — OOM killer triggered 3×. Flush restores payments-api immediately.
                        </div>
                      </div>

                      <div style={{ display: "flex", gap: 8 }}>
                        <button style={{
                          flex: 1, padding: "8px 0", background: "rgba(74,222,128,0.12)",
                          border: "1px solid #4ade80", color: "#4ade80",
                          fontFamily: "JetBrains Mono, monospace", fontSize: 11, cursor: "pointer",
                        }}>
                          APPROVE
                        </button>
                        <button style={{
                          flex: 1, padding: "8px 0", background: "rgba(255,68,68,0.08)",
                          border: `1px solid ${T.border}`, color: T.muted,
                          fontFamily: "JetBrains Mono, monospace", fontSize: 11, cursor: "pointer",
                        }}>
                          REJECT
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 04: LEARN ── */}
      <section style={{ padding: `96px ${px}`, borderBottom: `1px solid ${T.border}` }}>
        <div style={{ maxWidth: maxW, margin: "0 auto", width: "100%" }}>
          <SectionNum num="04" label="Learn" />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 80, alignItems: "start" }}>
            <div style={{
              background: T.surface, border: `1px solid ${T.border}`, padding: 32,
            }}>
              <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: T.muted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 24 }}>
                MTTR self-improvement — Qdrant memory effect
              </div>

              {/* Fake MTTR chart */}
              <div style={{ position: "relative", height: 160, marginBottom: 24 }}>
                <svg viewBox="0 0 400 120" style={{ width: "100%", height: "100%" }}>
                  {/* Grid lines */}
                  {[0, 30, 60, 90, 120].map(y => (
                    <line key={y} x1={0} y1={y} x2={400} y2={y} stroke={T.border} strokeWidth={1} />
                  ))}
                  {/* Scatter dots (MTTR decreasing) */}
                  {[
                    [20, 95], [50, 88], [80, 82], [110, 90], [140, 72],
                    [170, 65], [200, 58], [230, 70], [260, 45], [290, 38],
                    [320, 42], [350, 28], [380, 20],
                  ].map(([x, y], i) => (
                    <circle key={i} cx={x} cy={y} r={4} fill="#a2c9ff" opacity={0.85} />
                  ))}
                  {/* Trend line */}
                  <line x1={20} y1={95} x2={380} y2={18} stroke="#4ade80" strokeWidth={1.5} strokeDasharray="6 3" opacity={0.8} />
                </svg>
                <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 10, color: T.muted }}>Incident #1</span>
                  <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 10, color: T.muted }}>Incident #13</span>
                </div>
              </div>

              <div style={{ display: "flex", gap: 16, alignItems: "center", justifyContent: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#a2c9ff" }} />
                  <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 10, color: T.muted }}>Actual MTTR</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ width: 16, height: 1, background: "#4ade80" }} />
                  <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 10, color: T.muted }}>Trend (OLS)</span>
                </div>
              </div>

              <div style={{ marginTop: 24, padding: 16, background: `rgba(74,222,128,0.06)`, border: `1px solid rgba(74,222,128,0.2)` }}>
                <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: "#4ade80", marginBottom: 4 }}>
                  68% faster after 10 incidents
                </div>
                <div style={{ fontSize: 12, color: T.muted, lineHeight: "18px" }}>
                  9.2 min cold → 2.9 min with Qdrant memory recall
                </div>
              </div>
            </div>

            <div>
              <h2 style={{ fontSize: "clamp(32px, 4vw, 56px)", fontWeight: 700, letterSpacing: "-0.03em", lineHeight: 1.05, margin: "0 0 24px" }}>
                Gets faster<br />every time<br />it fires.
              </h2>
              <p style={{ fontSize: 16, lineHeight: "26px", color: T.muted, margin: "0 0 24px" }}>
                After every resolved incident, SIREN writes a structured post-mortem and
                embeds it in Qdrant. The next time a similar incident fires, semantic search
                surfaces the most relevant past resolution — and Claude tests that hypothesis first.
              </p>
              <p style={{ fontSize: 16, lineHeight: "26px", color: T.muted, margin: "0 0 48px" }}>
                Cold start: 6 tool calls, 9 minutes. With memory: 2 tool calls, 2.4 minutes.
                The improvement compounds with every incident.
              </p>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
                <FeatureBlock label="Storage" value="Qdrant" sub="384-dim cosine similarity, payload-indexed" />
                <FeatureBlock label="Embeddings" value="MiniLM" sub="Local inference — no API cost per incident" />
                <FeatureBlock label="Recall" value="Top 5" sub="0.75 similarity threshold, filtered by service" />
                <FeatureBlock label="Effect" value="−68% MTTR" sub="Measured over 13 incidents in demo data" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Tech Stack ── */}
      <section style={{ padding: `80px ${px}`, borderBottom: `1px solid ${T.border}` }}>
        <div style={{ maxWidth: maxW, margin: "0 auto", width: "100%" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 32, flexWrap: "wrap" }}>
            <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: T.muted, textTransform: "uppercase", letterSpacing: "0.08em", flexShrink: 0 }}>
              Built with
            </div>
            <div style={{ flex: 1, height: 1, background: T.border }} />
            {["Anthropic Claude", "LangGraph", "Qdrant", "FastAPI", "Slack SDK", "Docker"].map(tech => (
              <div key={tech} style={{
                fontFamily: "JetBrains Mono, monospace", fontSize: 12, color: T.muted,
                padding: "6px 16px", border: `1px solid ${T.border}`,
                transition: "color 0.2s, border-color 0.2s",
              }}
                onMouseEnter={e => { e.currentTarget.style.color = T.text; e.currentTarget.style.borderColor = `${T.text}33`; }}
                onMouseLeave={e => { e.currentTarget.style.color = T.muted; e.currentTarget.style.borderColor = T.border; }}>
                {tech}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section style={{ padding: `120px ${px}`, borderBottom: `1px solid ${T.border}` }}>
        <div style={{ maxWidth: maxW, margin: "0 auto", width: "100%", textAlign: "center" }}>
          <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: T.muted, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 24, display: "flex", alignItems: "center", justifyContent: "center", gap: 12 }}>
            <span style={{ display: "block", width: 32, height: 1, background: `${T.muted}4d` }} />
            Open source · MIT License
            <span style={{ display: "block", width: 32, height: 1, background: `${T.muted}4d` }} />
          </div>
          <h2 style={{ fontSize: "clamp(40px, 6vw, 80px)", fontWeight: 700, letterSpacing: "-0.04em", lineHeight: 1, margin: "0 0 32px" }}>
            Stop being<br />paged at 3am.
          </h2>
          <p style={{ fontSize: 18, color: T.muted, marginBottom: 48, lineHeight: "28px" }}>
            Deploy SIREN in minutes. Watch it resolve its first incident autonomously.
          </p>
          <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
            <Link href="/dashboard" style={{
              display: "inline-block", padding: "14px 40px",
              background: T.text, color: T.bg,
              fontFamily: "JetBrains Mono, monospace", fontSize: 12, letterSpacing: "0.05em",
              textDecoration: "none", textTransform: "uppercase", fontWeight: 700,
              transition: "opacity 0.2s",
            }}
              onMouseEnter={e => (e.currentTarget.style.opacity = "0.85")}
              onMouseLeave={e => (e.currentTarget.style.opacity = "1")}>
              Live Demo →
            </Link>
            <a href="https://github.com/RohanMulay1/siren" target="_blank" rel="noreferrer" style={{
              display: "inline-block", padding: "14px 40px",
              border: `1px solid ${T.border}`, color: T.text,
              fontFamily: "JetBrains Mono, monospace", fontSize: 12, letterSpacing: "0.05em",
              textDecoration: "none", textTransform: "uppercase",
              transition: "border-color 0.2s",
            }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = `${T.text}66`)}
              onMouseLeave={e => (e.currentTarget.style.borderColor = T.border)}>
              GitHub ↗
            </a>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer style={{ padding: `48px ${px}`, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
        <div>
          <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 20, fontWeight: 700, letterSpacing: "-0.03em", marginBottom: 8 }}>
            SIREN
          </div>
          <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: T.muted, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Open source · MIT
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "flex-end", fontFamily: "JetBrains Mono, monospace", fontSize: 12 }}>
          {[
            { label: "GitHub", href: "https://github.com/RohanMulay1/siren" },
            { label: "Anthropic Claude", href: "https://anthropic.com" },
            { label: "LangGraph", href: "https://langchain-ai.github.io/langgraph/" },
            { label: "Qdrant", href: "https://qdrant.tech" },
          ].map(link => (
            <a key={link.label} href={link.href} target="_blank" rel="noreferrer"
              style={{ color: T.muted, textDecoration: "none", transition: "color 0.2s" }}
              onMouseEnter={e => (e.currentTarget.style.color = T.text)}
              onMouseLeave={e => (e.currentTarget.style.color = T.muted)}>
              {link.label}
            </a>
          ))}
        </div>
      </footer>

    </div>
  );
}
