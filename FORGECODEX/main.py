import argparse
import asyncio
import math
import queue
import threading
import time
from pathlib import Path

import numpy as np

from config import (
    ALERT_COOLDOWN_STROKES,
    ALERT_FAILURE_PROB_THRESHOLD,
    DEFAULT_JOB_STROKES_REMAINING,
    DEMO_MODE,
    ENROLLMENT_RMS_REFERENCE,
    ERROR_SLEEP_SEC,
    IDLE_SLEEP_SEC,
    MACHINE_ID,
    SUPERVISOR_PHONE,
    TFT_MODEL_PATH,
    TOOL_ID,
)
from forge.alerts.whatsapp import WhatsAppAlerter
from forge.api.app import broadcast_state as api_broadcast_state
from forge.api.app import run_app as run_api_app
from forge.biometrics.tool_fingerprint import ToolBiometrics
from forge.db.audit_log import AuditLog
from forge.decision.evii_engine import EVIIDecisionEngine
from forge.llm.maintenance_assistant import FORGEMaintenanceAI
from forge.physics.taylor_engine import TaylorPhysicsEngine
from forge.prediction.tft_predictor import FORGEPredictor
from forge.processing.features import FeatureExtractor
from forge.sensors.capture import SensorCapture
from forge.trust.operator_trust_layer import OperatorTrustLayer
from forge.trust.threshold_updater import AdaptiveThresholdUpdater


class FORGEOrchestrator:
    def __init__(self, demo: bool = DEMO_MODE) -> None:
        self.demo = demo
        self.stroke_count = 0
        self.last_alert_stroke = -ALERT_COOLDOWN_STROKES
        self.job_strokes = DEFAULT_JOB_STROKES_REMAINING
        self.audit_log = AuditLog()
        self.sensor_capture = SensorCapture()
        self.sensor_capture.demo_mode = self.demo or self.sensor_capture.demo_mode
        if self.sensor_capture.demo_mode and self.sensor_capture.demo_audio is None:
            self.sensor_capture._load_demo_audio()
        self.feature_extractor = FeatureExtractor()
        self.physics_engine = TaylorPhysicsEngine(mode="live")
        self.biometrics = ToolBiometrics(TOOL_ID, self.physics_engine)
        checkpoint_path = Path(TFT_MODEL_PATH)
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"TFT checkpoint not found at {TFT_MODEL_PATH}")
        self.predictor = FORGEPredictor(TFT_MODEL_PATH)
        self.decision_engine = EVIIDecisionEngine()
        self.threshold_updater = AdaptiveThresholdUpdater(self.audit_log)
        self.trust_layer = OperatorTrustLayer(
            db=self.audit_log,
            tool_id=TOOL_ID,
            threshold_updater=self.threshold_updater,
        )
        self.alerter = WhatsAppAlerter()
        self.maintenance_ai = FORGEMaintenanceAI(MACHINE_ID, self.audit_log)
        self._api_thread = threading.Thread(target=run_api_app, daemon=True)
        self._api_started = False
        self.data_queue = queue.Queue(maxsize=10)
        self._shutdown_event = threading.Event()

    def start_services(self) -> None:
        if not self._api_started:
            self._api_thread.start()
            self._api_started = True
        self._send_startup_message()

    def capture_worker(self) -> None:
        while not self._shutdown_event.is_set():
            try:
                audio_chunk = self.sensor_capture.capture_chunk()
                vibration = self.sensor_capture.read_vibration()
                temperature = self.sensor_capture.read_temperature()
            except Exception:
                time.sleep(ERROR_SLEEP_SEC)
                continue

            try:
                cutting = self.sensor_capture.is_cutting(audio_chunk)
            except Exception:
                cutting = False
            if not cutting:
                time.sleep(IDLE_SLEEP_SEC)
                continue

            try:
                self.data_queue.put((audio_chunk, vibration, temperature), timeout=1.0)
            except queue.Full:
                pass

    def run(self, max_iterations: int | None = None) -> None:
        self.start_services()
        capture_thread = threading.Thread(target=self.capture_worker, daemon=True)
        capture_thread.start()
        iterations = 0
        while not self._shutdown_event.is_set():
            if max_iterations is not None and iterations >= max_iterations:
                self._shutdown_event.set()
                break
            
            try:
                audio_chunk, vibration, temperature = self.data_queue.get(timeout=1.0)
            except queue.Empty:
                continue
                
            iterations += 1
            self.stroke_count += 1

            if self.stroke_count <= 20:
                enrollment_result = self.biometrics.enroll_stroke(audio_chunk)
                if enrollment_result == "enrolled" and self.biometrics.identity_vector is not None:
                    calibration_factor = (
                        float(np.mean(self.biometrics.enrollment_rms_values)) / ENROLLMENT_RMS_REFERENCE
                        if self.biometrics.enrollment_rms_values
                        else 1.0
                    )
                    self.audit_log.log_tool_enrollment(
                        TOOL_ID,
                        MACHINE_ID,
                        calibration_factor,
                        self.biometrics.identity_vector.tolist(),
                    )
                if self.stroke_count < 20:
                    continue

            try:
                features = self.feature_extractor.extract(audio_chunk, vibration)
            except Exception:
                time.sleep(ERROR_SLEEP_SEC)
                continue

            if any(not math.isfinite(value) for value in features.values()):
                time.sleep(ERROR_SLEEP_SEC)
                continue

            try:
                features["biometric_wear"] = self.biometrics.measure_wear_distance(audio_chunk)
            except Exception:
                features["biometric_wear"] = 0.0

            try:
                twin_result = self.physics_engine.compare_to_reality(features, self.stroke_count)
                features["twin_divergence"] = float(twin_result.get("divergence", 0.0))
            except Exception:
                twin_result = {"divergence": 0.0, "alert": False, "alert_level": "NORMAL"}
                features["twin_divergence"] = 0.0

            feature_vector = dict(features)
            feature_vector["stroke_num"] = self.stroke_count
            feature_vector["tool_id"] = TOOL_ID
            feature_vector["stroke"] = self.stroke_count
            feature_vector["cutting_speed"] = self.physics_engine.cutting_speed
            feature_vector["remaining_life"] = max(0.0, self.physics_engine.expected_tool_life - self.stroke_count)

            prediction = None
            try:
                prediction = self.predictor.predict(feature_vector)
            except Exception:
                prediction = None

            decision = None
            if prediction is not None:
                try:
                    decision = self.decision_engine.compute(prediction, self.job_strokes)
                except Exception:
                    decision = {
                        "optimal_action": "MONITOR",
                        "action_message": "Continue monitoring.",
                        "saving_vs_worst": 0.0,
                        "all_costs": {},
                        "failure_probability_pct": 0.0,
                    }

            self.audit_log.log_sensor(MACHINE_ID, TOOL_ID, self.stroke_count, features, vibration, temperature)
            if prediction is not None:
                self.audit_log.log_prediction(
                    MACHINE_ID,
                    TOOL_ID,
                    self.stroke_count,
                    prediction,
                    float(features["twin_divergence"]),
                )

            if prediction is not None and decision is not None:
                should_alert = False
                if float(prediction.get("failure_probability", 0.0)) > self.threshold_updater.current_threshold:
                    if (self.stroke_count - self.last_alert_stroke) > ALERT_COOLDOWN_STROKES or twin_result.get("alert_level") == "CRITICAL":
                        should_alert = True
                
                if should_alert:
                    feature_history_df = self.feature_extractor.to_dataframe_row(features, self.stroke_count, TOOL_ID)
                    message, alert_id = self.trust_layer.compose_alert(
                        MACHINE_ID,
                        prediction,
                        decision,
                        twin_result,
                        feature_history_df,
                    )
                    if SUPERVISOR_PHONE:
                        self.alerter.send(SUPERVISOR_PHONE, message)
                    self.last_alert_stroke = self.stroke_count
                else:
                    alert_id = None
            else:
                alert_id = None

            forge_state = {
                "machine_id": MACHINE_ID,
                "tool_id": TOOL_ID,
                "features": features,
                "prediction": prediction,
                "decision": decision,
                "twin_result": twin_result,
                "alert_id": alert_id,
                "stroke_count": self.stroke_count,
            }
            try:
                api_broadcast_state(forge_state)
            except Exception:
                pass

            try:
                self.sensor_capture.blink_led(True)
            except Exception:
                pass

    def _send_startup_message(self) -> None:
        if SUPERVISOR_PHONE:
            self.alerter.send(SUPERVISOR_PHONE, f"FORGE online — Machine {MACHINE_ID}. Monitoring started.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--iterations", type=int, default=60)
    args = parser.parse_args()
    orchestrator = FORGEOrchestrator(demo=args.demo or DEMO_MODE)
    orchestrator.run(max_iterations=args.iterations if (args.demo or DEMO_MODE) else None)


if __name__ == "__main__":
    main()
