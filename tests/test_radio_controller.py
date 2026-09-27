from gui.radio_controller import RadioController


class Sdr:
    MinFreq = 0.5
    MaxFreq = 30
    DefaultFreq = 0.5

    def __init__(self):
        self.tuned = []

    def SetVFO(self, freq):
        self.tuned.append(freq)


def make():
    sdr = Sdr()
    return RadioController(sdr), sdr


def test_starts_at_500_khz():
    radio, _ = make()
    assert (radio.vfo_a, radio.vfo_b) == (0.5, 0.5)


def test_set_vfo_a_tunes_the_radio():
    radio, sdr = make()
    assert radio.set_vfo_a(7.2) == 7.2
    assert sdr.tuned == [7.2]


def test_set_vfo_a_clamps_to_tuning_range():
    radio, sdr = make()
    assert radio.set_vfo_a(99) == 30
    assert radio.set_vfo_a(0.1) == 0.5
    assert sdr.tuned == [30, 0.5]


def test_step_is_relative_and_clamped():
    radio, _ = make()
    radio.set_vfo_a(7.2)
    assert radio.step_vfo_a(0.005) == 7.205
    assert radio.step_vfo_a(-100) == 0.5


def test_store_copies_a_to_b_without_tuning():
    radio, sdr = make()
    radio.set_vfo_a(7.2)
    sdr.tuned.clear()
    assert radio.store_a_to_b() == 7.2
    assert radio.vfo_b == 7.2
    assert sdr.tuned == []


def test_swap_exchanges_and_tunes_to_new_a():
    radio, sdr = make()
    radio.set_vfo_a(7.2)
    radio.store_a_to_b()
    radio.set_vfo_a(14.1)
    sdr.tuned.clear()
    assert radio.swap_vfo() == (7.2, 14.1)
    assert sdr.tuned == [7.2]


def test_restore_clamps_and_sends_nothing():
    radio, sdr = make()
    radio.restore(99, 0.1)
    assert (radio.vfo_a, radio.vfo_b) == (30, 0.5)
    assert sdr.tuned == []
