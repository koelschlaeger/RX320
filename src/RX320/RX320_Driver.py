# -*- coding: utf-8 -*-
"""
Created on Sun May  1 14:58:07 2022

@author: KOelschlaeger
"""
import struct
from queue import Empty, Queue
from threading import Event, Thread

import serial

# Get/Set functions are thread-safe as they only append to the queue, which
# a worker thread (_ServiceQueue) drains to the serial port.

BAUDRATE = 1200
BYTESIZE = 8
PARITY = 'N'

POLL_INTERVAL = 0.2  # Seconds of idle time before polling signal strength
REPLY_LEN = 4        # Reply to 'X': b'X' + 16-bit value + b'\r'

class RX320_Driver():
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

    # Offset direction applied to the tuning frequency for each mode
    MODE_CORRECTION = dict({
        'AM'  :  0,
        'USB' :  1,
        'LSB' : -1,
        'CW'  : -1
        })

    def __init__(self, ComPort):
        # Setup serial interface
        self.com = serial.Serial()
        self.com.port = ComPort # SERIALPORT
        self.com.baudrate = BAUDRATE
        self.com.bytesize = BYTESIZE
        self.com.parity = PARITY
        self.com.timeout = 0.75
        # Setup message queue and worker thread state
        self.msgQueue = Queue()
        self.queueThread = None
        self._stop = Event()
        self.RSI = 0

    def OpenSerial(self):
        if not self.com.is_open:
            try:
                self.com.open()
            except serial.SerialException:
                return False
        self._PowerUp()

        self._stop.clear()
        # Daemon so a missed CloseSerial() can't keep the process alive
        self.queueThread = Thread(target=self._ServiceQueue, daemon=True)
        self.queueThread.start()
        return True

    def IsOpen(self):
        # True while the port is open and the worker is still servicing it
        return self.com.is_open and not self._stop.is_set()

    def CloseSerial(self):
        # Drop pending commands, let the worker finish, then close the port
        self._stop.set()
        with self.msgQueue.mutex:
            self.msgQueue.queue.clear()
        if self.queueThread:
            self.queueThread.join()
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
        mCorr = self.MODE_CORRECTION.get(mode, 0)

        # Filter Correction
        fCorr = (bw / 2) + 200

        # Tuning factors
        AdjustedTuningFreq = freq - 0.00125 + (mCorr * (fCorr + cwbfo)) / 1000000
        CoarseTuningFactor = int(AdjustedTuningFreq / 0.0025) + 18000
        FineTuningFactor = int((AdjustedTuningFreq % 0.0025) * 2500 * 5.46)
        BFOTuningFactor = int((fCorr + cwbfo + 8000) * 2.73)

        # 'N' followed by each factor as a big-endian 16-bit value
        self.msgQueue.put((struct.pack('>cHHH', b'N', CoarseTuningFactor,
                                       FineTuningFactor, BFOTuningFactor), 'W'))

    def GetSignalStrength(self):
        # Send X to request signal strength
        self.msgQueue.put((struct.pack('c', b'X'), 'RW'))

    def _PowerUp(self):
        # Reprogramming the radio at power-up requires setting the MODE,
        # FREQUENCY, FILTER and VOLUME level. To prevent unwanted audio
        # output the VOLUME setting should be done last.
        self.SetVFO(0.500, 'AM', 8000)
        # 8kHz filter
        self.SetFilter(8000)
        # Mute
        self.SetAttenuation(63, 'Both')

    def _CommandWrite(self, cmd):
        self.com.write(cmd + b'\r')

    def _CommandReadWrite(self, cmd):
        # Returns the reply's 16-bit value, or None if no valid reply arrived.
        # Replies end in '\r', not '\n', so read a fixed length rather than
        # readline(), which would always wait out the full timeout.
        self.com.read(self.com.in_waiting)  # Discard any stale reply bytes
        self.com.write(cmd + b'\r')
        reply = self.com.read(REPLY_LEN)
        if len(reply) != REPLY_LEN or reply[:1] != cmd[:1] or reply[-1:] != b'\r':
            return None
        return struct.unpack('>cHc', reply)[1]

    def _ServiceQueue(self):
        while not self._stop.is_set():
            try:
                (msg, mode) = self.msgQueue.get(timeout=POLL_INTERVAL)
            except Empty:
                # Nothing to send, so poll signal strength
                (msg, mode) = (b'X', 'RW')

            try:
                if mode == 'RW':
                    value = self._CommandReadWrite(msg)
                    if value is not None:
                        self.RSI = value
                elif mode == 'W':
                    self._CommandWrite(msg)
            except (OSError, serial.SerialException):
                # Port went away (e.g. USB unplugged); stop the worker
                self._stop.set()

