"""Test doubles for the RX320 at three levels: the RX320 wrapper, the
serial port object, and a pseudo-terminal that acts as the physical radio."""

import os
import threading
import time

import serial

from RX320.RX320 import RX320
from RX320.RX320_Driver import RX320_Driver


def wait_until(condition, timeout=3.0):
    """Poll condition() until it is true; fail the test if it never is."""
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError(f'condition not met within {timeout}s')
        time.sleep(0.01)


def tune_bytes(freq, mode, bandwidth):
    """The N command the driver sends for this frequency/mode/filter."""
    driver = RX320_Driver('/dev/null')
    driver.set_vfo(freq, mode, bandwidth)
    return driver.msg_queue.get()[0]


class FakeRadio:
    """Stands in for RX320 in GUI tests: records calls, no serial port."""

    MODES = RX320.MODES
    AGC_MODES = RX320.AGC_MODES
    FILTERS = RX320.FILTERS
    MIN_FREQ = RX320.MIN_FREQ
    MAX_FREQ = RX320.MAX_FREQ
    SIGNAL_MAX = RX320.SIGNAL_MAX
    MIN_VOLUME = RX320.MIN_VOLUME
    DEFAULT_MODE = RX320.DEFAULT_MODE
    DEFAULT_FILTER = RX320.DEFAULT_FILTER
    DEFAULT_AGC = RX320.DEFAULT_AGC
    DEFAULT_FREQ = RX320.DEFAULT_FREQ

    def __init__(self):
        self.calls = []
        self.connected = False       # set False to simulate a lost connection
        self.signal = 0
        self.connect_result = True   # False: port opens but reports failure
        self.connect_error = None    # exception for connect() to raise

    @property
    def signal_strength(self):
        return self.signal if self.connected else None

    def connect(self, port):
        self.calls.append(('connect', port))
        if self.connect_error:
            raise self.connect_error
        self.connected = self.connect_result

    def disconnect(self):
        self.calls.append(('disconnect',))
        self.connected = False

    def set_mode(self, mode):
        self.calls.append(('set_mode', mode))

    def set_filter(self, bandwidth):
        self.calls.append(('set_filter', bandwidth))

    def set_agc(self, agc):
        self.calls.append(('set_agc', agc))

    def set_vfo(self, freq):
        self.calls.append(('set_vfo', round(freq, 6)))

    def set_attenuation(self, value, target):
        self.calls.append(('set_attenuation', value, target))

    def named(self, name):
        """Calls to one method, e.g. named('set_vfo') -> [('set_vfo', 7.2)]."""
        return [c for c in self.calls if c[0] == name]


class FakeSerial:
    """In-memory replacement for serial.Serial, answering signal polls."""

    def __init__(self, reply=b'X\x00\x5a\r'):
        self.is_open = True
        self.reply = reply
        self.written = []
        self.failed = False
        self._rx = bytearray()
        self._lock = threading.Lock()

    def feed(self, data):
        """Bytes arriving from the radio, e.g. stale junk."""
        with self._lock:
            self._rx.extend(data)

    def fail(self):
        """Simulate the port going away (USB unplugged)."""
        self.failed = True

    def write(self, data):
        if self.failed:
            raise serial.SerialException('device disconnected')
        self.written.append(bytes(data))
        if data == b'X\r':
            self.feed(self.reply)
        return len(data)

    @property
    def in_waiting(self):
        if self.failed:
            raise OSError('device disconnected')
        return len(self._rx)

    def read(self, size=1):
        with self._lock:
            data = bytes(self._rx[:size])
            del self._rx[:size]
        return data

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False

    def commands(self):
        """Written commands without the trailing '\\r' and signal polls."""
        return [w[:-1] for w in self.written if w != b'X\r']


# Argument bytes after each command letter (commands end with '\r')
_ARG_LEN = {b'N': 6, b'W': 1, b'A': 2, b'V': 2, b'C': 2, b'M': 1, b'G': 1, b'X': 0}


class PtyRadio:
    """A pseudo-terminal pair acting as the physical radio: the app opens
    .port like a real serial device. Records every command received and
    answers signal-strength polls with .signal."""

    def __init__(self):
        import pty
        self._master, self._slave = pty.openpty()
        self.port = os.ttyname(self._slave)
        self.signal = 90
        self.received = []
        self._buffer = bytearray()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while True:
            try:
                data = os.read(self._master, 256)
            except OSError:
                return
            self._buffer.extend(data)
            self._parse()

    def _parse(self):
        # Parse by length rather than splitting on '\r': tuning factor
        # bytes can themselves be 0x0D.
        while self._buffer:
            letter = bytes(self._buffer[:1])
            size = 1 + _ARG_LEN.get(letter, 0) + 1
            if len(self._buffer) < size:
                return
            command = bytes(self._buffer[:size - 1])
            del self._buffer[:size]
            if letter == b'X':
                try:
                    os.write(self._master, b'X' + self.signal.to_bytes(2, 'big') + b'\r')
                except OSError:
                    return  # unplugged
            else:
                self.received.append(command)

    def commands(self, letter=None):
        return [c for c in self.received if letter is None or c[:1] == letter]

    def unplug(self):
        """Close the radio end; the app's next read or write fails."""
        for fd in (self._master, self._slave):
            try:
                os.close(fd)
            except OSError:
                pass

    close = unplug
