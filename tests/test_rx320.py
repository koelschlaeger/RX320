import pytest

from fakes import FakeSerial, tune_bytes, wait_until
from RX320.RX320 import RX320
from RX320.RX320_Driver import RX320_Driver


class SpyDriver(RX320_Driver):
    """Records every command in order, without merging or a port."""

    def __init__(self):
        super().__init__('/dev/null')
        self.sent = []

    def _queue_write(self, msg):
        self.sent.append(msg)


@pytest.fixture
def rx():
    radio = RX320()
    radio.sdr = SpyDriver()
    return radio


def test_limits_available_before_connecting():
    radio = RX320()
    assert (radio.MIN_FREQ, radio.MAX_FREQ, radio.SIGNAL_MAX) == (0.5, 30, 10000)


def test_mode_change_retunes_with_new_mode(rx):
    rx.set_vfo(7.2)
    rx.sdr.sent.clear()
    rx.set_mode('USB')
    assert rx.sdr.sent == [b'M1', tune_bytes(7.2, 'USB', 8000)]


def test_filter_change_retunes_with_new_filter(rx):
    rx.set_mode('LSB')
    rx.set_vfo(7.2)
    rx.sdr.sent.clear()
    rx.set_filter(3000)
    assert rx.sdr.sent == [b'W\x0a', tune_bytes(7.2, 'LSB', 3000)]


def test_agc_change_does_not_retune(rx):
    rx.set_agc('Fast')
    assert rx.sdr.sent == [b'G3']


def test_out_of_range_vfo_raises_and_sends_nothing(rx):
    with pytest.raises(ValueError):
        rx.set_vfo(30.5)
    assert rx.sdr.sent == []


@pytest.mark.parametrize('slider, attenuation', [(0, 0), (-40, 26), (-96, 63)])
def test_slider_value_maps_to_attenuation(rx, slider, attenuation):
    rx.set_attenuation(slider, 'Speaker')
    assert rx.sdr.sent == [bytes([ord('V'), 0, attenuation])]


def test_attenuation_formula_matches_original_over_full_range(rx):
    # The original code used the literal factor 0.65625 (= 63/96)
    for slider in range(RX320.MIN_VOLUME, 1):
        rx.sdr.sent.clear()
        rx.set_attenuation(slider, 'Line')
        assert rx.sdr.sent == [bytes([ord('A'), 0, int(-0.65625 * slider)])], slider


def test_invalid_attenuation_target_raises(rx):
    with pytest.raises(IndexError):
        rx.set_attenuation(-10, 'Headphones')


def test_connected_tracks_the_driver():
    radio = RX320()
    assert radio.connected is False
    assert radio.signal_strength is None

    radio.sdr = RX320_Driver('/dev/null')
    radio.sdr.com = FakeSerial()
    radio.sdr.open_serial()
    try:
        assert radio.connected
        wait_until(lambda: radio.signal_strength == 90)

        radio.sdr.com.fail()  # port lost: goes False on its own
        wait_until(lambda: not radio.connected)
        assert radio.signal_strength is None
    finally:
        radio.disconnect()


def test_disconnect_is_safe_any_time():
    radio = RX320()
    radio.disconnect()  # never connected
    radio.connect('/dev/does-not-exist')
    assert not radio.connected
    radio.disconnect()
    radio.disconnect()


def test_measure_signal_requires_a_connection():
    with pytest.raises(ConnectionError):
        RX320().measure_signal(3)


def test_measure_signal_reads_from_the_radio():
    radio = RX320()
    radio.sdr = RX320_Driver('/dev/null')
    radio.sdr.com = FakeSerial()
    radio.sdr.open_serial()
    try:
        assert radio.measure_signal(2, settle=0).result(timeout=3) == [90, 90]
    finally:
        radio.disconnect()
