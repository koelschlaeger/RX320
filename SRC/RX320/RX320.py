# -*- coding: utf-8 -*-
"""
Created on Sun May  1 14:58:07 2022

@author: KOelschlaeger
"""
import serial
import struct
from queue import Queue
from time import sleep

# Get/Set functions should be thread-safe as they only append to the queue.
# Still need to implement the way to call the _ServiceQueue() method either
# on a timer or as a 'continuous' task thread

SERIALPORT = '/dev/cu.usbserial-AB0N3GLA' #'/dev/cu.usbserial-2110'
BAUDRATE = 1200
BYTESIZE = 8
PARITY = 'N'

class RX320():
    MinFreq = 0.5
    MaxFreq = 30
    
    MODES = dict({
        'AM':  b'M0',     #M0
        'USB': b'M1',     #M1
        'LSB': b'M2',     #M2
        'CW':  b'M3'      #M3
        })

    FILTERS = dict({
        300: b'\x57\x20',       #W + binary(0-33)
        330: b'\x57\x1F',
        375: b'\x57\x1E',
        450: b'\x57\x1D',
        525: b'\x57\x1C',
        600: b'\x57\x1B',
        675: b'\x57\x1A',
        750: b'\x57\x19',
        900: b'\x57\x18',
        1050:b'\x57\x17',
        1200:b'\x57\x16',
        1350:b'\x57\x15',
        1500:b'\x57\x14',
        1650:b'\x57\x13',
        1800:b'\x57\x12',
        1950:b'\x57\x11',
        2100:b'\x57\x10',
        2250:b'\x57\x0F',
        2400:b'\x57\x0E',
        2550:b'\x57\x0D',
        2700:b'\x57\x0C',
        2850:b'\x57\x0B',
        3000:b'\x57\x0A',
        3300:b'\x57\x09',
        3600:b'\x57\x08',
        3900:b'\x57\x07',
        4200:b'\x57\x06',
        4500:b'\x57\x05',
        4800:b'\x57\x04',
        5100:b'\x57\x03',
        5400:b'\x57\x02',
        5700:b'\x57\x01',
        6000:b'\x57\x00',
        8000:b'\x57\x21'
        })

    AGC = dict({
         "Slow"   : b'G1',    #G1
         "Medium" : b'G2',    #G2
         "Fast"   : b'G3' })  #G3

    VOL = dict({
        'Line'    : b'A',    #A <00> <volume 0-63>
        'Speaker' : b'V',    #V <00> <volume 0-63>
        'Both'    : b'C'     #C <00> <volume 0-63>
        })
    
    def __init__(self, ComPort):
        # Setup serial interface
        self.com = serial.Serial()
        self.com.port = ComPort # SERIALPORT
        self.com.baudrate = BAUDRATE
        self.com.bytesize = BYTESIZE
        self.com.parity = PARITY
        self.com.timeout = 0.75
        # Setup message queue
        self.msgQueue = Queue()
        
    def OpenSerial(self):
        if self.com.is_open:
            self._PowerUp()
            #self.SetVFO(7.3, 'AM', 8000)
            #self.SetVolume('Both', 16)
        else:
            try:
                self.com.open()
            except serial.serialutil.SerialException:
                self.com.close()
                return False
            self._PowerUp()
        
        self._ServiceQueue()
        return True
        
        
    def CloseSerial(self):
        self.QueueEnable = False
        self.msgQueue.empty()
        sleep(0.250)
        if self.com.is_open:
            self.com.close()
        
    
    def SetAttenuation(self, level=63, cmd='Both'):
        if ((level >= 0) and (level <= 63)):
            self.msgQueue.put((struct.pack('cBB', self.VOL[cmd], 0, level), 'W'))
            return True
        else:
            return False
                
    def SetFilter(self, BandWidth):
        if BandWidth in self.FILTERS:
            self.msgQueue.put((struct.pack('2s',self.FILTERS[BandWidth]), 'W'))
            return True
        else:
            return False
                
    def SetAGC(self, mode):
        if mode in self.AGC:
            self.msgQueue.put((struct.pack('2s', self.AGC[mode]), 'W'))
            return True
        else:
            return False
    
    def SetMode(self, mode):
        if mode in self.MODES:
            self.msgQueue.put((struct.pack('2s', self.MODES[mode]), 'W'))
            return True
        else:
            return False
    
    # freq: VFO tuning frequency (MHz)
    # mode: AM/USB/LSB/CW
    # bw: filter bandwidth
    # cwbfo: CW Beat Freq Offset
    def SetVFO(self, freq, mode, bw, cwbfo=0):
        # Mode Correction
        ModeCorr = dict({
            'AM'  :  0,
            'USB' :  1,
            'LSB' : -1,
            'CW'  : -1
            })
        
        if mode in ModeCorr:
            mCorr = ModeCorr[mode]
        else:
            mCorr = 0
        
        # Filter Correction
        fCorr = (bw / 2) + 200
        
        # Tuning factors
        AdjustedTuningFreq = freq - 0.00125 + (mCorr * (fCorr + cwbfo)) / 1000000
        CoarseTuningFactor = int(AdjustedTuningFreq / 0.0025) + 18000
        FineTuningFactor = int((AdjustedTuningFreq % 0.0025) * 2500 * 5.46)
        BFOTuningFactor = int((fCorr + cwbfo + 8000) * 2.73)
        
        # Byte Packing
        baCTF = struct.pack('H', CoarseTuningFactor)
        baFTF = struct.pack('H', FineTuningFactor)
        baBFOTF = struct.pack('H', BFOTuningFactor)
        
        Ch = baCTF[1]
        Cl = baCTF[0]
        Fh = baFTF[1]
        Fl = baFTF[0]
        Bh = baBFOTF[1]
        Bl = baBFOTF[0]
        
        self.msgQueue.put((struct.pack('cBBBBBB', b'N', Ch, Cl, Fh, Fl, Bh, Bl),'W'))
                
    def GetSignalStrength(self):
        # Send X to request signal strength
        self.msgQueue.put((struct.pack('c', b'X'), 'RW'))
    
    def _PowerUp(self):
        # Reprogramming the radio at power-up requires setting the MODE,
        # FERQUENCY, FILTER and VOLUME level. To prevent unwanted audio output the VOLUME setting should be done last.
        self.SetVFO(0.550, 'AM', 8000)
        # 6kHz filter
        self.SetFilter(8000)
        # Mute
        self.SetAttenuation(63, 'Both')
        # Enable Message Queue
        self.QueueEnable = True
    
    def _CommandWrite(self, cmd):
        if self.com.is_open:
            FS = str(len(cmd)) + 'sc'
            ba = struct.pack(FS, cmd, b'\r')
            self.com.write(ba)
            # print(com.readline())
        
    def _CommandReadWrite(self, cmd):
        if self.com.is_open:
            FS = str(len(cmd)) + 'sc'
            self.com.write(struct.pack(FS, cmd, b'\r'))
            ret = self.com.readline()
            try:
                value = struct.unpack('>cHc', ret)
            except:
                value = ([0, 0, 0])
        return value[1]
    
    def _ServiceQueue(self):
        while self.QueueEnable:
            if self.msgQueue.empty():
                # If the queue is empty, add RSI request to queue
                self.GetSignalStrength()
            else:
                (msg, mode) = self.msgQueue.get()
                if mode == 'RW':
                    self.RSI = self._CommandReadWrite(msg)
                elif mode == 'W':
                    self._CommandWrite(msg)
                    