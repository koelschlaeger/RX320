# -*- coding: utf-8 -*-
"""
Created on Sun May  1 14:58:07 2022

@author: KOelschlaeger
"""
from RX320.RX320_Driver import RX320_Driver
from RX320 import RX320_Data as data


class RX320():
    Modes = tuple(m.name for m in data.MODES)
    _Target = tuple(t.name for t in data.VOLUME_TARGETS)
    AGCModes = tuple(m.name for m in data.AGC_MODES)
    Filters = tuple(f.bandwidth for f in data.FILTERS)

    # Tuning range (MHz), available before a driver is connected
    MinFreq = data.MINFREQ
    MaxFreq = data.MAXFREQ

    # Full-scale signal strength reading (measured on the radio)
    SignalMax = data.SIGNAL_MAX
    MinVolume = -data.ATTENUATION_RANGE_DB      # slider value for mute, in dB

    DefaultMode = data.DEFAULT_MODE
    DefaultFilter = data.DEFAULT_FILTER
    DefaultAGC = data.DEFAULT_AGC
    DefaultFreq = data.DEFAULT_FREQ

    # Internal state of the radio
    _Mode = DefaultMode
    _Filter = DefaultFilter
    _Freq = DefaultFreq
    _LineAttenuation = data.ATTENUATION_MAX
    _SpeakerAttenuation = data.ATTENUATION_MAX
    _AGC = DefaultAGC

    def __init__(self):
        self.sdr = None

    @property
    def Connected(self):
        # Live status: goes False on its own if the port is lost
        return self.sdr is not None and self.sdr.IsOpen()

    @property
    def SignalStrength(self):
        # Latest raw reading polled from the radio, or None when not connected
        return self.sdr.RSI if self.Connected else None

    def Connect(self, comPort):
        self.sdr = RX320_Driver(comPort)
        self.sdr.OpenSerial()

    def Disconnect(self):
        # Safe to call at any time, including after the connection was lost
        if self.sdr is not None:
            self.sdr.CloseSerial()

    def SetAttenuation(self, Value, Target):
        # slider dB [-96, 0] -> attenuation code [63, 0]
        if Target not in self._Target:
            raise IndexError()  # Invalid command
        attenuation = int(-Value * data.ATTENUATION_MAX / data.ATTENUATION_RANGE_DB)
        if Target in ('Line', 'Both'):
            self._LineAttenuation = attenuation
        if Target in ('Speaker', 'Both'):
            self._SpeakerAttenuation = attenuation
        self.sdr.SetAttenuation(attenuation, Target)

    def SetVFO(self, frequency):
        if self.MinFreq <= frequency <= self.MaxFreq:
            self._Freq = frequency
            self.sdr.SetVFO(self._Freq, self._Mode, self._Filter)
        else:
            # VFO frequency out of range
            raise ValueError()

    def SetAGC(self, Mode):
        if Mode in self.AGCModes:
            self._AGC = Mode
            self.sdr.SetAGC(Mode)
        else:
            # Invalid command
            raise IndexError()

    def SetFilter(self, Bandwidth):
        if Bandwidth in self.Filters:
            self._Filter = Bandwidth
            self.sdr.SetFilter(Bandwidth)
            self._Retune()
        else:
            #Invalid filter selection
            raise IndexError()

    def SetMode(self, Mode):
        if Mode in self.Modes:
            self._Mode = Mode
            self.sdr.SetMode(Mode)
            self._Retune()
        else:
            # Invalid Mode
            raise IndexError()

    def _Retune(self):
        # The tuning command encodes mode and filter offsets, so resend it
        # whenever either changes.
        self.sdr.SetVFO(self._Freq, self._Mode, self._Filter)

