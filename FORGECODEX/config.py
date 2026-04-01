import os

from dotenv import load_dotenv

load_dotenv()

# Machine identity
MACHINE_ID = os.getenv("MACHINE_ID", "M-01")
TOOL_ID = os.getenv("TOOL_ID", "BROACH-HSS-001")
PLANT_ID = os.getenv("PLANT_ID", "RANE-CHENNAI")

# Audio capture
SAMPLE_RATE = 44100
CHUNK_DURATION = 0.5
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)
AUDIO_DEVICE_INDEX = 0
AUDIO_CHANNELS = 1

# Cutting window detection
CUTTING_RMS_THRESHOLD = 0.02
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
DEMO_AUDIO_FILE = "data/demo_cutting_audio.wav"

# Feature extraction
BANDPASS_LOW_HZ = 1000
BANDPASS_HIGH_HZ = 15000
BANDPASS_FILTER_ORDER = 4
WELCH_NPERSEG = 1024
EPSILON = 1e-10
LOW_BAND_MAX_HZ = 5000
MID_BAND_MAX_HZ = 12000
HIGH_BAND_MAX_HZ = 20000
DEFAULT_FEATURE_FILL = 0.0

# Physics engine (Taylor's Tool Life)
DEFAULT_CUTTING_SPEED = 8.0
DEFAULT_TAYLOR_N = 0.12
DEFAULT_TAYLOR_C = 60.0
DEFAULT_TOOL_LIFE = 500
WEAR_EXPONENT = 1.3
TRAINING_TOOL_COUNT = 200
TRAINING_SPEED_MIN = 6.0
TRAINING_SPEED_MAX = 12.0
TRAINING_N_MIN = 0.09
TRAINING_N_MAX = 0.16
TRAINING_STROKES_MIN = 350
TRAINING_STROKES_MAX = 700
TRAINING_NOISE_MIN = 0.03
TRAINING_NOISE_MAX = 0.08
TRAINING_MIN_ROWS = 70000
TRAINING_TARGET_ROWS = 100000
TRAINING_DATA_PATH = "data/forge_training_data.csv"

# Biometric enrollment
ENROLLMENT_STROKES = 20
CALIBRATION_FACTOR_MIN = 0.5
CALIBRATION_FACTOR_MAX = 2.0
MFCC_COUNT = 13
ENROLLMENT_RMS_REFERENCE = 0.015
BIOMETRIC_DISTANCE_SCALE = 2.0

# Decision engine
REPLACE_NOW_ACTION = "REPLACE_NOW"
COMPLETE_JOB_ACTION = "COMPLETE_JOB_THEN_REPLACE"
RUN_TO_FAILURE_ACTION = "RUN_TO_FAILURE"
DEFAULT_MONITOR_ACTION = "MONITOR"

# TFT model
TFT_MODEL_PATH = "data/models/forge_tft_v1.ckpt"
TFT_ENCODER_LENGTH = 30
TFT_PREDICTION_LENGTH = 10
TFT_HIDDEN_SIZE = 64
TFT_ATTENTION_HEADS = 4
TFT_DROPOUT = 0.1
TFT_HIDDEN_CONTINUOUS = 32
TFT_BATCH_SIZE = 64
TFT_MAX_EPOCHS = 50
TFT_LEARNING_RATE = 0.03
TFT_OUTPUT_SIZE = 7
TFT_QUANTILES = [0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9]
FAILURE_LOWER_BOUND_STROKES = 50

# Alert thresholds
ALERT_FAILURE_PROB_THRESHOLD = 0.4
ALERT_COOLDOWN_STROKES = 50
TWIN_DIVERGENCE_WARN = 1.5
TWIN_DIVERGENCE_ALERT = 2.0
TWIN_DIVERGENCE_CRITICAL = 3.0
ALERT_THRESHOLD_MIN = 0.2
ALERT_THRESHOLD_MAX = 0.8
ALERT_THRESHOLD_STEP = 0.05
ALERT_RECALIBRATION_OVERRIDE_COUNT = 3

# Financial model
TOOL_COST_INR = 60000
DOWNTIME_RATE_INR_PER_HOUR = 12000
PLANNED_REPLACE_HOURS = 0.5
UNPLANNED_DOWNTIME_HOURS = 4.0
STROKES_PER_HOUR = 80
DEFAULT_JOB_STROKES_REMAINING = 80

# Federated learning
FLOWER_SERVER_ADDRESS = os.getenv("FLOWER_SERVER", "localhost:8080")
FEDERATED_ROUNDS = 10
MIN_FIT_CLIENTS = 1 if DEMO_MODE else 2

# External APIs
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
SUPERVISOR_PHONE = os.getenv("SUPERVISOR_PHONE")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = "claude-sonnet-4-6"
LLM_MAX_TOKENS = 300

# Trust and messaging
OVERRIDE_REASON_TEXT = {
    1: "ToolFine",
    2: "Deadline",
    3: "Unclear",
    4: "Other",
}
TRUST_FEATURE_NAME_MAP = {
    0: "rms",
    1: "kurtosis",
    2: "skewness",
    3: "crest_factor",
    4: "peak_amplitude",
    5: "spectral_centroid",
    6: "spectral_bandwidth",
    7: "low_band_energy",
    8: "mid_band_energy",
    9: "high_band_energy",
    10: "high_low_ratio",
    11: "dominant_freq",
    12: "biometric_wear",
    13: "twin_divergence",
}
TRUST_EXPLANATION_TEMPLATES = {
    "kurtosis": "Impact spikes are rising beyond the normal cutting pattern, which usually indicates unstable tool wear.",
    "spectral_centroid": "The acoustic energy has shifted upward in frequency, which is consistent with sharper friction and wear.",
    "high_low_ratio": "High-frequency energy is overtaking the low-frequency band, which is a common wear signature.",
    "rms": "Overall acoustic power has increased compared with baseline, showing the cut is getting harsher.",
    "biometric_wear": "The current acoustic fingerprint is drifting away from the enrolled tool identity.",
    "twin_divergence": "The live machine behavior is separating from the digital twin expectation.",
}
WHATSAPP_OVERRIDE_PROMPT = "Why override? [1] Tool feels fine [2] Production deadline [3] Alert unclear [4] Other Reply with number."
TAMIL_UNICODE_MIN = 0x0B80
TAMIL_UNICODE_MAX = 0x0BFF

# Database
DB_PATH = "data/forge.db"

# FastAPI
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8001"))

# GPIO
LED_STATUS_PIN = 17

# Sonification
SONIFICATION_SAMPLE_RATE = 22050
SONIFICATION_DURATION_SEC = 1.0
SONIFICATION_BASE_FREQ = 220.0
SONIFICATION_DIVERGENCE_GAIN = 55.0

# Runtime loop
IDLE_SLEEP_SEC = 0.1
ERROR_SLEEP_SEC = 0.1

# Sensor buses and addresses
I2C_BUS_ID = 1
SPI_BUS_ID = 0
SPI_DEVICE_ID = 0
SPI_MAX_SPEED_HZ = 1000000
SPI_MODE = 1
MPU6050_I2C_ADDRESS = 0x68
MPU6050_PWR_MGMT_1 = 0x6B
MPU6050_ACCEL_XOUT_H = 0x3B
MPU6050_TEMP_OUT_H = 0x41
MPU6050_GYRO_XOUT_H = 0x43
MPU6050_ACCEL_SCALE = 16384.0
MPU6050_GYRO_SCALE = 131.0
GRAVITY_MPS2 = 9.81
MAX31865_CONFIG_REGISTER = 0x00
MAX31865_RTD_MSB_REGISTER = 0x01
MAX31865_CONFIG_BIAS_AUTO = 0xC2

# Sensor fallbacks
DEFAULT_SENSOR_TEMPERATURE = 25.0
PT100_FAULT_TEMPERATURE = -999.0
DEFAULT_ACCEL_AXIS_VALUE = 0.0
DEFAULT_GYRO_AXIS_VALUE = 0.0
DEFAULT_MPU_TEMPERATURE = 0.0
ZERO_VIBRATION_DICT = {
    "ax": DEFAULT_ACCEL_AXIS_VALUE,
    "ay": DEFAULT_ACCEL_AXIS_VALUE,
    "az": DEFAULT_ACCEL_AXIS_VALUE,
    "gx": DEFAULT_GYRO_AXIS_VALUE,
    "gy": DEFAULT_GYRO_AXIS_VALUE,
    "gz": DEFAULT_GYRO_AXIS_VALUE,
    "temperature": DEFAULT_MPU_TEMPERATURE,
}
