import json
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from config import DB_PATH, TOOL_ID


class AuditLog:
    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY,
                machine_id TEXT,
                tool_id TEXT,
                timestamp TEXT,
                stroke_num INTEGER,
                rms REAL,
                kurtosis REAL,
                skewness REAL,
                crest_factor REAL,
                peak_amplitude REAL,
                spectral_centroid REAL,
                spectral_bandwidth REAL,
                low_band_energy REAL,
                mid_band_energy REAL,
                high_band_energy REAL,
                high_low_ratio REAL,
                dominant_freq REAL,
                biometric_wear REAL,
                twin_divergence REAL,
                temperature REAL,
                ax REAL,
                ay REAL,
                az REAL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY,
                machine_id TEXT,
                tool_id TEXT,
                timestamp TEXT,
                stroke_num INTEGER,
                median_remaining INTEGER,
                lower_bound INTEGER,
                upper_bound INTEGER,
                failure_probability REAL,
                divergence REAL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                machine_id TEXT,
                tool_id TEXT,
                timestamp TEXT,
                stroke_num INTEGER,
                alert_level TEXT,
                message TEXT,
                optimal_action TEXT,
                saving_inr REAL,
                sent_to TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS overrides (
                id INTEGER PRIMARY KEY,
                alert_id TEXT,
                machine_id TEXT,
                tool_id TEXT,
                timestamp TEXT,
                reason_code INTEGER,
                reason_text TEXT,
                actual_outcome TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS tool_enrollments (
                id INTEGER PRIMARY KEY,
                tool_id TEXT,
                machine_id TEXT,
                enrolled_at TEXT,
                calibration_factor REAL,
                identity_vector_json TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS alert_threshold_history (
                id INTEGER PRIMARY KEY,
                machine_id TEXT,
                timestamp TEXT,
                old_threshold REAL,
                new_threshold REAL,
                reason TEXT
            )
            """,
        ]
        with self.conn:
            for statement in statements:
                self.conn.execute(statement)
        self._ensure_sensor_readings_columns()

    def _ensure_sensor_readings_columns(self) -> None:
        expected_columns = {
            "skewness": "REAL",
            "peak_amplitude": "REAL",
            "spectral_bandwidth": "REAL",
            "low_band_energy": "REAL",
            "mid_band_energy": "REAL",
            "high_band_energy": "REAL",
            "dominant_freq": "REAL",
        }
        existing_columns = {
            row[1] for row in self.conn.execute("PRAGMA table_info(sensor_readings)").fetchall()
        }
        with self.conn:
            for column_name, column_type in expected_columns.items():
                if column_name not in existing_columns:
                    self.conn.execute(
                        f"ALTER TABLE sensor_readings ADD COLUMN {column_name} {column_type}"
                    )

    def log_sensor(
        self,
        machine_id: str,
        tool_id: str,
        stroke_num: int,
        features: dict[str, Any],
        vibration: dict[str, Any],
        temperature: float,
    ) -> None:
        try:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO sensor_readings (
                        machine_id, tool_id, timestamp, stroke_num, rms, kurtosis,
                        skewness, crest_factor, peak_amplitude, spectral_centroid,
                        spectral_bandwidth, low_band_energy, mid_band_energy,
                        high_band_energy, high_low_ratio, dominant_freq, biometric_wear,
                        twin_divergence, temperature, ax, ay, az
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        machine_id,
                        tool_id,
                        datetime.now().isoformat(),
                        stroke_num,
                        float(features.get("rms", 0.0)),
                        float(features.get("kurtosis", 0.0)),
                        float(features.get("skewness", 0.0)),
                        float(features.get("crest_factor", 0.0)),
                        float(features.get("peak_amplitude", 0.0)),
                        float(features.get("spectral_centroid", 0.0)),
                        float(features.get("spectral_bandwidth", 0.0)),
                        float(features.get("low_band_energy", 0.0)),
                        float(features.get("mid_band_energy", 0.0)),
                        float(features.get("high_band_energy", 0.0)),
                        float(features.get("high_low_ratio", 0.0)),
                        float(features.get("dominant_freq", 0.0)),
                        float(features.get("biometric_wear", 0.0)),
                        float(features.get("twin_divergence", 0.0)),
                        float(temperature),
                        float(vibration.get("ax", 0.0)),
                        float(vibration.get("ay", 0.0)),
                        float(vibration.get("az", 0.0)),
                    ),
                )
        except Exception as exc:
            print(f"AuditLog.log_sensor error: {exc}", file=sys.stderr)

    def log_prediction(
        self,
        machine_id: str,
        tool_id: str,
        stroke_num: int,
        prediction: dict[str, Any],
        divergence: float,
    ) -> None:
        try:
            lower_bound, upper_bound = prediction.get("confidence_band", (0, 0))
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO predictions (
                        machine_id, tool_id, timestamp, stroke_num, median_remaining,
                        lower_bound, upper_bound, failure_probability, divergence
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        machine_id,
                        tool_id,
                        datetime.now().isoformat(),
                        stroke_num,
                        int(prediction.get("median_remaining_strokes", 0)),
                        int(lower_bound),
                        int(upper_bound),
                        float(prediction.get("failure_probability", 0.0)),
                        float(divergence),
                    ),
                )
        except Exception as exc:
            print(f"AuditLog.log_prediction error: {exc}", file=sys.stderr)

    def log_alert(
        self,
        machine_id: str,
        tool_id: str,
        stroke_num: int,
        alert_level: str,
        message: str,
        decision: dict[str, Any],
    ) -> str:
        alert_id = str(uuid.uuid4())
        try:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO alerts (
                        id, machine_id, tool_id, timestamp, stroke_num, alert_level,
                        message, optimal_action, saving_inr, sent_to
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        alert_id,
                        machine_id,
                        tool_id,
                        datetime.now().isoformat(),
                        stroke_num,
                        alert_level,
                        message,
                        decision.get("optimal_action", ""),
                        float(decision.get("saving_vs_worst", 0.0)),
                        decision.get("sent_to"),
                    ),
                )
        except Exception as exc:
            print(f"AuditLog.log_alert error: {exc}", file=sys.stderr)
        return alert_id

    def log_override(self, alert_id: str, machine_id: str, reason_code: int) -> None:
        reason_map = {1: "ToolFine", 2: "Deadline", 3: "Unclear", 4: "Other"}
        try:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO overrides (
                        alert_id, machine_id, tool_id, timestamp, reason_code,
                        reason_text, actual_outcome
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        alert_id,
                        machine_id,
                        TOOL_ID,
                        datetime.now().isoformat(),
                        reason_code,
                        reason_map.get(reason_code, "Other"),
                        None,
                    ),
                )
        except Exception as exc:
            print(f"AuditLog.log_override error: {exc}", file=sys.stderr)

    def log_tool_enrollment(
        self,
        tool_id: str,
        machine_id: str,
        calibration_factor: float,
        identity_vector: list[float],
    ) -> None:
        try:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO tool_enrollments (
                        tool_id, machine_id, enrolled_at, calibration_factor,
                        identity_vector_json
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        tool_id,
                        machine_id,
                        datetime.now().isoformat(),
                        float(calibration_factor),
                        json.dumps(identity_vector),
                    ),
                )
        except Exception as exc:
            print(f"AuditLog.log_tool_enrollment error: {exc}", file=sys.stderr)

    def log_threshold_change(
        self,
        machine_id: str,
        old_threshold: float,
        new_threshold: float,
        reason: str,
    ) -> None:
        try:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO alert_threshold_history (
                        machine_id, timestamp, old_threshold, new_threshold, reason
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        machine_id,
                        datetime.now().isoformat(),
                        float(old_threshold),
                        float(new_threshold),
                        reason,
                    ),
                )
        except Exception as exc:
            print(f"AuditLog.log_threshold_change error: {exc}", file=sys.stderr)

    def find_similar_patterns(self, machine_id: str, kurtosis_val: float) -> list[dict[str, Any]]:
        lower_bound = float(kurtosis_val) * 0.9
        upper_bound = float(kurtosis_val) * 1.1
        query = """
            SELECT
                alerts.id AS alert_id,
                alerts.timestamp,
                alerts.alert_level,
                alerts.optimal_action,
                sensor_readings.kurtosis,
                sensor_readings.rms,
                sensor_readings.spectral_centroid
            FROM alerts
            JOIN sensor_readings
                ON alerts.machine_id = sensor_readings.machine_id
                AND alerts.tool_id = sensor_readings.tool_id
                AND alerts.stroke_num = sensor_readings.stroke_num
            WHERE alerts.machine_id = ?
              AND sensor_readings.kurtosis BETWEEN ? AND ?
            ORDER BY alerts.timestamp DESC
            LIMIT 2
        """
        rows = self.conn.execute(query, (machine_id, lower_bound, upper_bound)).fetchall()
        return [dict(row) for row in rows]

    def get_recent_overrides(self, machine_id: str, days: int = 7) -> list[dict[str, Any]]:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        rows = self.conn.execute(
            """
            SELECT *
            FROM overrides
            WHERE machine_id = ? AND timestamp > ?
            ORDER BY timestamp DESC
            LIMIT 10
            """,
            (machine_id, cutoff),
        ).fetchall()
        return [dict(row) for row in rows]
