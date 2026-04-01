export default function AlertFeed({ alerts }) {
  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Alert Feed</h2>
      <div style={{ display: "grid", gap: "10px", maxHeight: "280px", overflow: "auto" }}>
        {alerts.map((alert, index) => (
          <div
            key={`${alert.timestamp || "alert"}-${index}`}
            style={{
              padding: "12px 14px",
              borderRadius: "14px",
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(148,163,184,0.14)",
            }}
          >
            <div style={{ fontWeight: 700 }}>{alert.alert || "INFO"}</div>
            <div style={{ color: "#cbd5e1", fontSize: "14px" }}>{alert.timestamp || "—"}</div>
            <div style={{ marginTop: "4px" }}>Prediction: {alert.prediction ?? "—"}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
