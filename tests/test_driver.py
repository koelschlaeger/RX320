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


def test_close_sends_commands_still_queued(running):
    # e.g. the main window restoring AGC and frequency after a scan that the
    # disconnect itself stopped
    running.set_agc('Medium')
    running.set_vfo(14.2, 'AM', 8000)
    running.close_serial()
    assert running.com.commands()[-2:] == [b'G2', tune_bytes(14.2, 'AM', 8000)]


def test_close_during_a_measurement_still_sends_queued_commands(running):
    # Closing ends the measurement, but that isn't a lost port: the worker
    # must go on to send what was queued behind it
    settling = running.measure(1, settle=5)
    running.set_agc('Medium')
    wait_until(settling.running)
    running.close_serial()
    assert isinstance(settling.exception(timeout=1), ConnectionError)
    assert running.com.commands()[-1] == b'G2'


def test_close_gives_up_sending_after_the_timeout(running):
    wait_until(lambda: len(running.com.commands()) >= 3)  # power-up sent
    real_write = running.com.write
    running.com.write = lambda data: (time.sleep(0.2), real_write(data))[1]
    for level in range(20):
        running.set_attenuation(level, 'Speaker')
        running.measure(1)  # keeps the volume commands from merging
    start = time.monotonic()
    running.close_serial(drain_timeout=0.3)
    assert time.monotonic() - start < 1.5
    assert len([c for c in running.com.commands() if c[:1] == b'V']) < 20
    assert not running.queue_thread.is_alive()


def test_lost_port_stops_worker_cleanly(running):
    running.com.fail()
    wait_until(lambda: not running.queue_thread.is_alive())
    assert not running.is_open()
    running.close_serial()  # still safe afterwards


def test_close_after_lost_port_does_not_wait_to_send(running):
    # Nothing can be sent once the port is gone: close must not sit out the
    # drain timeout waiting for a worker that has stopped
    running.com.fail()
    wait_until(lambda: not running.queue_thread.is_alive())
    running.set_agc('Fast')  # queued, but will never be sent
    start = time.monotonic()
    running.close_serial()
    assert time.monotonic() - start < 0.5


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


# --- Measuring signal strength (for scans) ---------------------------------

def test_measurement_is_queued_after_pending_commands(driver):
    driver.set_vfo(7.2, 'USB', 3000)
    future = driver.measure(3, settle=0.1)
    assert [mode for _, mode in driver.msg_queue.queue] == ['W', 'MEASURE']
    assert not future.done()


def test_commands_are_not_merged_across_a_measurement(driver):
    # A measurement must see exactly the settings queued before it, so a
    # later tune may not replace the one waiting ahead of it.
    driver.set_vfo(7.0, 'USB', 3000)
    driver.measure(1)
    driver.set_vfo(7.1, 'USB', 3000)
    assert queued(driver)[0] == tune_bytes(7.0, 'USB', 3000)
    assert queued(driver)[2] == tune_bytes(7.1, 'USB', 3000)


def test_measurement_needs_at_least_one_sample(driver):
    with pytest.raises(ValueError):
        driver.measure(0)


def test_measurement_samples_right_after_the_tune(running):
    running.set_vfo(7.2, 'USB', 3000)
    future = running.measure(3)
    assert future.result(timeout=3) == [90, 90, 90]
    written = running.com.written
    tune = written.index(tune_bytes(7.2, 'USB', 3000) + b'\r')
    assert written[tune + 1:tune + 4] == [b'X\r'] * 3


def test_measurement_waits_the_settle_time(running):
    start = time.monotonic()
    running.measure(1, settle=0.3).result(timeout=3)
    # Allow for the clock: on Windows, time.monotonic() and thread waits
    # follow the ~15.6 ms system tick, so 0.3 s can measure a hair under.
    # Without the settle wait this takes a few ms, far below the bound.
    assert time.monotonic() - start >= 0.25


def test_measurement_updates_the_meter_reading(running):
    running.com.reply = b'X\x01\x00\r'
    assert running.measure(2).result(timeout=3) == [256, 256]
    assert running.rsi == 256


def test_measurement_skips_garbled_replies(running):
    running.com.reply = b'Z\r\x00\x00'
    assert running.measure(3).result(timeout=3) == []


def test_close_ends_running_and_waiting_measurements(running):
    settling = running.measure(1, settle=5)
    waiting = running.measure(1)
    wait_until(lambda: settling.running())
    start = time.monotonic()
    running.close_serial()
    assert time.monotonic() - start < 1  # the settle wait is interrupted
    assert isinstance(settling.exception(timeout=1), ConnectionError)
    assert waiting.cancelled()


def test_lost_port_ends_measurements(running):
    settling = running.measure(1, settle=0.3)
    waiting = running.measure(1)   # queued behind it when the port dies
    wait_until(settling.running)
    running.com.fail()
    assert isinstance(settling.exception(timeout=3), OSError)
    wait_until(waiting.done)
    assert waiting.cancelled()
    # The worker has stopped: later requests are cancelled at once
    wait_until(lambda: not running.queue_thread.is_alive())
    assert running.measure(1).cancelled()
