"""The scan logic, without Qt: frequency plan, stepping, results."""

import pytest

from fakes import FakeRadio
from gui.scanner import Scanner, ScanPoint, scan_frequencies


def peak_at_7_1(freq):
    """A fake band: noise floor 100, a signal of 5000 at 7.100 MHz."""
    return 5000 if round(freq, 6) == 7.1 else 100


@pytest.fixture
def radio():
    radio = FakeRadio()
    radio.connected = True
    return radio


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


# --- Frequency plan ------------------------------------------------------------

def test_frequencies_have_no_rounding_drift():
    freqs = scan_frequencies(7.0, 7.3, 0.005)
    assert len(freqs) == 61
    assert freqs[0] == 7.0 and freqs[-1] == 7.3
    assert freqs == tuple(round(7.0 + i * 0.005, 6) for i in range(61))


def test_stop_is_included_when_not_a_whole_step_away():
    assert scan_frequencies(7.0, 7.012, 0.005) == (7.0, 7.005, 7.01, 7.012)


def test_frequencies_are_clamped_to_the_tuning_range():
    assert scan_frequencies(0.1, 0.52, 0.01) == (0.5, 0.51, 0.52)
    assert scan_frequencies(29.98, 35, 0.01)[-1] == 30.0


@pytest.mark.parametrize('start, stop, step', [
    (7.3, 7.0, 0.005),      # stop below start
    (7.0, 7.0, 0.005),      # empty range
    (7.0, 7.3, 0),          # no step
    (7.0, 7.3, 0.000001),   # below the 10 Hz minimum step
    (31, 32, 0.01),         # entirely above the tuning range
])
def test_invalid_frequency_plans_are_rejected(start, stop, step):
    with pytest.raises(ValueError):
        scan_frequencies(start, stop, step)


@pytest.mark.parametrize('samples, settle', [(0, 0.1), (5, -0.1)])
def test_invalid_measurement_settings_are_rejected(radio, samples, settle):
    with pytest.raises(ValueError):
        Scanner(radio, 7.0, 7.3, 0.005, samples, settle)


# --- Running a scan --------------------------------------------------------------

def test_complete_scan_finds_the_peak(radio):
    radio.signal_at = peak_at_7_1
    scanner = Scanner(radio, 7.0, 7.3, 0.005, samples=5, settle=0.1)
    scanner.start()
    while not scanner.finished:
        scanner.poll()
    assert scanner.state == 'done'
    assert [p.freq for p in scanner.points] == list(scanner.frequencies)
    peak = max(scanner.points, key=lambda p: p.mean)
    assert (peak.freq, peak.mean) == (7.1, 5000)
    assert radio.named('measure_signal') == [('measure_signal', 5, 0.1)] * 61
    assert scanner.progress == (61, 61)


def test_each_step_tunes_then_measures(radio):
    radio.auto_measure = False
    scanner = Scanner(radio, 7.0, 7.01, 0.005, samples=3, settle=0.1)
    scanner.start()
    assert radio.calls == [('set_vfo', 7.0), ('measure_signal', 3, 0.1)]
    assert scanner.poll() is None  # measurement still running

    radio.calls.clear()
    radio.measurements[0].set_result([10, 20, 60])
    assert scanner.poll() == ScanPoint(7.0, (10, 20, 60))
    assert radio.calls == [('set_vfo', 7.005), ('measure_signal', 3, 0.1)]
    assert scanner.progress == (1, 3)


def test_mean_of_readings():
    assert ScanPoint(7.0, (10, 20, 60)).mean == 30
    assert ScanPoint(7.0, ()).mean is None  # every reply was garbled


def test_stop_cancels_the_pending_measurement(radio):
    radio.auto_measure = False
    scanner = Scanner(radio, 7.0, 7.3, 0.005, samples=1, settle=0)
    scanner.start()
    radio.measurements[0].set_result([100])
    scanner.poll()
    scanner.stop()
    assert scanner.state == 'stopped' and scanner.finished
    assert radio.measurements[1].cancelled()
    tunes = len(radio.named('set_vfo'))
    assert scanner.poll() is None
    assert len(radio.named('set_vfo')) == tunes  # nothing more sent
    assert len(scanner.points) == 1  # results so far are kept


def test_result_arriving_after_stop_is_ignored(radio):
    # Stopped while the radio was already measuring: the cancel has no
    # effect, and the late result must not be recorded or start a new step.
    radio.auto_measure = False
    scanner = Scanner(radio, 7.0, 7.3, 0.005, samples=1, settle=0)
    scanner.start()
    radio.measurements[0].set_running_or_notify_cancel()  # radio busy
    scanner.stop()
    radio.measurements[0].set_result([100])
    assert scanner.poll() is None
    assert scanner.points == []
    assert len(radio.named('set_vfo')) == 1
    assert scanner.state == 'stopped'


@pytest.mark.parametrize('end', ['cancel', 'exception'])
def test_lost_connection_fails_the_scan(radio, end):
    radio.auto_measure = False
    scanner = Scanner(radio, 7.0, 7.3, 0.005, samples=1, settle=0)
    scanner.start()
    if end == 'cancel':
        radio.measurements[0].cancel()
    else:
        radio.measurements[0].set_exception(ConnectionError('port lost'))
    assert scanner.poll() is None
    assert scanner.state == 'failed' and scanner.finished
    assert isinstance(scanner.error, ConnectionError)


def test_scan_without_connection_fails_at_start(radio):
    radio.connected = False
    scanner = Scanner(radio, 7.0, 7.3, 0.005, samples=1, settle=0)
    scanner.start()
    assert scanner.state == 'failed'
    assert isinstance(scanner.error, ConnectionError)


# --- Time and clicking -------------------------------------------------------------

def test_estimated_duration_at_1200_baud(radio):
    # Per step: tune (8 bytes) + 5 polls (6 bytes each) at 10 bits per byte,
    # plus the settle time
    scanner = Scanner(radio, 7.0, 7.3, 0.005, samples=5, settle=0.1)
    per_step = (8 + 5 * 6) * 10 / 1200 + 0.1
    assert scanner.estimated_duration() == pytest.approx(61 * per_step)


def test_remaining_time_uses_the_measured_pace(radio):
    clock = Clock()
    radio.auto_measure = False
    scanner = Scanner(radio, 7.0, 7.3, 0.005, samples=5, settle=0.1, clock=clock)
    assert scanner.remaining_time() == pytest.approx(scanner.estimated_duration())
    scanner.start()
    for i in range(10):
        clock.now += 0.5
        radio.measurements[i].set_result([100])
        scanner.poll()
    assert scanner.remaining_time() == pytest.approx(0.5 * 51)


def test_nearest_point_to_a_click(radio):
    scanner = Scanner(radio, 7.0, 7.3, 0.005, samples=1, settle=0)
    assert scanner.nearest_point(7.1) is None  # nothing measured yet
    scanner.start()
    while not scanner.finished:
        scanner.poll()
    assert scanner.nearest_point(7.1021).freq == 7.1
    assert scanner.nearest_point(7.1029).freq == 7.105
    assert scanner.nearest_point(99).freq == 7.3
