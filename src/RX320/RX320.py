# -*- coding: utf-8 -*-
"""
Created on Sun May  1 14:58:07 2022

@author: KOelschlaeger
"""
from RX320.RX320_Driver import RX320_Driver
from RX320 import RX320_Data as data


class RX320():
    MODES = tuple(m.name for m in data.MODES)
    _TARGETS = tuple(t.name for t in data.VOLUME_TARGETS)
    AGC_MODES = tuple(m.name for m in data.AGC_MODES)
    FILTERS = tuple(f.bandwidth for f in data.FILTERS)

    # Tuning range (MHz), available before a driver is connected
    MIN_FREQ = data.MINFREQ
    MAX_FREQ = data.MAXFREQ

    # Full-scale signal strength reading (measured on the radio)
    SIGNAL_MAX = data.SIGNAL_MAX
    MIN_VOLUME = -data.ATTENUATION_RANGE_DB      # slider value for mute, in dB

    DEFAULT_MODE = data.DEFAULT_MODE
    DEFAULT_FILTER = data.DEFAULT_FILTER
    DEFAULT_AGC = data.DEFAULT_AGC
    DEFAULT_FREQ = data.DEFAULT_FREQ

    # Current tuning, kept so mode and filter changes can retune
    _mode = DEFAULT_MODE
    _filter = DEFAULT_FILTER
    _freq = DEFAULT_FREQ

    def __init__(self):
        self.sdr = None

    @property
    def connected(self):
        # Live status: goes False on its own if the port is lost
        return self.sdr is not None and self.sdr.is_open()

    @property
    def signal_strength(self):
        # Latest raw reading polled from the radio, or None when not connected
        return self.sdr.rsi if self.connected else None

    def connect(self, port):
        self.sdr = RX320_Driver(port)
        self.sdr.open_serial()

    def disconnect(self):
        # Safe to call at any time, including after the connection was lost
        if self.sdr is not None:
            self.sdr.close_serial()

    def set_attenuation(self, value, target):
        # slider dB [-96, 0] -> attenuation code [63, 0]
        if target not in self._TARGETS:
            raise IndexError()  # Invalid command
        attenuation = int(-value * data.ATTENUATION_MAX / data.ATTENUATION_RANGE_DB)
        self.sdr.set_attenuation(attenuation, target)

    def set_vfo(self, frequency):
        if self.MIN_FREQ <= frequency <= self.MAX_FREQ:
            self._freq = frequency
            self.sdr.set_vfo(self._freq, self._mode, self._filter)
        else:
            # VFO frequency out of range
            raise ValueError()

    def set_agc(self, mode):
        if mode in self.AGC_MODES:
            self.sdr.set_agc(mode)
        else:
            # Invalid command
            raise IndexError()

    def set_filter(self, bandwidth):
        if bandwidth in self.FILTERS:
            self._filter = bandwidth
            self.sdr.set_filter(bandwidth)
            self._retune()
        else:
            #Invalid filter selection
            raise IndexError()

    def set_mode(self, mode):
        if mode in self.MODES:
            self._mode = mode
            self.sdr.set_mode(mode)
            self._retune()
        else:
            # Invalid mode
            raise IndexError()

    def _retune(self):
        # The tuning command encodes mode and filter offsets, so resend it
        # whenever either changes.
        self.sdr.set_vfo(self._freq, self._mode, self._filter)

