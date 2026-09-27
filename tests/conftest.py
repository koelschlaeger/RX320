import atexit
import os
import shutil
import sys
import tempfile

# Must happen before Qt starts or any QSettings is created:
# - run headless unless a platform is explicitly requested
# - a throwaway folder for settings (see clean_settings). XDG_CONFIG_HOME
#   is an extra guard on Linux only; Qt reads it once.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
TEST_CONFIG_DIR = tempfile.mkdtemp(prefix='rx320-test-config-')
os.environ['XDG_CONFIG_HOME'] = TEST_CONFIG_DIR
atexit.register(shutil.rmtree, TEST_CONFIG_DIR, ignore_errors=True)

import pytest
from PyQt6.QtCore import QSettings

from fakes import FakeRadio, PtyRadio
from gui import main_window
from gui.main_window import MainWindow

# The app's real settings (native storage: registry on Windows, plist on
# macOS, a .conf file on Linux), kept for the test that checks it
REAL_OPEN_SETTINGS = getattr(main_window, 'open_settings', None)
TEST_SETTINGS_FILE = os.path.join(TEST_CONFIG_DIR, 'RX320.ini')

FAKE_PORTS = ['/dev/fake0', '/dev/fake1', '/dev/fake2']
FAKE_PORT_DESCRIPTIONS = {'/dev/fake0': 'FT232R USB UART (FTDI), serial AB0N3GLA',
                          '/dev/fake1': 'Prolific USB-Serial',
                          '/dev/fake2': None}  # e.g. a built-in port


def _test_settings():
    return QSettings(TEST_SETTINGS_FILE, QSettings.Format.IniFormat)


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch):
    """Every test uses a temporary INI file instead of the real settings, on
    every OS, and starts with it empty. Windows are closed (and save their
    settings) before this is undone, so nothing reaches the real settings."""
    monkeypatch.setattr(main_window, 'open_settings', _test_settings)
    _test_settings().clear()
    yield
    _test_settings().clear()


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
    monkeypatch.setattr(main_window, 'get_serial_ports',
                        lambda: [(p, FAKE_PORT_DESCRIPTIONS.get(p)) for p in ports])
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
    assert radio.connected
    radio.calls.clear()
    return window


@pytest.fixture
def pty_radio():
    if sys.platform.startswith('win'):
        pytest.skip('pseudo-terminals are not available on Windows')
    device = PtyRadio()
    yield device
    device.close()
