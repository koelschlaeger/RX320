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
    assert window.sdr.Connected
    return window


def test_connect_programs_radio_with_volume_last(app, pty_radio):
    wait_until(lambda: len(pty_radio.commands(b'V')) >= 1)
    received = pty_radio.commands()
    assert received[-2:] == [b'A\x00\x3f', b'V\x00\x3f']
    assert b'M0' in received and b'G2' in received and b'W\x21' in received
    assert tune_bytes(0.5, 'AM', 8000) in received


def test_mode_change_retunes_over_the_wire(app, pty_radio):
    app.spinBoxVFOA.setValue(7.2)
    app.modeButtonGroup.button(2).click()  # USB
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
    assert not driver.queueThread.is_alive()
    assert not driver.com.is_open


def test_close_stops_the_driver(app):
    driver = app.sdr.sdr
    app.close()
    assert not driver.queueThread.is_alive()
    assert not driver.com.is_open


def test_fast_dial_spin_is_merged(app, pty_radio):
    # Throttle writes to real 1200 baud (10 bits per byte), as the radio's
    # serial line would, so a backlog can build up.
    com = app.sdr.sdr.com
    real_write = com.write
    com.write = lambda data: (time.sleep(len(data) * 10 / 1200), real_write(data))[1]
    wait_until(lambda: app.sdr.sdr.msgQueue.empty())
    pty_radio.received.clear()

    app.stepButtonGroup.button(2).click()  # 1 kHz
    for click in range(1, 31):
        app.dial.setValue(click)
        time.sleep(0.01)

    final = tune_bytes(0.53, 'AM', 8000)
    wait_until(lambda: pty_radio.commands(b'N')[-1:] == [final])
    assert len(pty_radio.commands(b'N')) < 30
