"""The scan window: inputs, running a scan, the live plot, click-to-tune."""

import math

import pytest
from PyQt6.QtCore import QPointF, QSettings, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QWidget

from fakes import FakeRadio
from gui.scan_window import ScanWindow, format_duration, format_frequency


def peak_at_7_1(freq):
    """A fake band: noise floor 100, a signal of 5000 at 7.100 MHz."""
    return 5000 if round(freq, 6) == 7.1 else 100


@pytest.fixture
def radio():
    radio = FakeRadio()
    radio.connected = True
    radio.signal_at = peak_at_7_1
    return radio


@pytest.fixture
def scan(qtbot, radio):
    window = ScanWindow(radio)
    qtbot.addWidget(window)
    window.show()
    return window


@pytest.fixture
def events(scan):
    """Records the window's signals, and how many radio calls had been made
    when each was emitted."""
    log = []
    scan.scanStarted.connect(lambda: log.append(('started', len(scan.sdr.calls))))
    scan.scanFinished.connect(lambda: log.append(('finished',)))
    scan.tuneRequested.connect(lambda freq: log.append(('tune', freq)))
    return log


def plotted(scan):
    """The plotted points, with frequencies converted back to MHz (the plot
    works in Hz so its axis can show kHz or MHz)."""
    xs, ys = scan.curve.getData()
    return ([] if xs is None else [round(x / 1e6, 6) for x in xs],
            [] if ys is None else list(ys))


def run_to_end(qtbot, scan):
    scan.buttonStart.click()
    qtbot.waitUntil(lambda: scan.scanner.finished)


# --- Inputs and estimate ---------------------------------------------------------

def test_defaults_and_estimate(scan):
    assert (scan.spinStart.value(), scan.spinStop.value()) == (7.0, 7.3)
    assert scan.spinStep.value() == 5.0      # kHz
    assert scan.spinSamples.value() == 5
    assert scan.spinSettle.value() == 100    # ms
    assert scan.labelEstimate.text() == '61 steps, about 25 s'
    assert scan.buttonStart.isEnabled()
    assert not scan.buttonStop.isEnabled()


def test_estimate_follows_the_inputs(scan):
    scan.spinStep.setValue(10)
    assert scan.labelEstimate.text().startswith('31 steps')


def test_invalid_range_disables_start(scan):
    scan.spinStop.setValue(6.9)
    assert not scan.buttonStart.isEnabled()
    assert 'stop must be above start' in scan.labelEstimate.text()
    scan.spinStop.setValue(7.3)
    assert scan.buttonStart.isEnabled()


def test_no_scanning_while_disconnected(scan):
    scan.set_connected(False)
    assert not scan.buttonStart.isEnabled()
    assert 'connect' in scan.labelEstimate.text().lower()
    scan.set_connected(True)
    assert scan.buttonStart.isEnabled()
    assert scan.labelEstimate.text() == '61 steps, about 25 s'


def test_scan_ending_after_disconnect_keeps_start_disabled(qtbot, scan, radio):
    radio.auto_measure = False
    scan.buttonStart.click()
    scan.set_connected(False)        # told while the scan was still running
    radio.measurements[0].cancel()   # ...which then fails
    qtbot.waitUntil(lambda: scan.scanner.finished)
    assert not scan.buttonStart.isEnabled()


def test_stays_a_separate_window_with_a_parent(qtbot, radio):
    parent = QWidget()
    qtbot.addWidget(parent)
    window = ScanWindow(radio, parent)
    assert window.isWindow()


# --- Remembering the inputs ------------------------------------------------------------

@pytest.fixture
def settings(tmp_path):
    return QSettings(str(tmp_path / 'scan.ini'), QSettings.Format.IniFormat)


def test_inputs_are_saved_and_restored(qtbot, scan, radio, settings):
    scan.spinStart.setValue(9.4)
    scan.spinStop.setValue(9.9)
    scan.spinStep.setValue(2.5)
    scan.spinSamples.setValue(8)
    scan.spinSettle.setValue(250)
    scan.save_settings(settings)

    restored = ScanWindow(radio)
    qtbot.addWidget(restored)
    restored.restore_settings(settings)
    assert restored.spinStart.value() == 9.4
    assert restored.spinStop.value() == 9.9
    assert restored.spinStep.value() == 2.5
    assert restored.spinSamples.value() == 8
    assert restored.spinSettle.value() == 250
    assert restored.labelEstimate.text().startswith('201 steps')


def test_nothing_saved_keeps_the_defaults(scan, settings):
    scan.restore_settings(settings)
    assert (scan.spinStart.value(), scan.spinStop.value()) == (7.0, 7.3)
    assert scan.labelEstimate.text() == '61 steps, about 25 s'


def test_corrupted_scan_settings_fall_back(scan, settings):
    for key, value in [('scan/start', 'hello'), ('scan/stop', 'abc'),
                       ('scan/step', ''), ('scan/samples', 999),
                       ('scan/settle', -5)]:
        settings.setValue(key, value)
    scan.restore_settings(settings)  # must not raise
    assert (scan.spinStart.value(), scan.spinStop.value()) == (7.0, 7.3)
    assert scan.spinStep.value() == 5.0
    assert scan.spinSamples.value() == 50   # clamped to the allowed range
    assert scan.spinSettle.value() == 0


@pytest.mark.parametrize('seconds, text', [
    (0.4, '1 s'), (25.4, '25 s'), (125, '2 min 5 s'), (3900, '1 h 5 min')])
def test_format_duration(seconds, text):
    assert format_duration(seconds) == text


@pytest.mark.parametrize('mhz, text', [
    (0.75, '750.000 kHz'), (0.500001, '500.001 kHz'),
    (1.0, '1.000000 MHz'), (7.1, '7.100000 MHz')])
def test_format_frequency(mhz, text):
    assert format_frequency(mhz) == text


@pytest.mark.parametrize('start, stop, unit', [
    (0.5, 0.9, 'kHz'),    # below 1 MHz: kHz, not "mMHz"
    (7.0, 7.3, 'MHz')])
def test_frequency_axis_units(qtbot, scan, start, stop, unit):
    scan.spinStart.setValue(start)
    scan.spinStop.setValue(stop)
    run_to_end(qtbot, scan)
    axis = scan.plot.getAxis('bottom')
    qtbot.waitUntil(lambda: axis.labelUnitPrefix + axis.labelUnits == unit)


# --- Running a scan ------------------------------------------------------------------

def test_scan_plots_every_point_and_finds_the_peak(qtbot, scan, radio, events):
    run_to_end(qtbot, scan)
    xs, ys = plotted(scan)
    assert xs == list(scan.scanner.frequencies)
    assert max(zip(ys, xs)) == (5000, 7.1)
    assert scan.progressBar.value() == scan.progressBar.maximum() == 61
    assert scan.labelStatus.text() == 'Done'


def test_scan_started_is_emitted_before_the_first_tune(qtbot, scan, events):
    # So the main window can switch to Fast AGC before anything is measured
    run_to_end(qtbot, scan)
    assert events == [('started', 0), ('finished',)]


def test_controls_are_locked_while_scanning(scan, radio):
    radio.auto_measure = False
    scan.buttonStart.click()
    assert not scan.buttonStart.isEnabled()
    assert scan.buttonStop.isEnabled()
    assert not scan.spinStart.isEnabled() and not scan.spinSamples.isEnabled()
    assert 'left' in scan.labelRemaining.text()

    scan.buttonStop.click()
    assert scan.buttonStart.isEnabled()
    assert not scan.buttonStop.isEnabled()
    assert scan.spinStart.isEnabled() and scan.spinSamples.isEnabled()


def test_plot_updates_live(qtbot, scan, radio):
    radio.auto_measure = False
    scan.buttonStart.click()
    radio.measurements[0].set_result([100])
    qtbot.waitUntil(lambda: len(plotted(scan)[0]) == 1)
    radio.measurements[1].set_result([300])
    qtbot.waitUntil(lambda: len(plotted(scan)[0]) == 2)
    assert plotted(scan) == ([7.0, 7.005], [100, 300])
    assert scan.progressBar.value() == 2


def test_stop_keeps_the_points_so_far(qtbot, scan, radio, events):
    radio.auto_measure = False
    scan.buttonStart.click()
    radio.measurements[0].set_result([100])
    qtbot.waitUntil(lambda: len(plotted(scan)[0]) == 1)
    scan.buttonStop.click()
    assert radio.measurements[1].cancelled()
    assert events[-1] == ('finished',)
    assert plotted(scan)[0] == [7.0]
    assert scan.labelStatus.text() == 'Stopped'


def test_lost_connection_ends_the_scan(qtbot, scan, radio, events):
    radio.auto_measure = False
    scan.buttonStart.click()
    radio.measurements[0].cancel()
    qtbot.waitUntil(lambda: events[-1] == ('finished',))
    assert 'connection lost' in scan.labelStatus.text().lower()
    assert scan.buttonStart.isEnabled()


def test_unreadable_step_leaves_a_gap(qtbot, scan, radio):
    radio.auto_measure = False
    scan.buttonStart.click()
    radio.measurements[0].set_result([])  # every reply garbled
    qtbot.waitUntil(lambda: len(plotted(scan)[1]) == 1)
    assert math.isnan(plotted(scan)[1][0])


def test_new_scan_replaces_the_previous_one(qtbot, scan):
    run_to_end(qtbot, scan)
    scan.tune_to(7.1)
    scan.spinStop.setValue(7.02)
    run_to_end(qtbot, scan)
    assert plotted(scan)[0] == [7.0, 7.005, 7.01, 7.015, 7.02]
    assert not scan.marker.isVisible()


def test_closing_the_window_stops_the_scan(scan, radio, events):
    radio.auto_measure = False
    scan.buttonStart.click()
    scan.close()
    assert scan.scanner.state == 'stopped'
    assert events[-1] == ('finished',)


# --- Click to tune ---------------------------------------------------------------------

def test_tune_to_nearest_measured_point(qtbot, scan, events):
    run_to_end(qtbot, scan)
    scan.tune_to(7.1021)
    assert events[-1] == ('tune', 7.1)
    assert scan.marker.isVisible() and scan.marker.value() == pytest.approx(7.1e6)  # Hz
    assert scan.marker.label.toPlainText() == '7.100000 MHz'


def test_marker_label_in_khz_below_1_mhz(qtbot, scan):
    scan.spinStart.setValue(0.5)
    scan.spinStop.setValue(0.9)
    run_to_end(qtbot, scan)
    scan.tune_to(0.75)
    assert scan.marker.label.toPlainText() == '750.000 kHz'


@pytest.mark.parametrize('freq', [7.0, 7.3])
def test_marker_label_stays_inside_the_plot(qtbot, scan, freq):
    # The label goes on whichever side of the line has room
    run_to_end(qtbot, scan)
    scan.tune_to(freq)
    qtbot.wait(50)  # let the label lay itself out
    label = scan.marker.label
    label_rect = label.mapRectToScene(label.boundingRect())
    plot_rect = scan.plot.plotItem.vb.sceneBoundingRect()
    assert plot_rect.left() <= label_rect.left()
    assert label_rect.right() <= plot_rect.right()


def test_no_tuning_while_scanning_or_before_a_scan(qtbot, scan, radio, events):
    scan.tune_to(7.1)  # nothing measured yet
    radio.auto_measure = False
    scan.buttonStart.click()
    radio.measurements[0].set_result([100])
    qtbot.waitUntil(lambda: len(plotted(scan)[0]) == 1)
    scan.tune_to(7.0)  # a point exists, but the scan is still running
    assert [e for e in events if e[0] == 'tune'] == []
    assert not scan.marker.isVisible()


def test_mouse_click_on_the_plot_tunes(qtbot, scan, events):
    run_to_end(qtbot, scan)
    # Click at 7.1 MHz, halfway up the plot. (The y range follows the data
    # only after a repaint, so don't pick a y value from the data.)
    view = scan.plot.plotItem.vb
    y_low, y_high = view.viewRange()[1]
    scene_pos = view.mapViewToScene(QPointF(7.1e6, (y_low + y_high) / 2))  # Hz
    widget_pos = scan.plot.mapFromScene(scene_pos)
    QTest.mouseClick(scan.plot.viewport(), Qt.MouseButton.LeftButton, pos=widget_pos)
    qtbot.waitUntil(lambda: events[-1] == ('tune', 7.1))


def test_click_outside_the_plot_area_is_ignored(qtbot, scan, events):
    run_to_end(qtbot, scan)
    QTest.mouseClick(scan.plot.viewport(), Qt.MouseButton.LeftButton,
                     pos=scan.plot.viewport().rect().bottomLeft())  # on the axes
    qtbot.wait(50)
    assert events[-1] == ('finished',)

