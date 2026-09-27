import pytest

from fakes import FakeSerial, tune_bytes, wait_until
from RX320.RX320 import RX320
from RX320.RX320_Driver import RX320_Driver


class SpyDriver(RX320_Driver):
    """Records every command in order, without merging or a port."""

    def __init__(self):
        super().__init__('/dev/null')
        self.sent = []

    def _QueueWrite(self, msg):
        self.sent.append(msg)


@pytest.fixture
def rx():
    radio = RX320()
    radio.sdr = SpyDriver()
    return radio


def test_limits_available_before_connecting():
    radio = RX320()
    assert (radio.MinFreq, radio.MaxFreq, radio.SignalMax) == (0.5, 30, 10000)


def test_mode_change_retunes_with_new_mode(rx):
    rx.SetVFO(7.2)
    rx.sdr.sent.clear()
    rx.SetMode('USB')
    assert rx.sdr.sent == [b'M1', tune_bytes(7.2, 'USB', 8000)]


def test_filter_change_retunes_with_new_filter(rx):
    rx.SetMode('LSB')
    rx.SetVFO(7.2)
    rx.sdr.sent.clear()
    rx.SetFilter(3000)
    assert rx.sdr.sent == [b'W\x0a', tune_bytes(7.2, 'LSB', 3000)]


def test_agc_change_does_not_retune(rx):
    rx.SetAGC('Fast')
    assert rx.sdr.sent == [b'G3']


def test_out_of_range_vfo_raises_and_sends_nothing(rx):
    with pytest.raises(ValueError):
        rx.SetVFO(30.5)
    assert rx.sdr.sent == []


@pytest.mark.parametrize('slider, attenuation', [(0, 0), (-40, 26), (-96, 63)])
def test_slider_value_maps_to_attenuation(rx, slider, attenuation):
    rx.SetAttenuation(slider, 'Speaker')
    assert rx.sdr.sent == [bytes([ord('V'), 0, attenuation])]


def test_invalid_attenuation_target_raises(rx):
    with pytest.raises(IndexError):
        rx.SetAttenuation(-10, 'Headphones')


def test_connected_tracks_the_driver():
    radio = RX320()
    assert radio.Connected is False
    assert radio.SignalStrength is None

    radio.sdr = RX320_Driver('/dev/null')
    radio.sdr.com = FakeSerial()
    radio.sdr.OpenSerial()
    try:
        assert radio.Connected
        wait_until(lambda: radio.SignalStrength == 90)

        radio.sdr.com.fail()  # port lost: goes False on its own
        wait_until(lambda: not radio.Connected)
        assert radio.SignalStrength is None
    finally:
        radio.Disconnect()


def test_disconnect_is_safe_any_time():
    radio = RX320()
    radio.Disconnect()  # never connected
    radio.Connect('/dev/does-not-exist')
    assert not radio.Connected
    radio.Disconnect()
    radio.Disconnect()
