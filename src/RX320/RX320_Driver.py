# -*- coding: utf-8 -*-
"""
Created on Sun May  1 14:58:07 2022

@author: KOelschlaeger
"""
import struct
from queue import Empty, Queue
from threading import Event, Thread

import serial

from RX320 import RX320_Data as data

# Get/Set functions are thread-safe as they only append to the queue, which
# a worker thread (_service_queue) drains to the serial port.

POLL_INTERVAL = 0.2  # Seconds of idle time before polling signal strength
REPLY_LEN = 4        # Reply to 'X': b'X' + 16-bit value + b'\r'

class RX320_Driver():
    # Lookup by name, e.g. MODES['USB'].command -> b'M1'
    MODES = {m.name: m for m in data.MODES}
    FILTERS = {f.bandwidth: f for f in data.FILTERS}
    AGC = {m.name: m for m in data.AGC_MODES}
    VOL = {v.name: v for v in data.VOLUME_TARGETS}

    def __init__(self, port):
        # Setup serial interface
        self.com = serial.Serial()
        self.com.port = port # SERIALPORT
        settings = data.SerialSettings()
        self.com.baudrate = settings.baudrate
        self.com.bytesize = settings.bytesize
        self.com.parity = settings.parity
        self.com.timeout = settings.timeout
        # Setup message queue and worker thread state
        self.msg_queue = Queue()
        self.queue_thread = None
        self._stop = Event()
        self.rsi = 0

    def open_serial(self):
        if self.queue_thread is not None and self.queue_thread.is_alive():
            # Already open and running: don't start a second worker
            return True
        if not self.com.is_open:
            try:
                self.com.open()
            except serial.SerialException:
                return False
        self._power_up()

        self._stop.clear()
        # Daemon so a missed close_serial() can't keep the process alive
        self.queue_thread = Thread(target=self._service_queue, daemon=True)
        self.queue_thread.start()
        return True

    def is_open(self):
        # True while the port is open and the worker is still servicing it
        return self.com.is_open and not self._stop.is_set()

    def close_serial(self):
        # Drop pending commands, let the worker finish, then close the port
        self._stop.set()
        with self.msg_queue.mutex:
            self.msg_queue.queue.clear()
        if self.queue_thread:
            self.queue_thread.join()
        self.com.close()

    def _queue_write(self, msg):
        # Queue a setting command. If one of the same kind (same command
        # letter, e.g. 'N' tune or 'V' speaker volume) is still waiting to be
        # sent, overwrite it in place: only the latest value matters, and at
        # 1200 baud a fast dial spin or slider drag would otherwise leave the
        # radio seconds behind. Overwriting in place keeps the queue order.
        with self.msg_queue.mutex:
            pending = self.msg_queue.queue
            for i, (queued, mode) in enumerate(pending):
                if mode == 'W' and queued[:1] == msg[:1]:
                    pending[i] = (msg, 'W')
                    return
        self.msg_queue.put((msg, 'W'))

    def set_attenuation(self, level=data.ATTENUATION_MAX, cmd='Both'):
        if ((level >= 0) and (level <= data.ATTENUATION_MAX)):
            self._queue_write(struct.pack('cBB', self.VOL[cmd].command, 0, level))
            return True
        else:
            return False

    def set_filter(self, bandwidth):
        if bandwidth in self.FILTERS:
            self._queue_write(struct.pack('2s', self.FILTERS[bandwidth].command))
            return True
        else:
            return False

    def set_agc(self, mode):
        if mode in self.AGC:
            self._queue_write(struct.pack('2s', self.AGC[mode].command))
            return True
        else:
            return False

    def set_mode(self, mode):
        if mode in self.MODES:
            self._queue_write(struct.pack('2s', self.MODES[mode].command))
            return True
        else:
            return False

    # freq: VFO tuning frequency (MHz)
    # mode: AM/USB/LSB/CW
    # bw: filter bandwidth
    # cwbfo: CW Beat Freq Offset
    def set_vfo(self, freq, mode, bw, cwbfo=0):
        # Mode Correction
        mode_correction = self.MODES[mode].correction

        # Filter Correction
        filter_correction = (bw / 2) + 200

        # Tuning factors
        adjusted_freq = freq - 0.00125 + (mode_correction * (filter_correction + cwbfo)) / 1000000
        coarse_factor = int(adjusted_freq / 0.0025) + 18000
        fine_factor = int((adjusted_freq % 0.0025) * 2500 * 5.46)
        bfo_factor = int((filter_correction + cwbfo + 8000) * 2.73)

        # 'N' followed by each factor as a big-endian 16-bit value
        self._queue_write(struct.pack('>cHHH', b'N', coarse_factor,
                                     fine_factor, bfo_factor))

    def get_signal_strength(self):
        # Send X to request signal strength
        self.msg_queue.put((struct.pack('c', b'X'), 'RW'))

    def _power_up(self):
        # Reprogramming the radio at power-up requires setting the MODE,
        # FREQUENCY, FILTER and VOLUME level. To prevent unwanted audio
        # output the VOLUME setting should be done last.
        self.set_vfo(data.DEFAULT_FREQ, data.DEFAULT_MODE, data.DEFAULT_FILTER)
        self.set_filter(data.DEFAULT_FILTER)
        # Mute
        self.set_attenuation(data.ATTENUATION_MAX, 'Both')

    def _command_write(self, cmd):
        self.com.write(cmd + b'\r')

    def _command_read_write(self, cmd):
        # Returns the reply's 16-bit value, or None if no valid reply arrived.
        # Replies end in '\r', not '\n', so read a fixed length rather than
        # readline(), which would always wait out the full timeout.
        self.com.read(self.com.in_waiting)  # Discard any stale reply bytes
        self.com.write(cmd + b'\r')
        reply = self.com.read(REPLY_LEN)
        if len(reply) != REPLY_LEN or reply[:1] != cmd[:1] or reply[-1:] != b'\r':
            return None
        return struct.unpack('>cHc', reply)[1]

    def _service_queue(self):
        while not self._stop.is_set():
            try:
                (msg, mode) = self.msg_queue.get(timeout=POLL_INTERVAL)
            except Empty:
                # Nothing to send, so poll signal strength
                (msg, mode) = (b'X', 'RW')

            try:
                if mode == 'RW':
                    value = self._command_read_write(msg)
                    if value is not None:
                        self.rsi = value
                elif mode == 'W':
                    self._command_write(msg)
            except (OSError, serial.SerialException):
                # Port went away (e.g. USB unplugged); stop the worker
                self._stop.set()

