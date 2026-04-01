const labels = {
  REPLACE_NOW: "Replace Now",
  COMPLETE_JOB_THEN_REPLACE: "Complete Job",
  RUN_TO_FAILURE: "Run to Failure",
};

export default function DecisionPanel({ decision, prediction }) {
  const costs = decision?.all_costs || {};
  const optimal = decision?.optimal_action;

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Decision Panel</h2>
      <div style={{ display: "grid", gap: "10px" }}>
        {Object.entries(labels).map(([key, label]) => (
          <div
            key={key}
            style={{
              padding: "14px",
              borderRadius: "16px",
              border: optimal === key ? "1px solid #38bdf8" : "1px solid rgba(148,163,184,0.18)",
              background: optimal === key ? "rgba(14, 165, 233, 0.16)" : "rgba(255,255,255,0.04)",
            }}
          >
            <div style={{ fontWeight: 700 }}>{label}</div>
            <div style={{ color: "#cbd5e1", marginTop: "6px" }}>
              Rs. {(costs[key] ?? 0).toLocaleString()}
            </div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: "14px", color: "#fcd34d" }}>
        Failure Probability: <strong>{((prediction?.failure_probability ?? 0) * 100).toFixed(0)}%</strong>
      </div>
    </div>
  );
}
