"""Signal-strength scan across a frequency range, independent of the GUI
toolkit: tunes each frequency in turn, measures, and collects the results.
A GUI timer drives it by calling poll()."""

import time
from dataclasses import dataclass

from RX320 import RX320_Data as data

MIN_STEP_HZ = 10    # the smallest tuning step the GUI offers

# Bytes on the wire per scan step, for the time estimate
TUNE_BYTES = 8      # 'N' + 6 tuning factor bytes + '\r'
POLL_BYTES = 6      # 'X\r' out, 'X' + 16-bit value + '\r' back
BITS_PER_BYTE = 10  # 8N1: start bit + 8 data bits + stop bit


def scan_frequencies(start, stop, step, low=data.MINFREQ, high=data.MAXFREQ):
    """Frequencies (MHz) from start to stop in steps, clamped to low..high.
    Worked out in whole Hz so a long scan doesn't drift. Stop is included
    even when it isn't a whole number of steps from start."""
    start_hz, stop_hz, step_hz = (round(f * 1_000_000) for f in (start, stop, step))
    if step_hz < MIN_STEP_HZ:
        raise ValueError(f'step must be at least {MIN_STEP_HZ} Hz')
    start_hz = max(start_hz, round(low * 1_000_000))
    stop_hz = min(stop_hz, round(high * 1_000_000))
    if stop_hz <= start_hz:
        raise ValueError('stop must be above start, within the tuning range')
    freqs = list(range(start_hz, stop_hz + 1, step_hz))
    if freqs[-1] != stop_hz:
        freqs.append(stop_hz)
    return tuple(f / 1_000_000 for f in freqs)


@dataclass(frozen=True)
class ScanPoint:
    freq: float         # MHz
    readings: tuple     # raw signal readings taken at this frequency

    @property
    def mean(self):
        # None when no valid reading arrived (every reply garbled)
        return sum(self.readings) / len(self.readings) if self.readings else None


class Scanner:
    """One scan. States: 'idle' -> 'running' -> 'done', 'stopped' or
    'failed' (connection lost; the exception is in .error)."""

    def __init__(self, radio, start, stop, step, samples, settle,
                 clock=time.monotonic):
        if samples < 1:
            raise ValueError('samples must be at least 1')
        if settle < 0:
            raise ValueError('settle time cannot be negative')
        self.radio = radio
        self.frequencies = scan_frequencies(start, stop, step,
                                            radio.MIN_FREQ, radio.MAX_FREQ)
        self.samples = samples
        self.settle = settle
        self.points = []
        self.state = 'idle'
        self.error = None
        self._clock = clock
        self._started = None
        self._pending = None    # Future of the measurement in progress

    @property
    def finished(self):
        return self.state in ('done', 'stopped', 'failed')

    @property
    def progress(self):
        return len(self.points), len(self.frequencies)

    def start(self):
        self.state = 'running'
        self._started = self._clock()
        self._next_step()

    def poll(self):
        """If the current measurement has finished, record it and start the
        next step. Returns the new ScanPoint, or None. Only one measurement
        is ever outstanding, so a call completes at most one step."""
        if self.state != 'running' or not self._pending.done():
            return None
        future, self._pending = self._pending, None
        if future.cancelled():
            self._fail(ConnectionError('measurement cancelled'))
            return None
        if future.exception() is not None:
            self._fail(future.exception())
            return None
        point = ScanPoint(self.frequencies[len(self.points)], tuple(future.result()))
        self.points.append(point)
        self._next_step()
        return point

    def stop(self):
        if self.state == 'running':
            if self._pending is not None:
                self._pending.cancel()  # no effect once the radio is measuring
            self.state = 'stopped'

    def estimated_duration(self):
        """Seconds for the whole scan, from the serial speed."""
        wire = (TUNE_BYTES + self.samples * POLL_BYTES) * BITS_PER_BYTE
        per_step = wire / data.SerialSettings().baudrate + self.settle
        return len(self.frequencies) * per_step

    def remaining_time(self):
        done, total = self.progress
        if done == 0:
            return self.estimated_duration()
        pace = (self._clock() - self._started) / done
        return pace * (total - done)

    def nearest_point(self, freq):
        if not self.points:
            return None
        return min(self.points, key=lambda p: abs(p.freq - freq))

    def _next_step(self):
        if len(self.points) == len(self.frequencies):
            self.state = 'done'
            return
        try:
            self.radio.set_vfo(self.frequencies[len(self.points)])
            self._pending = self.radio.measure_signal(self.samples, self.settle)
        except ConnectionError as error:
            self._fail(error)

    def _fail(self, error):
        self.state = 'failed'
        self.error = error
