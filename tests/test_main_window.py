import pytest
import serial
from PyQt6.QtCore import QLocale, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QPushButton

from conftest import FAKE_PORTS


def button(window, text):
    [btn] = [b for b in window.findChildren(QPushButton) if b.text() == text]
    return btn


def vfo_button(window, row, column=0):
    # Step arrows are rows 0-3 (up x10, up, down, down x10); A->B and A/B
    # are on row 4.
    return window.vfoGroupBox.layout().itemAtPosition(row, column).widget()


def type_into(widget, text):
    widget.setFocus()
    widget.selectAll()
    QTest.keyClicks(widget, text)
    QTest.keyClick(widget, Qt.Key.Key_Return)


# --- Connecting --------------------------------------------------------------

def test_starts_disconnected(window):
    assert not window.modeGroupBox.isEnabled()
    assert not window.spinBoxVFOA.isEnabled()
    assert window.labelConnection.text() == 'Disconnected'
    assert not window.progressBarSignal.isVisible()


def test_connect_syncs_radio_with_volume_last(window, radio):
    button(window, 'Connect').click()
    assert radio.calls == [
        ('connect', FAKE_PORTS[0]),
        ('set_mode', 'AM'),
        ('set_filter', 8000),
        ('set_agc', 'Medium'),
        ('set_vfo', 0.5),
        ('set_attenuation', -96, 'Line'),
        ('set_attenuation', -96, 'Speaker'),
    ]
    assert window.modeGroupBox.isEnabled()
    assert window.labelConnection.text() == f'Connected: {FAKE_PORTS[0]}'
    assert window.progressBarSignal.isVisible()


def test_connect_without_a_port_warns(window, radio, dialogs):
    window.comboBoxSerialPort.clear()
    button(window, 'Connect').click()
    assert dialogs == [('warning', 'No port selected')]
    assert radio.calls == []


def test_failed_open_keeps_controls_disabled(window, radio, dialogs):
    radio.connect_result = False
    button(window, 'Connect').click()
    assert dialogs == [('critical', 'Connection failed')]
    assert not window.modeGroupBox.isEnabled()


def test_connect_exception_is_reported(window, radio, dialogs):
    radio.connect_error = serial.SerialException('busy')
    button(window, 'Connect').click()
    assert dialogs == [('critical', 'Connection failed')]
    assert not window.modeGroupBox.isEnabled()


def test_disconnect_button(connected, radio):
    button(connected, 'Disconnect').click()
    assert radio.calls == [('disconnect',)]
    assert not connected.modeGroupBox.isEnabled()
    assert connected.labelConnection.text() == 'Disconnected'


def test_lost_connection_is_detected(qtbot, connected, radio, dialogs):
    radio.connected = False  # e.g. USB unplugged
    qtbot.waitUntil(lambda: connected.labelConnection.text() == 'Connection lost')
    assert dialogs == [('warning', 'Connection lost')]
    assert ('disconnect',) in radio.calls
    assert not connected.modeGroupBox.isEnabled()
    assert not connected.progressBarSignal.isVisible()


# --- Signal meter ------------------------------------------------------------

@pytest.mark.parametrize('reading, shown', [(0, 0), (4321, 4321), (10000, 10000), (65535, 10000)])
def test_signal_meter(qtbot, connected, radio, reading, shown):
    radio.signal = reading
    qtbot.waitUntil(lambda: connected.progressBarSignal.value() == shown)


# --- Mode, AGC, filter ---------------------------------------------------------

def test_initial_settings_come_from_the_radio(make_window, radio):
    radio.DEFAULT_MODE = 'LSB'
    radio.DEFAULT_AGC = 'Fast'
    radio.DEFAULT_FILTER = 3000
    radio.DEFAULT_FREQ = 7.2
    radio.MIN_VOLUME = -48
    window = make_window(radio)
    assert window.labelMode_Act.text() == 'LSB'
    assert window.labelAGC_Act.text() == 'Fast'
    assert window.labelBW_Act.text() == '3000'
    assert window.spinBoxVFOA.value() == pytest.approx(7.2)
    assert window.sliderVol.minimum() == window.sliderVol.value() == -48
    button(window, 'Mute').setEnabled(True)
    window.sliderVol.setValue(-10)
    button(window, 'Mute').click()
    assert window.sliderVol.value() == -48


def test_mode_button_order(window):
    labels = [b.text() for b in window.modeButtonGroup.buttons()]
    assert labels == ['AM', 'USB', 'LSB', 'CW']


def test_mode_click(connected, radio):
    connected.modeButtonGroup.button(1).click()
    assert radio.calls == [('set_mode', 'USB')]
    assert connected.labelMode_Act.text() == 'USB'


def test_agc_click(connected, radio):
    connected.agcButtonGroup.button(2).click()
    assert radio.calls == [('set_agc', 'Fast')]
    assert connected.labelAGC_Act.text() == 'Fast'


def test_bandwidth_drag_sends_only_on_release(connected, radio):
    slider = connected.sliderBW
    slider.setSliderDown(True)
    for position in range(33, 9, -1):
        slider.setSliderPosition(position)
    assert radio.calls == []
    assert connected.labelBW_Act.text() == '1200'  # label follows the drag
    slider.setSliderDown(False)
    assert radio.calls == [('set_filter', 1200)]


def test_bandwidth_keyboard_step_sends_immediately(connected, radio):
    connected.sliderBW.triggerAction(connected.sliderBW.SliderAction.SliderSingleStepSub)
    assert radio.calls == [('set_filter', 6000)]


# --- Tuning --------------------------------------------------------------------

def test_step_labels_come_from_tuning_steps(window):
    labels = [b.text() for b in window.stepButtonGroup.buttons()]
    assert labels == ['10 Hz', '100 Hz', '1 kHz', '5 kHz', '10 kHz']


def test_dial_tunes_by_step(connected, radio):
    connected.stepButtonGroup.button(2).click()  # 1 kHz
    connected.dial.setValue(3)
    assert radio.calls == [('set_vfo', 0.503)]
    assert connected.spinBoxVFOA.value() == pytest.approx(0.503)


def test_dial_wraparound_keeps_direction(connected, radio):
    connected.stepButtonGroup.button(2).click()  # 1 kHz
    connected.dial.setValue(99)
    radio.calls.clear()
    connected.dial.setValue(-98)  # past the end stop: +3 clicks, not -197
    assert radio.calls == [('set_vfo', 0.602)]


@pytest.mark.parametrize('row, expected', [(0, 0.55), (1, 0.505), (2, 0.5), (3, 0.5)])
def test_step_buttons(connected, radio, row, expected):
    # At 5 kHz from 0.5 MHz; downward steps clamp at the 0.5 MHz minimum
    vfo_button(connected, row).click()
    assert radio.calls == [('set_vfo', expected)]


def test_store_and_swap(connected, radio):
    connected.spinBoxVFOA.setValue(7.2)
    vfo_button(connected, 4, 0).click()  # A -> B
    connected.spinBoxVFOA.setValue(14.1)
    radio.calls.clear()
    vfo_button(connected, 4, 2).click()  # A / B
    assert radio.calls == [('set_vfo', 7.2)]
    assert connected.spinBoxVFOA.value() == pytest.approx(7.2)
    assert connected.spinBoxVFOB.value() == pytest.approx(14.1)


def test_spin_box_arrows_follow_step(connected, radio):
    connected.stepButtonGroup.button(0).click()  # 10 Hz
    connected.spinBoxVFOA.stepBy(3)
    assert radio.calls == [('set_vfo', 0.50003)]


def test_typing_sends_only_on_enter(connected, radio):
    spin = connected.spinBoxVFOA
    spin.setFocus()
    spin.selectAll()
    QTest.keyClicks(spin, '7.3')
    assert radio.calls == []
    QTest.keyClick(spin, Qt.Key.Key_Return)
    assert radio.calls == [('set_vfo', 7.3)]


def test_spin_box_limited_to_tuning_range(connected):
    connected.spinBoxVFOA.setValue(50)
    assert connected.spinBoxVFOA.value() == 30


def test_display_updates_do_not_retune_twice(connected, radio):
    connected.dial.setValue(1)
    vfo_button(connected, 1).click()
    assert len(radio.named('set_vfo')) == 2  # one per action


@pytest.fixture
def german_locale():
    previous = QLocale()
    QLocale.setDefault(QLocale('de_DE'))
    yield
    QLocale.setDefault(previous)


def test_decimal_comma_locale(german_locale, make_window, radio):
    window = make_window(radio)
    window._connect()
    radio.calls.clear()
    type_into(window.spinBoxVFOA, '7,3')
    assert radio.calls == [('set_vfo', 7.3)]


# --- Audio ---------------------------------------------------------------------

def test_linked_volume_moves_both(connected, radio):
    connected.checkBoxLink.setChecked(True)
    radio.calls.clear()
    connected.sliderVol.setValue(-20)
    assert connected.sliderLine.value() == -20
    assert ('set_attenuation', -20, 'Line') in radio.calls
    assert ('set_attenuation', -20, 'Speaker') in radio.calls


def test_linking_equalizes_to_the_quieter_level(connected):
    connected.sliderLine.setValue(-40)
    connected.sliderVol.setValue(-20)
    connected.checkBoxLink.setChecked(True)
    assert connected.sliderLine.value() == connected.sliderVol.value() == -40


def test_mute(connected, radio):
    connected.sliderLine.setValue(-10)
    connected.sliderVol.setValue(-10)
    radio.calls.clear()
    button(connected, 'Mute').click()
    assert radio.calls == [('set_attenuation', -96, 'Line'), ('set_attenuation', -96, 'Speaker')]


# --- Closing -------------------------------------------------------------------

def test_quit_disconnects(connected, radio):
    button(connected, 'Quit').click()
    assert not connected.isVisible()
    assert ('disconnect',) in radio.calls
    assert not connected.statusTimer.isActive()


def test_window_close_disconnects(connected, radio):
    connected.close()
    assert ('disconnect',) in radio.calls


def test_escape_does_not_quit(connected):
    QTest.keyClick(connected, Qt.Key.Key_Escape)
    assert connected.isVisible()
