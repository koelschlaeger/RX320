import time

import pytest

from fakes import FakeSerial, tune_bytes, wait_until
from RX320.RX320_Driver import RX320_Driver

# Known-good command bytes (without the trailing '\r'), verified against
# the driver as it was before the 2026 cleanup. Locks the protocol.
GOLDEN = [
    ('set_vfo', (0.5, 'AM', 8000), '4e47170011821a'),
    ('set_vfo', (7.2, 'USB', 3000), '4e519000066771'),
    ('set_vfo', (14.074, 'LSB', 2400), '4e5c4c0012643e'),
    ('set_vfo', (29.9999, 'CW', 300, 800), '4e752f00006193'),
    ('set_filter', (300,), '5720'),
    ('set_filter', (3000,), '570a'),
    ('set_filter', (8000,), '5721'),
    ('set_mode', ('AM',), '4d30'),
    ('set_mode', ('USB',), '4d31'),
    ('set_mode', ('LSB',), '4d32'),
    ('set_mode', ('CW',), '4d33'),
    ('set_agc', ('Slow',), '4731'),
    ('set_agc', ('Medium',), '4732'),
    ('set_agc', ('Fast',), '4733'),
    ('set_attenuation', (0, 'Line'), '410000'),
    ('set_attenuation', (63, 'Speaker'), '56003f'),
    ('set_attenuation', (20, 'Both'), '430014'),
]


def queued(driver):
    return [msg for msg, _ in driver.msg_queue.queue]


@pytest.fixture
def driver():
    return RX320_Driver('/dev/null')  # never opened


@pytest.fixture
def running():
    """A driver whose worker thread runs against an in-memory port."""
    d = RX320_Driver('/dev/null')
    d.com = FakeSerial()
    assert d.open_serial()
    yield d
    d.close_serial()


@pytest.mark.parametrize('method, args, expected', GOLDEN)
def test_command_bytes(driver, method, args, expected):
    getattr(driver, method)(*args)
    assert queued(driver) == [bytes.fromhex(expected)]


@pytest.mark.parametrize('method, args', [
    ('set_filter', (1234,)),
    ('set_mode', ('FM',)),
    ('set_agc', ('Turbo',)),
    ('set_attenuation', (64, 'Line')),
    ('set_attenuation', (-1, 'Line')),
])
def test_invalid_values_are_rejected(driver, method, args):
    assert getattr(driver, method)(*args) is False
    assert queued(driver) == []


# --- Merging of queued commands -------------------------------------------

def test_newer_setting_replaces_a_waiting_one(driver):
    for freq in (7.0, 7.1, 7.2):
        driver.set_vfo(freq, 'USB', 3000)
    assert queued(driver) == [tune_bytes(7.2, 'USB', 3000)]


def test_replacement_keeps_queue_order(driver):
    # Volume must stay last (the manual's power-up rule), even when an
    # earlier tune is replaced afterwards.
    driver.set_vfo(7.0, 'USB', 3000)
    driver.set_attenuation(10, 'Speaker')
    driver.set_vfo(7.2, 'USB', 3000)
    assert queued(driver) == [tune_bytes(7.2, 'USB', 3000), b'V\x00\x0a']


def test_different_kinds_are_not_merged(driver):
    driver.set_attenuation(10, 'Line')
    driver.set_attenuation(20, 'Speaker')
    driver.set_mode('USB')
    driver.set_agc('Fast')
    assert queued(driver) == [b'A\x00\x0a', b'V\x00\x14', b'M1', b'G3']


def test_both_volume_supersedes_waiting_line_and_speaker(driver):
    # 'C' sets both outputs, so it replaces any waiting A, V or C, taking the
    # place of the first. Otherwise a waiting A could be sent after the newer
    # C and leave the line output at the older level.
    driver.set_attenuation(10, 'Both')
    driver.set_attenuation(20, 'Line')
    driver.set_mode('USB')
    driver.set_attenuation(30, 'Speaker')
    driver.set_attenuation(40, 'Both')
    assert queued(driver) == [b'C\x00\x28', b'M1']


def test_line_or_speaker_after_both_is_kept(driver):
    driver.set_attenuation(40, 'Both')
    driver.set_attenuation(20, 'Line')
    assert queued(driver) == [b'C\x00\x28', b'A\x00\x14']


def test_signal_polls_are_not_merged(driver):
    driver.get_signal_strength()
    driver.get_signal_strength()
    assert list(driver.msg_queue.queue) == [(b'X', 'RW'), (b'X', 'RW')]


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
    assert driver._command_read_write(b'X') == expected


def test_stale_input_is_discarded_before_a_poll(driver):
    driver.com = FakeSerial()
    driver.com.feed(b'DSP START\r')
    assert driver._command_read_write(b'X') == 90


# --- Worker thread ---------------------------------------------------------

def test_open_programs_the_radio_muted(running):
    wait_until(lambda: len(running.com.commands()) >= 3)
    assert running.com.commands()[:3] == [
        tune_bytes(0.5, 'AM', 8000), b'W\x21', b'C\x00\x3f']


def test_worker_sends_commands_and_polls_signal(running):
    running.set_mode('LSB')
    wait_until(lambda: b'M2' in running.com.commands())
    wait_until(lambda: running.rsi == 90)
    assert running.is_open()


def test_close_stops_worker_and_port(running):
    running.close_serial()
    assert not running.queue_thread.is_alive()
    assert not running.com.is_open
    assert not running.is_open()


def test_lost_port_stops_worker_cleanly(running):
    running.com.fail()
    wait_until(lambda: not running.queue_thread.is_alive())
    assert not running.is_open()
    running.close_serial()  # still safe afterwards


def test_open_twice_keeps_one_worker(running):
    worker = running.queue_thread
    wait_until(lambda: len(running.com.commands()) >= 3)  # power-up sent
    assert running.open_serial() is True
    assert running.queue_thread is worker
    time.sleep(0.3)
    power_up_tune = tune_bytes(0.5, 'AM', 8000)
    assert running.com.commands().count(power_up_tune) == 1  # not re-sent


def test_open_failure_returns_false():
    d = RX320_Driver('/dev/does-not-exist')
    assert d.open_serial() is False
    assert not d.is_open()
