import os

import pytest
from PyQt6.QtCore import QSettings

from conftest import FAKE_PORTS, TEST_CONFIG_DIR
from fakes import FakeRadio
from gui.main_window import SETTINGS_SCOPE


def test_settings_stay_out_of_real_config():
    path = QSettings(*SETTINGS_SCOPE).fileName()
    assert path.startswith(TEST_CONFIG_DIR)


def test_defaults_without_saved_settings(window):
    assert window.comboBoxSerialPort.currentText() == FAKE_PORTS[0]
    assert window.spinBoxVFOA.value() == 0.5
    assert window.labelMode_Act.text() == 'AM'
    assert window.labelAGC_Act.text() == 'Medium'
    assert window.labelBW_Act.text() == '8000'
    assert window.stepButtonGroup.checkedButton().text() == '5 kHz'


@pytest.fixture
def saved_session(make_window):
    """Run a session that changes everything, then close it."""
    radio = FakeRadio()
    window = make_window(radio)
    window.resize(700, 400)
    window.comboBoxSerialPort.setCurrentText(FAKE_PORTS[1])
    window._connect()
    window.spinBoxVFOA.setValue(7.2)
    window.on_vfo_store()
    window.spinBoxVFOA.setValue(14.074)
    window.modeButtonGroup.button(2).click()   # LSB
    window.agcButtonGroup.button(0).click()    # Slow
    window.stepButtonGroup.button(1).click()   # 100 Hz
    window.sliderBW.setValue(22)               # 3000 Hz
    window.sliderVol.setValue(-20)
    window.checkBoxLink.setChecked(True)
    window.close()


def test_settings_restored_next_session(saved_session, make_window):
    radio = FakeRadio()
    window = make_window(radio)
    assert window.comboBoxSerialPort.currentText() == FAKE_PORTS[1]
    assert window.spinBoxVFOA.value() == pytest.approx(14.074)
    assert window.spinBoxVFOB.value() == pytest.approx(7.2)
    assert window.labelMode_Act.text() == 'LSB'
    assert window.labelAGC_Act.text() == 'Slow'
    assert window.labelBW_Act.text() == '3000'
    assert window.stepButtonGroup.checkedButton().text() == '100 Hz'
    assert window.spinBoxVFOA.singleStep() == pytest.approx(0.0001)
    assert window.checkBoxLink.isChecked()
    assert (window.width(), window.height()) == (700, 400)


def test_volume_is_never_restored(saved_session, make_window):
    window = make_window(FakeRadio())
    assert window.sliderLine.value() == window.sliderVol.value() == -96


def test_restoring_sends_nothing_until_connect(saved_session, make_window):
    radio = FakeRadio()
    window = make_window(radio)
    assert radio.calls == []

    window._connect()
    assert radio.calls == [
        ('connect', FAKE_PORTS[1]),
        ('set_mode', 'LSB'),
        ('set_filter', 3000),
        ('set_agc', 'Slow'),
        ('set_vfo', 14.074),
        ('set_attenuation', -96, 'Line'),
        ('set_attenuation', -96, 'Speaker'),
    ]


def test_corrupted_settings_fall_back_to_defaults(make_window):
    path = QSettings(*SETTINGS_SCOPE).fileName()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write('[audio]\nlink=maybe\n'
                '[radio]\nagc=Turbo\nfilter=abc\nmode=Banana\n'
                '[serial]\nport=/dev/nonexistent\n'
                '[tuning]\nstep=xyz\n'
                '[vfo]\na=hello\nb=999\n'
                '[window]\ngeometry=not-a-geometry\n')

    window = make_window(FakeRadio())  # must not raise
    assert window.comboBoxSerialPort.currentText() == FAKE_PORTS[0]
    assert window.spinBoxVFOA.value() == 0.5
    assert window.spinBoxVFOB.value() == 30  # 999 clamped
    assert window.labelMode_Act.text() == 'AM'
    assert window.labelAGC_Act.text() == 'Medium'
    assert window.labelBW_Act.text() == '8000'
    assert window.stepButtonGroup.checkedButton().text() == '5 kHz'
