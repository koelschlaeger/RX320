"""Shared constants for the RX320 GUI."""

from pathlib import Path

# Image directory, resolved from this file so the app can be launched from any cwd.
IMG_DIR = Path(__file__).resolve().parent.parent / 'img'

# Available tuning step sizes, in Hz.

TuningSteps = (10.0, 100.0, 1000.0, 5000.0, 10000.0)

DEFAULT_STEP = 5000.0   # Hz

# Scan window defaults: the 40 m band, where there is usually something to see
DEFAULT_SCAN_START = 7.0        # MHz
DEFAULT_SCAN_STOP = 7.3         # MHz
DEFAULT_SCAN_STEP = 5.0         # kHz
DEFAULT_SCAN_SAMPLES = 5        # readings averaged per frequency
DEFAULT_SCAN_SETTLE = 100       # ms to wait after tuning before measuring
SCAN_AGC = 'Fast'               # AGC while scanning: recovers quickest between steps
