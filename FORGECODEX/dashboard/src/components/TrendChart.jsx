import React from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function normalize(history, key) {
  const values = history.map((entry) => entry[key] ?? 0);
  const max = Math.max(...values, 1);
  return history.map((entry) => ({
    ...entry,
    [key]: (entry[key] ?? 0) / max,
  }));
}

export default function TrendChart({ history }) {
  const withSignals = normalize(
    history.map((entry, index) => ({
      stroke_num: entry.stroke_num ?? index,
      kurtosis: entry.kurtosis ?? 0,
      spectral_centroid: entry.spectral_centroid ?? 0,
      high_low_ratio: entry.high_low_ratio ?? 0,
    })),
    "spectral_centroid",
  );

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Trend Chart</h2>
      <div style={{ height: "280px" }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={withSignals}>
            <XAxis dataKey="stroke_num" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip />
            <Line type="monotone" dataKey="kurtosis" stroke="#60a5fa" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="spectral_centroid" stroke="#fb923c" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="high_low_ratio" stroke="#f43f5e" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
