import pytest

from fakes import FakeSerial, tune_bytes, wait_until
from RX320.RX320_Driver import RX320_Driver

# Known-good command bytes (without the trailing '\r'), verified against
# the driver as it was before the 2026 cleanup. Locks the protocol.
GOLDEN = [
    ('SetVFO', (0.5, 'AM', 8000), '4e47170011821a'),
    ('SetVFO', (7.2, 'USB', 3000), '4e519000066771'),
    ('SetVFO', (14.074, 'LSB', 2400), '4e5c4c0012643e'),
    ('SetVFO', (29.9999, 'CW', 300, 800), '4e752f00006193'),
    ('SetFilter', (300,), '5720'),
    ('SetFilter', (3000,), '570a'),
    ('SetFilter', (8000,), '5721'),
    ('SetMode', ('AM',), '4d30'),
    ('SetMode', ('USB',), '4d31'),
    ('SetMode', ('LSB',), '4d32'),
    ('SetMode', ('CW',), '4d33'),
    ('SetAGC', ('Slow',), '4731'),
    ('SetAGC', ('Medium',), '4732'),
    ('SetAGC', ('Fast',), '4733'),
    ('SetAttenuation', (0, 'Line'), '410000'),
    ('SetAttenuation', (63, 'Speaker'), '56003f'),
    ('SetAttenuation', (20, 'Both'), '430014'),
]


def queued(driver):
    return [msg for msg, _ in driver.msgQueue.queue]


@pytest.fixture
def driver():
    return RX320_Driver('/dev/null')  # never opened


@pytest.fixture
def running():
    """A driver whose worker thread runs against an in-memory port."""
    d = RX320_Driver('/dev/null')
    d.com = FakeSerial()
    assert d.OpenSerial()
    yield d
    d.CloseSerial()


@pytest.mark.parametrize('method, args, expected', GOLDEN)
def test_command_bytes(driver, method, args, expected):
    getattr(driver, method)(*args)
    assert queued(driver) == [bytes.fromhex(expected)]


@pytest.mark.parametrize('method, args', [
    ('SetFilter', (1234,)),
    ('SetMode', ('FM',)),
    ('SetAGC', ('Turbo',)),
    ('SetAttenuation', (64, 'Line')),
    ('SetAttenuation', (-1, 'Line')),
])
def test_invalid_values_are_rejected(driver, method, args):
    assert getattr(driver, method)(*args) is False
    assert queued(driver) == []


# --- Merging of queued commands -------------------------------------------

def test_newer_setting_replaces_a_waiting_one(driver):
    for freq in (7.0, 7.1, 7.2):
        driver.SetVFO(freq, 'USB', 3000)
    assert queued(driver) == [tune_bytes(7.2, 'USB', 3000)]


def test_replacement_keeps_queue_order(driver):
    # Volume must stay last (the manual's power-up rule), even when an
    # earlier tune is replaced afterwards.
    driver.SetVFO(7.0, 'USB', 3000)
    driver.SetAttenuation(10, 'Speaker')
    driver.SetVFO(7.2, 'USB', 3000)
    assert queued(driver) == [tune_bytes(7.2, 'USB', 3000), b'V\x00\x0a']


def test_different_kinds_are_not_merged(driver):
    driver.SetAttenuation(10, 'Line')
    driver.SetAttenuation(20, 'Speaker')
    driver.SetMode('USB')
    driver.SetAGC('Fast')
    assert queued(driver) == [b'A\x00\x0a', b'V\x00\x14', b'M1', b'G3']


def test_signal_polls_are_not_merged(driver):
    driver.GetSignalStrength()
    driver.GetSignalStrength()
    assert list(driver.msgQueue.queue) == [(b'X', 'RW'), (b'X', 'RW')]


# --- Reading signal-strength replies --------------------------------------

@pytest.mark.parametrize('reply, expected', [
    (b'X\x00\x5a\r', 90),
    (b'X\x27\x10\r', 10000),
    (b'X\x00', None),            # too short (timeout)
    (b'Z\r\x00\x00', None),      # radio didn't recognise the command
    (b'X\x00\x5aQ', None),       # missing '\r'
])
def test_signal_reply_parsing(driver, reply, expected):
    driver.com = FakeSerial(reply=reply)
    assert driver._CommandReadWrite(b'X') == expected


def test_stale_input_is_discarded_before_a_poll(driver):
    driver.com = FakeSerial()
    driver.com.feed(b'DSP START\r')
    assert driver._CommandReadWrite(b'X') == 90


# --- Worker thread ---------------------------------------------------------

def test_open_programs_the_radio_muted(running):
    wait_until(lambda: len(running.com.commands()) >= 3)
    assert running.com.commands()[:3] == [
        tune_bytes(0.5, 'AM', 8000), b'W\x21', b'C\x00\x3f']


def test_worker_sends_commands_and_polls_signal(running):
    running.SetMode('LSB')
    wait_until(lambda: b'M2' in running.com.commands())
    wait_until(lambda: running.RSI == 90)
    assert running.IsOpen()


def test_close_stops_worker_and_port(running):
    running.CloseSerial()
    assert not running.queueThread.is_alive()
    assert not running.com.is_open
    assert not running.IsOpen()


def test_lost_port_stops_worker_cleanly(running):
    running.com.fail()
    wait_until(lambda: not running.queueThread.is_alive())
    assert not running.IsOpen()
    running.CloseSerial()  # still safe afterwards


def test_open_failure_returns_false():
    d = RX320_Driver('/dev/does-not-exist')
    assert d.OpenSerial() is False
    assert not d.IsOpen()
