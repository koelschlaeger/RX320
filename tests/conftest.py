import atexit
import os
import shutil
import sys
import tempfile

# Must happen before Qt starts or any QSettings is created:
# - run headless unless a platform is explicitly requested
# - keep settings out of the real ~/.config (Qt reads this path once)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
TEST_CONFIG_DIR = tempfile.mkdtemp(prefix='rx320-test-config-')
os.environ['XDG_CONFIG_HOME'] = TEST_CONFIG_DIR
atexit.register(shutil.rmtree, TEST_CONFIG_DIR, ignore_errors=True)

import pytest
from PyQt6.QtCore import QSettings

from fakes import FakeRadio, PtyRadio
from gui import main_window
from gui.main_window import SETTINGS_SCOPE, MainWindow

FAKE_PORTS = ['/dev/fake0', '/dev/fake1']


@pytest.fixture(autouse=True)
def clean_settings():
    """Every test starts with no saved settings."""
    QSettings(*SETTINGS_SCOPE).clear()
    yield
    QSettings(*SETTINGS_SCOPE).clear()


@pytest.fixture(autouse=True)
def dialogs(monkeypatch):
    """Record message boxes instead of showing them (a real one would
    block the test run). Returns the list of (kind, title) shown."""
    shown = []
    for kind in ('warning', 'critical', 'information'):
        monkeypatch.setattr(main_window.QMessageBox, kind,
                            lambda parent, title, text, kind=kind: shown.append((kind, title)))
    return shown


@pytest.fixture(autouse=True)
def fake_ports(monkeypatch):
    """Port list that doesn't depend on what's plugged into this machine."""
    ports = list(FAKE_PORTS)
    monkeypatch.setattr(main_window, 'get_serial_ports', lambda: list(ports))
    return ports


@pytest.fixture
def radio():
    return FakeRadio()


@pytest.fixture
def make_window(qtbot):
    """Create (and on teardown close) MainWindows on a given radio."""
    def make(sdr):
        window = MainWindow(sdr)
        qtbot.addWidget(window)
        window.show()
        return window
    return make


@pytest.fixture
def window(make_window, radio):
    return make_window(radio)


@pytest.fixture
def connected(window, radio):
    """A window connected to the fake radio, with the connect-time sync
    calls cleared so tests see only what they trigger."""
    window._connect()
    assert radio.Connected
    radio.calls.clear()
    return window


@pytest.fixture
def pty_radio():
    if sys.platform.startswith('win'):
        pytest.skip('pseudo-terminals are not available on Windows')
    device = PtyRadio()
    yield device
    device.close()
