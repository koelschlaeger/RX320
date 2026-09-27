"""Radio (VFO) state and control logic, independent of the GUI toolkit."""


class RadioController:
    """Owns radio state and talks to the SDR. No Qt dependencies."""

    def __init__(self, sdr):
        self.sdr = sdr
        self.vfo_a = sdr.DEFAULT_FREQ  # MHz
        self.vfo_b = sdr.DEFAULT_FREQ  # MHz

    def _clamp(self, freq_mhz: float) -> float:
        return max(self.sdr.MIN_FREQ, min(self.sdr.MAX_FREQ, freq_mhz))

    def restore(self, vfo_a: float, vfo_b: float):
        """Set both VFOs (clamped) without sending anything to the radio."""
        self.vfo_a = self._clamp(vfo_a)
        self.vfo_b = self._clamp(vfo_b)

    def set_vfo_a(self, freq_mhz: float) -> float:
        """Set VFO A to an absolute frequency (clamped). Returns the applied value."""
        self.vfo_a = self._clamp(freq_mhz)
        self.sdr.set_vfo(self.vfo_a)
        return self.vfo_a

    def step_vfo_a(self, step_mhz: float) -> float:
        """Nudge VFO A by a relative step (clamped). Returns the applied value."""
        return self.set_vfo_a(self.vfo_a + step_mhz)

    def store_a_to_b(self) -> float:
        """Copy VFO A into VFO B. Returns the new B value."""
        self.vfo_b = self.vfo_a
        return self.vfo_b

    def swap_vfo(self) -> tuple[float, float]:
        """Swap A and B, and re-tune the radio to the new A. Returns (a, b)."""
        self.vfo_a, self.vfo_b = self.vfo_b, self.vfo_a
        self.vfo_a = self._clamp(self.vfo_a)  # now actually protected
        self.sdr.set_vfo(self.vfo_a)
        return self.vfo_a, self.vfo_b
