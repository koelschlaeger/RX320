"""Scanning from the main window: opening the scan window, Fast AGC during
a scan, locking and restoring the main controls, click-to-tune."""

import pytest

from gui.constants import SCAN_AGC
from test_main_window import button


def peak_at_7_1(freq):
    return 5000 if round(freq, 6) == 7.1 else 100


@pytest.fixture
def scan(connected, radio):
    """The scan window, opened from a connected main window whose user has
    chosen Slow AGC and 14.2 MHz."""
    connected.agcButtonGroup.button(connected.AGCModes.index('Slow')).click()
    connected.spinBoxVFOA.setValue(14.2)
    radio.signal_at = peak_at_7_1
    button(connected, 'Scan…').click()
    radio.calls.clear()
    return connected.scanWindow


def run_to_end(qtbot, scan):
    scan.buttonStart.click()
    qtbot.waitUntil(lambda: scan.scanner.finished)


def test_scan_agc_is_a_real_agc_mode(radio):
    assert SCAN_AGC in radio.AGC_MODES


def test_scan_button_needs_a_connection(qtbot, window, radio):
    assert not button(window, 'Scan…').isEnabled()
    button(window, 'Connect').click()
    assert button(window, 'Scan…').isEnabled()
    button(window, 'Disconnect').click()
    assert not button(window, 'Scan…').isEnabled()


def test_scan_button_opens_one_separate_window(connected):
    button(connected, 'Scan…').click()
    scan = connected.scanWindow
    assert scan.isVisible() and scan.isWindow()
    button(connected, 'Scan…').click()
    assert connected.scanWindow is scan  # reused, not a second window


def test_fast_agc_during_scan_then_settings_restored(qtbot, scan, radio):
    run_to_end(qtbot, scan)
    assert radio.calls[0] == ('set_agc', SCAN_AGC)  # before the first tune
    assert radio.calls[1] == ('set_vfo', 7.0)
    assert radio.calls[-2:] == [('set_agc', 'Slow'), ('set_vfo', 14.2)]


def test_main_controls_locked_while_scanning(scan, radio):
    main = scan.parent()
    radio.auto_measure = False
    scan.buttonStart.click()
    assert not main.modeGroupBox.isEnabled()
    assert not main.agcGroupBox.isEnabled()
    assert not main.spinBoxVFOA.isEnabled()
    assert not main.vfoGroupBox.isEnabled()
    assert main.labelAGC_Act.text() == f'{SCAN_AGC} (scan)'
    assert main.spinBoxVFOA.value() == pytest.approx(14.2)  # display unchanged

    scan.buttonStop.click()
    assert main.modeGroupBox.isEnabled() and main.spinBoxVFOA.isEnabled()
    assert main.labelAGC_Act.text() == 'Slow'


def test_stopping_restores_settings(scan, radio):
    radio.auto_measure = False
    scan.buttonStart.click()
    radio.measurements[0].set_result([100])
    scan.buttonStop.click()
    assert radio.calls[-2:] == [('set_agc', 'Slow'), ('set_vfo', 14.2)]


def test_click_to_tune_moves_vfo_a(qtbot, scan, radio):
    main = scan.parent()
    run_to_end(qtbot, scan)
    radio.calls.clear()
    scan.tune_to(7.1003)
    assert radio.calls == [('set_vfo', 7.1)]
    assert main.spinBoxVFOA.value() == pytest.approx(7.1)
    assert main.radio.vfo_a == pytest.approx(7.1)


def test_disconnect_during_scan_stops_it_first(scan, radio, dialogs):
    main = scan.parent()
    radio.auto_measure = False
    scan.buttonStart.click()
    button(main, 'Disconnect').click()
    assert scan.labelStatus.text() == 'Stopped'  # not "connection lost"
    # Restored while the port was still open, then disconnected
    assert radio.calls[-3:] == [('set_agc', 'Slow'), ('set_vfo', 14.2), ('disconnect',)]
    assert dialogs == []
    assert not scan.buttonStart.isEnabled()


def test_lost_connection_during_scan(qtbot, scan, radio, dialogs):
    main = scan.parent()
    radio.auto_measure = False
    scan.buttonStart.click()
    radio.calls.clear()
    radio.connected = False              # e.g. USB unplugged
    radio.measurements[0].cancel()       # the driver ends the measurement
    qtbot.waitUntil(lambda: main.labelConnection.text() == 'Connection lost')
    qtbot.waitUntil(lambda: scan.scanner.finished)
    assert [c for c in radio.calls if c[0] != 'disconnect'] == []  # nothing to restore
    assert not main.modeGroupBox.isEnabled()
    assert not scan.buttonStart.isEnabled()
    assert ('warning', 'Connection lost') in dialogs


def test_reconnecting_enables_scanning_again(scan):
    main = scan.parent()
    button(main, 'Disconnect').click()
    assert not scan.buttonStart.isEnabled()
    button(main, 'Connect').click()
    assert scan.buttonStart.isEnabled()


def test_closing_the_app_stops_the_scan(scan, radio):
    main = scan.parent()
    radio.auto_measure = False
    scan.buttonStart.click()
    main.close()
    assert scan.scanner.state == 'stopped'
    assert not scan.isVisible()
    assert radio.calls[-3:] == [('set_agc', 'Slow'), ('set_vfo', 14.2), ('disconnect',)]
