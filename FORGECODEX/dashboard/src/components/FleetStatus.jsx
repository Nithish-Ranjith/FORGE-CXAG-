import React from "react";
export default function FleetStatus({ fleet }) {
  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Fleet Status</h2>
      <div style={{ display: "grid", gap: "12px" }}>
        {fleet.map((machine) => (
          <div
            key={machine.machine_id}
            style={{
              borderRadius: "16px",
              padding: "14px",
              border: "1px solid rgba(148,163,184,0.18)",
              background: "rgba(255,255,255,0.04)",
            }}
          >
            <div style={{ fontWeight: 700 }}>{machine.machine_id}</div>
            <div>Status: {machine.status}</div>
            <div>Remaining: {machine.last_prediction ?? "—"} strokes</div>
            <div>Divergence: {(machine.divergence ?? 0).toFixed(1)} sigma</div>
          </div>
        ))}
      </div>
    </div>
  );
}
