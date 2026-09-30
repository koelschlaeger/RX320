"""End to end: real GUI, RX320 wrapper and driver, talking over a
pseudo-terminal to a fake radio."""

import time

import pytest

from fakes import tune_bytes, wait_until
from RX320.RX320 import RX320


@pytest.fixture
def app(make_window, pty_radio):
    window = make_window(RX320())
    window.comboBoxSerialPort.addItem(pty_radio.port)
    window.comboBoxSerialPort.setCurrentText(pty_radio.port)
    window._connect()
    assert window.sdr.connected
    return window


def test_connect_programs_radio_with_volume_last(app, pty_radio):
    wait_until(lambda: len(pty_radio.commands(b'V')) >= 1)
    received = pty_radio.commands()
    assert received[-2:] == [b'A\x00\x3f', b'V\x00\x3f']
    assert b'M0' in received and b'G2' in received and b'W\x21' in received
    assert tune_bytes(0.5, 'AM', 8000) in received


def test_mode_change_retunes_over_the_wire(app, pty_radio):
    app.spinBoxVFOA.setValue(7.2)
    app.modeButtonGroup.button(1).click()  # USB
    # The radio must end on a tune calculated for USB. It may arrive before
    # M1: a still-queued AM tune is replaced in place by the USB retune.
    final = tune_bytes(7.2, 'USB', 8000)
    wait_until(lambda: pty_radio.commands(b'N')[-1:] == [final]
               and b'M1' in pty_radio.commands())


def test_signal_strength_reaches_the_meter(qtbot, app, pty_radio):
    pty_radio.signal = 4321
    qtbot.waitUntil(lambda: app.progressBarSignal.value() == 4321, timeout=3000)


def test_unplug_is_detected(qtbot, app, pty_radio, dialogs):
    driver = app.sdr.sdr
    pty_radio.unplug()
    qtbot.waitUntil(lambda: app.labelConnection.text() == 'Connection lost', timeout=3000)
    assert dialogs == [('warning', 'Connection lost')]
    assert not driver.queue_thread.is_alive()
    assert not driver.com.is_open


def test_connecting_again_replaces_the_driver(pty_radio):
    radio = RX320()
    radio.connect(pty_radio.port)
    first = radio.sdr
    radio.connect(pty_radio.port)
    try:
        assert radio.sdr is not first
        assert not first.queue_thread.is_alive()  # no orphaned worker
        assert not first.com.is_open
        assert radio.connected
    finally:
        radio.disconnect()


def test_close_stops_the_driver(app):
    driver = app.sdr.sdr
    app.close()
    assert not driver.queue_thread.is_alive()
    assert not driver.com.is_open


def test_fast_dial_spin_is_merged(app, pty_radio):
    # Throttle writes to real 1200 baud (10 bits per byte), as the radio's
    # serial line would, so a backlog can build up.
    com = app.sdr.sdr.com
    real_write = com.write
    com.write = lambda data: (time.sleep(len(data) * 10 / 1200), real_write(data))[1]
    wait_until(lambda: app.sdr.sdr.msg_queue.empty())
    pty_radio.received.clear()

    app.stepButtonGroup.button(2).click()  # 1 kHz
    for click in range(1, 31):
        app.dial.setValue(click)
        time.sleep(0.01)

    final = tune_bytes(0.53, 'AM', 8000)
    wait_until(lambda: pty_radio.commands(b'N')[-1:] == [final])
    assert len(pty_radio.commands(b'N')) < 30


def test_scan_end_to_end(qtbot, app, pty_radio):
    # A station at 7.100 MHz: the radio reports 5000 while tuned there (in
    # CW with the 4800 Hz filter, as scanned with the default 5 kHz step)
    station = tune_bytes(7.1, 'CW', 4800)
    pty_radio.signal_for = lambda tune: 5000 if tune == station else 100
    app.spinBoxVFOA.setValue(14.2)
    app.pushButtonScan.click()
    scan = app.scanWindow
    scan.spinStart.setValue(7.09)
    scan.spinStop.setValue(7.11)
    scan.spinSamples.setValue(2)
    scan.spinSettle.setValue(0)
    wait_until(lambda: app.sdr.sdr.msg_queue.empty())
    pty_radio.received.clear()

    scan.buttonStart.click()
    qtbot.waitUntil(lambda: scan.scanner.finished, timeout=10000)
    assert scan.scanner.state == 'done'
    peak = max(scan.scanner.points, key=lambda p: p.mean)
    assert (peak.freq, peak.readings) == (7.1, (5000, 5000))

    # Muted, CW, 4800 Hz and Fast AGC before the first measurement, which
    # comes between the first and second scan tunes. (The first tune itself
    # may arrive earlier: it merges into the retune queued by the mode
    # change, but it is calculated for CW and 4800 Hz.)
    received = pty_radio.commands()
    assert tune_bytes(7.09, 'CW', 4800) in received
    second_scan_tune = received.index(tune_bytes(7.095, 'CW', 4800))
    for setup in (b'C\x00\x3f', b'M3', b'W\x04', b'G3'):
        assert received.index(setup) < second_scan_tune
    # Afterwards everything the user had, with volume last
    assert_restored(pty_radio)


def assert_restored(pty_radio):
    """After a scan (or its end by disconnecting): AM, 8000 Hz, Medium AGC,
    14.2 MHz and the muted volumes the test user had, with volume last."""
    back = tune_bytes(14.2, 'AM', 8000)
    wait_until(lambda: pty_radio.commands()[-2:] == [b'A\x00\x3f', b'V\x00\x3f'])
    received = pty_radio.commands()
    after = received[len(received) - received[::-1].index(b'G3'):]  # after scan setup
    assert {b'M0', b'W\x21', b'G2'} <= set(after)
    assert [c for c in after if c[:1] == b'N'][-1] == back


def test_disconnect_during_scan_restores_the_radio(app, pty_radio):
    app.spinBoxVFOA.setValue(14.2)
    app.pushButtonScan.click()
    app.scanWindow.spinSettle.setValue(500)  # still settling at the disconnect
    wait_until(lambda: app.sdr.sdr.msg_queue.empty())
    pty_radio.received.clear()
    app.scanWindow.buttonStart.click()
    wait_until(lambda: b'G3' in pty_radio.commands())  # scan under way
    app.pushButtonDisconnect.click()
    # The restore reached the radio before the port closed
    assert_restored(pty_radio)
