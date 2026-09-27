import os
from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings

from conftest import FAKE_PORTS, REAL_OPEN_SETTINGS, TEST_CONFIG_DIR
from fakes import FakeRadio
from gui import main_window
from gui.main_window import SETTINGS_SCOPE


def test_settings_stay_out_of_real_config():
    path = Path(main_window.open_settings().fileName()).resolve()
    assert path.is_relative_to(Path(TEST_CONFIG_DIR).resolve())


def test_app_uses_native_settings():
    # Only the tests swap in an INI file; the app keeps the OS's own storage
    settings = REAL_OPEN_SETTINGS()
    assert settings.format() == QSettings.Format.NativeFormat
    assert (settings.organizationName(), settings.applicationName()) == SETTINGS_SCOPE


def test_defaults_without_saved_settings(window):
    assert window.comboBoxSerialPort.currentText() == FAKE_PORTS[0]
    assert window.spinBoxVFOA.value() == 0.5
    assert window.labelMode_Act.text() == 'AM'
    assert window.labelAGC_Act.text() == 'Medium'
    assert window.labelBW_Act.text() == '8000'
    assert window.stepButtonGroup.checkedButton().text() == '5 kHz'


@pytest.fixture
def saved_session(make_window):
    """Run a session that changes everything, then close it. Returns the
    window size it saved, as (default size, saved size)."""
    radio = FakeRadio()
    window = make_window(radio)
    default_size = (window.width(), window.height())
    # Change only the height: the minimum width depends on the platform's
    # fonts and style (about 673 px on Linux, 808 px on Windows), so Qt
    # may not allow a fixed width; the height has room everywhere.
    window.resize(window.width(), window.height() + 60)
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
    saved_size = (window.width(), window.height())
    window.close()
    return default_size, saved_size


def test_settings_restored_next_session(saved_session, make_window):
    default_size, saved_size = saved_session
    assert saved_size != default_size  # the resize really changed something
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
    assert (window.width(), window.height()) == saved_size


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
    path = main_window.open_settings().fileName()
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
