export default function WearGauge({ wearPct, alertLevel }) {
  const bounded = Math.max(0, Math.min(100, wearPct ?? 0));
  const strokeColor = bounded < 50 ? "#22c55e" : bounded < 75 ? "#f59e0b" : "#ef4444";
  const dashOffset = 339.292 - (339.292 * bounded) / 100;

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Wear Gauge</h2>
      <svg viewBox="0 0 160 160" style={{ width: "100%", maxWidth: "260px", display: "block", margin: "0 auto" }}>
        <circle cx="80" cy="80" r="54" stroke="rgba(255,255,255,0.12)" strokeWidth="12" fill="none" />
        <circle
          cx="80"
          cy="80"
          r="54"
          stroke={strokeColor}
          strokeWidth="12"
          fill="none"
          strokeLinecap="round"
          strokeDasharray="339.292"
          strokeDashoffset={dashOffset}
          transform="rotate(-90 80 80)"
        />
        <text x="80" y="74" textAnchor="middle" fill="#f8fafc" fontSize="34" fontWeight="700">
          {bounded.toFixed(0)}%
        </text>
        <text x="80" y="98" textAnchor="middle" fill="#94a3b8" fontSize="14">
          Tool wear
        </text>
      </svg>
      <div style={{ marginTop: "12px", padding: "10px 14px", borderRadius: "999px", background: "rgba(255,255,255,0.08)", display: "inline-block" }}>
        Alert Level: <strong>{alertLevel}</strong>
      </div>
    </div>
  );
}
