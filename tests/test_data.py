"""Consistency checks on the radio's data tables (RX320_Data)."""

import dataclasses

import pytest

from RX320 import RX320_Data as data
from RX320.RX320 import RX320


def test_filters_cover_all_34_codes_in_bandwidth_order():
    bandwidths = [f.bandwidth for f in data.FILTERS]
    assert len(bandwidths) == 34
    assert bandwidths == sorted(bandwidths)
    assert all(f.command[:1] == b'W' for f in data.FILTERS)
    assert sorted(f.command[1] for f in data.FILTERS) == list(range(0x22))


@pytest.mark.parametrize('table', [data.MODES, data.AGC_MODES, data.VOLUME_TARGETS])
def test_names_and_commands_are_unique(table):
    assert len({row.name for row in table}) == len(table)
    assert len({row.command for row in table}) == len(table)


def test_mode_corrections():
    corrections = {m.name: m.correction for m in data.MODES}
    assert corrections == {'AM': 0, 'USB': 1, 'LSB': -1, 'CW': -1}


def test_tables_are_read_only():
    with pytest.raises(dataclasses.FrozenInstanceError):
        data.MODES[0].command = b'M9'


def test_wrapper_names_come_from_the_tables():
    assert RX320.Modes == tuple(m.name for m in data.MODES)
    assert RX320.AGCModes == tuple(a.name for a in data.AGC_MODES)
    assert RX320.Filters == tuple(f.bandwidth for f in data.FILTERS)
    assert (RX320.MinFreq, RX320.MaxFreq) == (data.MINFREQ, data.MAXFREQ)
