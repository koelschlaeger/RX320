# -*- coding: utf-8 -*-
"""
Created on Sun May  1 14:58:07 2022

@author: KOelschlaeger
"""
from RX320.RX320 import *
# import RX320.MODES as MODES
# import RX320.AGC as AGC
# import RX320.FILTERS as FILTERS

class MySDR(): # was SDR but apparently that is a namespace collision!?!
    Mode = 'AM'                # AM
    Filter = 8000              # 8kHz
    Freq = 0.5                 # 500kHz
    LineAttenuation = 63       # Mute
    SpeakerAttenuation = 63    # Mute
    AGC = 'Medium'             # 'Medium'
    Connected = False
    
    def __init__(self):
        self.Connected = False
        
    def Connect(self, comPort='/dev/cu.usbserial-AB0N3GLA'):
        self.sdr = RX320(comPort)
        self.Connected = self.sdr.OpenSerial()
        
    def Disconnect(self):
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
        if frequency >= self.sdr.MinFreq and frequency <= self.sdr.MaxFreq:
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
        else:
            #Invalid filter selection
            raise IndexError()
    
    def SetMode(self, Mode):
        if Mode in self.sdr.MODES:
            self.Mode = Mode
            self.sdr.SetMode(Mode)
        else:
            # Invalid Mode
            raise IndexError()
            