import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { BoltIcon } from "@heroicons/react/24/outline";

import AlertFeed from "./components/AlertFeed.jsx";
import DecisionPanel from "./components/DecisionPanel.jsx";
import FleetStatus from "./components/FleetStatus.jsx";
import MachineHero from "./components/MachineHero.jsx";
import TrendChart from "./components/TrendChart.jsx";
import WearGauge from "./components/WearGauge.jsx";
import useWebSocket from "./hooks/useWebSocket.js";

const apiBase = `http://${window.location.hostname || "localhost"}:8000`;

const shellStyle = {
  minHeight: "100vh",
  background:
    "radial-gradient(circle at top left, rgba(253, 186, 116, 0.2), transparent 30%), linear-gradient(135deg, #0f172a 0%, #111827 40%, #172554 100%)",
  color: "#e5e7eb",
  fontFamily: '"IBM Plex Sans", "Avenir Next", sans-serif',
  padding: "24px",
};

const gridStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
  gap: "18px",
};

const cardStyle = {
  background: "rgba(15, 23, 42, 0.78)",
  border: "1px solid rgba(148, 163, 184, 0.18)",
  borderRadius: "20px",
  padding: "18px",
  boxShadow: "0 18px 40px rgba(15, 23, 42, 0.35)",
  backdropFilter: "blur(16px)",
};

const fallbackState = {
  features: {
    rms: 0.031,
    high_low_ratio: 0.29,
    temperature: 42.6,
    kurtosis: 4.2,
    spectral_centroid: 4380,
  },
  prediction: {
    median_remaining_strokes: 38,
    confidence_band: [22, 54],
    failure_probability: 0.46,
    confidence_pct: 80,
  },
  decision: {
    optimal_action: "REPLACE_NOW",
    all_costs: {
      REPLACE_NOW: 66000,
      COMPLETE_JOB_THEN_REPLACE: 81200,
      RUN_TO_FAILURE: 86400,
    },
  },
  twin_result: {
    divergence: 2.3,
    alert_level: "WARNING",
  },
};

const fallbackHistory = Array.from({ length: 24 }, (_, index) => ({
  stroke_num: index + 1,
  kurtosis: 2.8 + index * 0.08,
  spectral_centroid: 3050 + index * 58,
  high_low_ratio: 0.05 + index * 0.011,
  alert: index > 18 ? "WATCH" : "INFO",
  prediction: `${Math.max(12, 62 - index)} strokes`,
  timestamp: `T-${24 - index} min`,
}));

const fallbackFleet = [
  { machine_id: "M-01", status: "warning", last_prediction: 38, divergence: 2.3 },
  { machine_id: "M-02", status: "healthy", last_prediction: 96, divergence: 0.8 },
  { machine_id: "M-03", status: "watch", last_prediction: 54, divergence: 1.7 },
];

const fallbackAlerts = [
  {
    alert: "FORGE ALERT",
    timestamp: "Just now",
    prediction: "Replace now to avoid elevated failure risk",
  },
  {
    alert: "WATCH",
    timestamp: "12 min ago",
    prediction: "Twin divergence crossed 1.5 sigma",
  },
];

export default function App() {
  const liveData = useWebSocket(`${apiBase.replace("http", "ws")}/live`);
  const [history, setHistory] = useState(fallbackHistory);
  const [fleet, setFleet] = useState(fallbackFleet);
  const [alerts, setAlerts] = useState(fallbackAlerts);
  const [backendLive, setBackendLive] = useState(false);
  const [state, setState] = useState(fallbackState);

  useEffect(() => {
    axios.get(`${apiBase}/state`).then((response) => {
      setState((previous) => ({ ...previous, ...response.data }));
      setBackendLive(true);
    }).catch(() => undefined);

    axios.get(`${apiBase}/history?hours=2`).then((response) => {
      if (Array.isArray(response.data) && response.data.length > 0) {
        setHistory(response.data);
        setAlerts(response.data.slice(0, 10));
      }
      setBackendLive(true);
    }).catch(() => undefined);

    axios.get(`${apiBase}/fleet`).then((response) => {
      if (Array.isArray(response.data) && response.data.length > 0) {
        setFleet(response.data);
      }
      setBackendLive(true);
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!liveData) {
      return;
    }

    setBackendLive(true);
    setState((previous) => ({
      ...previous,
      features: liveData.feature_vector || previous.features,
      prediction: liveData.prediction || previous.prediction,
      decision: liveData.decision || previous.decision,
      twin_result: liveData.twin_result || previous.twin_result,
    }));
  }, [liveData]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      axios.get(`${apiBase}/history?hours=2`).then((response) => {
        if (Array.isArray(response.data) && response.data.length > 0) {
          setHistory(response.data);
          setAlerts(response.data.slice(0, 10));
        }
      }).catch(() => undefined);

      axios.get(`${apiBase}/fleet`).then((response) => {
        if (Array.isArray(response.data) && response.data.length > 0) {
          setFleet(response.data);
        }
      }).catch(() => undefined);
    }, 10000);

    return () => window.clearInterval(interval);
  }, []);

  const wearPct = useMemo(() => {
    const medianRemaining = state.prediction?.median_remaining_strokes ?? 100;
    return Math.max(0, Math.min(100, 100 - medianRemaining));
  }, [state.prediction]);

  return (
    <div style={shellStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px", gap: "16px", flexWrap: "wrap" }}>
        <div>
          <div style={{ letterSpacing: "0.2em", textTransform: "uppercase", color: "#fdba74", fontSize: "12px" }}>
            FORGE Command View
          </div>
          <h1 style={{ fontSize: "40px", margin: "8px 0 0", fontWeight: 700 }}>Broaching Predictive Dashboard</h1>
        </div>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <div style={{ ...cardStyle, display: "flex", alignItems: "center", gap: "10px", padding: "12px 16px" }}>
            <BoltIcon style={{ width: "20px", color: "#fbbf24" }} />
            <span>Live edge decision stream</span>
          </div>
          <div
            style={{
              ...cardStyle,
              padding: "12px 16px",
              border: backendLive ? "1px solid rgba(34, 197, 94, 0.35)" : "1px solid rgba(245, 158, 11, 0.35)",
              background: backendLive ? "rgba(34, 197, 94, 0.14)" : "rgba(245, 158, 11, 0.14)",
            }}
          >
            {backendLive ? "Backend live data connected" : "Demo fallback mode active"}
          </div>
        </div>
      </div>

      <div style={{ marginBottom: "18px" }}>
        <MachineHero
          features={state.features}
          twinResult={state.twin_result}
          prediction={state.prediction}
          wearPct={wearPct}
        />
      </div>

      <div style={gridStyle}>
        <div style={cardStyle}>
          <WearGauge wearPct={wearPct} alertLevel={state.twin_result?.alert_level || "NORMAL"} />
        </div>
        <div style={cardStyle}>
          <DecisionPanel decision={state.decision} prediction={state.prediction} />
        </div>
      </div>

      <div style={{ ...gridStyle, marginTop: "18px" }}>
        <div style={cardStyle}>
          <TrendChart history={history} />
        </div>
        <div style={cardStyle}>
          <FleetStatus fleet={fleet} />
        </div>
      </div>

      <div style={{ ...cardStyle, marginTop: "18px" }}>
        <AlertFeed alerts={alerts} />
      </div>
    </div>
  );
}
