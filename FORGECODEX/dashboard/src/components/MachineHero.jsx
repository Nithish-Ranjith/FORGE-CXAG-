import { useEffect, useMemo, useState } from "react";

const stageLabels = ["Sensing", "Features", "Digital Twin", "TFT", "Decision", "Alert"];

function metricTone(value, warn, critical) {
  if (value >= critical) {
    return "#fb7185";
  }
  if (value >= warn) {
    return "#f59e0b";
  }
  return "#22d3ee";
}

function SignalMetric({ label, value, unit, color }) {
  return (
    <div
      style={{
        padding: "12px 14px",
        borderRadius: "16px",
        background: "rgba(15, 23, 42, 0.75)",
        border: `1px solid ${color}55`,
        boxShadow: `0 0 28px ${color}18`,
      }}
    >
      <div style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.16em", color: "#94a3b8" }}>
        {label}
      </div>
      <div style={{ marginTop: "6px", fontSize: "24px", fontWeight: 700, color }}>{value}</div>
      <div style={{ color: "#94a3b8", fontSize: "13px" }}>{unit}</div>
    </div>
  );
}

export default function MachineHero({ features, twinResult, prediction, wearPct }) {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setPhase((value) => (value + 1) % 240);
    }, 40);
    return () => window.clearInterval(timer);
  }, []);

  const boundedWear = Math.max(0, Math.min(100, wearPct ?? 0));
  const alertLevel = twinResult?.alert_level || "NORMAL";
  const alertColor = alertLevel === "CRITICAL" ? "#fb7185" : alertLevel === "WARNING" ? "#f59e0b" : "#22d3ee";
  const carriageOffset = 46 + Math.sin(phase / 10) * 7;
  const pulse = 0.55 + ((Math.sin(phase / 8) + 1) / 2) * 0.45;
  const acoustic = Number(features?.rms ?? 0).toFixed(3);
  const vibration = Number(features?.high_low_ratio ?? 0).toFixed(3);
  const temperature = Number(features?.temperature ?? 25).toFixed(1);
  const divergence = Number(twinResult?.divergence ?? 0).toFixed(2);
  const remaining = Number(prediction?.median_remaining_strokes ?? 0).toFixed(0);

  const machineGlow = useMemo(() => {
    if (boundedWear >= 75) {
      return "rgba(251, 113, 133, 0.28)";
    }
    if (boundedWear >= 50) {
      return "rgba(245, 158, 11, 0.24)";
    }
    return "rgba(34, 211, 238, 0.22)";
  }, [boundedWear]);

  return (
    <div
      style={{
        position: "relative",
        overflow: "hidden",
        borderRadius: "28px",
        padding: "24px",
        background:
          "radial-gradient(circle at top left, rgba(34, 211, 238, 0.12), transparent 24%), radial-gradient(circle at top right, rgba(59, 130, 246, 0.2), transparent 30%), linear-gradient(180deg, rgba(2, 6, 23, 0.96) 0%, rgba(15, 23, 42, 0.96) 100%)",
        border: "1px solid rgba(56, 189, 248, 0.16)",
        boxShadow: "0 30px 60px rgba(2, 6, 23, 0.55)",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(148, 163, 184, 0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(148, 163, 184, 0.06) 1px, transparent 1px)",
          backgroundSize: "36px 36px",
          maskImage: "linear-gradient(180deg, rgba(0,0,0,0.7), transparent)",
          pointerEvents: "none",
        }}
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.7fr) minmax(320px, 1fr)",
          gap: "22px",
          alignItems: "stretch",
        }}
      >
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", gap: "16px", alignItems: "flex-start" }}>
            <div>
              <div style={{ color: "#67e8f9", letterSpacing: "0.18em", textTransform: "uppercase", fontSize: "12px" }}>
                Live Machine View
              </div>
              <h2 style={{ margin: "10px 0 6px", fontSize: "34px", lineHeight: 1.05 }}>Broaching Cell Digital Twin</h2>
              <p style={{ margin: 0, color: "#94a3b8", maxWidth: "560px" }}>
                Real-time wireframe machine motion feeding acoustic, vibration, and thermal signals into FORGE&apos;s prediction stack.
              </p>
            </div>
            <div
              style={{
                padding: "10px 14px",
                borderRadius: "999px",
                color: "#e2e8f0",
                border: `1px solid ${alertColor}77`,
                background: `${alertColor}18`,
                whiteSpace: "nowrap",
              }}
            >
              {alertLevel} MODE
            </div>
          </div>

          <div style={{ marginTop: "18px", display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "12px" }}>
            <SignalMetric label="Acoustic RMS" value={acoustic} unit="normalized" color={metricTone(Number(features?.rms ?? 0), 0.03, 0.045)} />
            <SignalMetric label="Vibration Ratio" value={vibration} unit="high / low band" color={metricTone(Number(features?.high_low_ratio ?? 0), 0.25, 0.5)} />
            <SignalMetric label="Temperature" value={temperature} unit="°C" color={metricTone(Number(features?.temperature ?? 25), 40, 55)} />
          </div>

          <div
            style={{
              marginTop: "18px",
              borderRadius: "24px",
              padding: "18px",
              background: "linear-gradient(180deg, rgba(15, 23, 42, 0.86), rgba(2, 6, 23, 0.94))",
              border: "1px solid rgba(56, 189, 248, 0.12)",
              position: "relative",
              boxShadow: `inset 0 0 40px ${machineGlow}`,
            }}
          >
            <svg viewBox="0 0 760 360" style={{ width: "100%", display: "block" }}>
              <defs>
                <filter id="wireGlow">
                  <feGaussianBlur stdDeviation="2.2" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
                <linearGradient id="energyBeam" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.1" />
                  <stop offset="50%" stopColor={alertColor} stopOpacity="0.88" />
                  <stop offset="100%" stopColor="#60a5fa" stopOpacity="0.08" />
                </linearGradient>
              </defs>

              <rect x="44" y="244" width="670" height="54" rx="8" stroke="#475569" strokeWidth="2" fill="none" opacity="0.7" />
              <rect x="70" y="218" width="120" height="24" rx="3" stroke="#38bdf8" strokeWidth="2" fill="none" filter="url(#wireGlow)" />
              <rect x="132" y="118" width="34" height="104" rx="4" stroke="#38bdf8" strokeWidth="2" fill="none" filter="url(#wireGlow)" />
              <rect x="258" y="108" width="144" height="76" rx="6" stroke="#60a5fa" strokeWidth="2" fill="none" filter="url(#wireGlow)" />
              <rect x="420" y="116" width="134" height="68" rx="6" stroke="#22d3ee" strokeWidth="2" fill="none" filter="url(#wireGlow)" />
              <rect x="578" y="102" width="68" height="140" rx="6" stroke="#38bdf8" strokeWidth="2" fill="none" filter="url(#wireGlow)" />

              <line x1="166" y1="170" x2="258" y2="146" stroke="#67e8f9" strokeWidth="2" strokeDasharray="8 8" opacity="0.7" />
              <line x1="402" y1="146" x2="420" y2="146" stroke="#67e8f9" strokeWidth="2" />
              <line x1="554" y1="148" x2="578" y2="148" stroke="#67e8f9" strokeWidth="2" />

              <rect
                x={290 + Math.sin(phase / 14) * 8}
                y={carriageOffset}
                width="84"
                height="34"
                rx="4"
                stroke={alertColor}
                strokeWidth="2.4"
                fill="none"
                filter="url(#wireGlow)"
              />
              <line
                x1={332 + Math.sin(phase / 14) * 8}
                y1={carriageOffset + 34}
                x2={332 + Math.sin(phase / 14) * 8}
                y2={210}
                stroke={alertColor}
                strokeWidth="3"
                filter="url(#wireGlow)"
              />
              <rect x="468" y="192" width="78" height="26" rx="4" stroke="#f97316" strokeWidth="2" fill="none" filter="url(#wireGlow)" />
              <line x1="332" y1="210" x2="468" y2="205" stroke="url(#energyBeam)" strokeWidth="5" strokeLinecap="round" opacity={pulse} />

              <circle cx="132" cy="170" r="10" stroke="#67e8f9" strokeWidth="2" fill="none" filter="url(#wireGlow)" />
              <circle cx="508" cy="205" r="10" stroke="#f97316" strokeWidth="2" fill="none" filter="url(#wireGlow)" />
              <circle cx="612" cy="132" r="10" stroke={alertColor} strokeWidth="2" fill="none" filter="url(#wireGlow)" />
              <line x1="132" y1="180" x2="132" y2="214" stroke="#67e8f9" strokeWidth="2" strokeDasharray="5 5" />
              <line x1="508" y1="215" x2="508" y2="244" stroke="#f97316" strokeWidth="2" strokeDasharray="5 5" />
              <line x1="612" y1="142" x2="612" y2="84" stroke={alertColor} strokeWidth="2" strokeDasharray="5 5" />

              <text x="92" y="80" fill="#67e8f9" fontSize="15">Mic</text>
              <text x="470" y="82" fill="#f97316" fontSize="15">PT100</text>
              <text x="574" y="74" fill={alertColor} fontSize="15">MPU-6050</text>
              <text x="274" y="96" fill="#cbd5e1" fontSize="13">Broach carriage</text>
              <text x="448" y="236" fill="#cbd5e1" fontSize="13">Cutting zone</text>
            </svg>
          </div>
        </div>

        <div style={{ display: "grid", gap: "16px" }}>
          <div
            style={{
              padding: "18px",
              borderRadius: "24px",
              background: "rgba(15, 23, 42, 0.78)",
              border: "1px solid rgba(148, 163, 184, 0.18)",
            }}
          >
            <div style={{ color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.16em", fontSize: "11px" }}>
              Pipeline Status
            </div>
            <div style={{ marginTop: "14px", display: "grid", gap: "10px" }}>
              {stageLabels.map((label, index) => {
                const activeIndex = boundedWear >= 75 ? 5 : boundedWear >= 50 ? 4 : 3;
                const active = index <= activeIndex;
                return (
                  <div key={label} style={{ display: "grid", gridTemplateColumns: "24px 1fr auto", gap: "10px", alignItems: "center" }}>
                    <div
                      style={{
                        width: "14px",
                        height: "14px",
                        borderRadius: "999px",
                        background: active ? alertColor : "rgba(148, 163, 184, 0.22)",
                        boxShadow: active ? `0 0 18px ${alertColor}` : "none",
                      }}
                    />
                    <div style={{ color: active ? "#f8fafc" : "#94a3b8" }}>{label}</div>
                    <div style={{ color: "#94a3b8", fontSize: "13px" }}>{active ? "live" : "standby"}</div>
                  </div>
                );
              })}
            </div>
          </div>

          <div
            style={{
              padding: "18px",
              borderRadius: "24px",
              background: "rgba(15, 23, 42, 0.78)",
              border: "1px solid rgba(148, 163, 184, 0.18)",
              display: "grid",
              gap: "14px",
            }}
          >
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div>
                <div style={{ color: "#94a3b8", fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.16em" }}>Wear State</div>
                <div style={{ marginTop: "8px", fontSize: "38px", fontWeight: 700, color: alertColor }}>{boundedWear.toFixed(0)}%</div>
              </div>
              <div>
                <div style={{ color: "#94a3b8", fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.16em" }}>Remaining Life</div>
                <div style={{ marginTop: "8px", fontSize: "38px", fontWeight: 700 }}>{remaining}</div>
              </div>
            </div>
            <div
              style={{
                height: "10px",
                borderRadius: "999px",
                background: "rgba(148, 163, 184, 0.12)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${boundedWear}%`,
                  height: "100%",
                  background: `linear-gradient(90deg, #22d3ee 0%, ${alertColor} 100%)`,
                  boxShadow: `0 0 20px ${alertColor}`,
                }}
              />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", color: "#cbd5e1" }}>
              <div>
                <div style={{ color: "#94a3b8", fontSize: "12px" }}>Twin divergence</div>
                <div style={{ marginTop: "6px", fontSize: "22px", fontWeight: 700 }}>{divergence} sigma</div>
              </div>
              <div>
                <div style={{ color: "#94a3b8", fontSize: "12px" }}>Failure risk</div>
                <div style={{ marginTop: "6px", fontSize: "22px", fontWeight: 700 }}>
                  {((prediction?.failure_probability ?? 0) * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
