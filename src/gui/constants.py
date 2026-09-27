"""Shared constants for the RX320 GUI."""

from pathlib import Path

# Image directory, resolved from this file so the app can be launched from any cwd.
IMG_DIR = Path(__file__).resolve().parent.parent / 'img'

# Available tuning step sizes, in Hz.

TuningSteps = (10.0, 100.0, 1000.0, 5000.0, 10000.0)
