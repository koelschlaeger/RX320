# -*- coding: utf-8 -*-
"""
Created on Sun May  1 14:58:07 2022

@author: KOelschlaeger
"""
from RX320.RX320_Driver import RX320_Driver


class RX320():
    Modes = ('AM', 'LSB', 'USB', 'CW')
    Target = ('Line', 'Speaker', 'Both')
    AGCModes = ('Slow', 'Medium', 'Fast')

    Filters = (300, 330, 375, 450, 525, 600, 675, 750, 900, 1050, 1200,
               1350, 1500, 1650, 1800, 1950, 2100, 2250, 2400, 2550, 2700, 2850,
               3000, 3300, 3600, 3900, 4200, 4500, 4800, 5100, 5400, 5700, 6000, 8000)

    # Tuning range (MHz), available before a driver is connected
    MinFreq = RX320_Driver.MinFreq
    MaxFreq = RX320_Driver.MaxFreq

    Mode = 'AM'                # AM
    Filter = 8000              # 8kHz
    Freq = 0.5                 # 500kHz
    LineAttenuation = 63       # Mute
    SpeakerAttenuation = 63    # Mute
    AGC = 'Medium'             # 'Medium'

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
        # Remap [0, -96] to [0, 63]
        # Attenuation is from 0 to 63 -> 0 to 96dB (1.5dB/step)
        # Magic number is 63/-96 = -0.65625
        attenuation = int(-0.65625 * Value)
        if Target == 'Both':
            self.LineAttenuation = attenuation
            self.SpeakerAttenuation = attenuation
            self.sdr.SetAttenuation(attenuation, 'Both')
        elif Target == 'Line':
            self.LineAttenuation = attenuation
            self.sdr.SetAttenuation(attenuation, 'Line')
        elif Target == 'Speaker':
            self.SpeakerAttenuation = attenuation
            self.sdr.SetAttenuation(attenuation, 'Speaker')
        else:
            # Invalid command
            raise IndexError()

    def SetVFO(self, frequency):
        if self.MinFreq <= frequency <= self.MaxFreq:
            self.Freq = frequency
            self.sdr.SetVFO(self.Freq, self.Mode, self.Filter)
        else:
            # VFO frequency out of range
            raise ValueError()

    def SetAGC(self, Mode):
        if Mode in self.sdr.AGC:
            self.AGC = Mode
            self.sdr.SetAGC(Mode)
        else:
            # Invalid command
            raise IndexError()

    def SetFilter(self, Bandwidth):
        if Bandwidth in self.sdr.FILTERS:
            self.Filter = Bandwidth
            self.sdr.SetFilter(Bandwidth)
            self._Retune()
        else:
            #Invalid filter selection
            raise IndexError()

    def SetMode(self, Mode):
        if Mode in self.sdr.MODES:
            self.Mode = Mode
            self.sdr.SetMode(Mode)
            self._Retune()
        else:
            # Invalid Mode
            raise IndexError()

    def _Retune(self):
        # The tuning command encodes mode and filter offsets, so resend it
        # whenever either changes.
        self.sdr.SetVFO(self.Freq, self.Mode, self.Filter)

