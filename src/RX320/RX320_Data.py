from dataclasses import dataclass


@dataclass(frozen=True)
class Mode:
    name: str           # 'AM'
    command: bytes      # b'M0'
    correction: int     # tuning offset direction: +1, -1, or 0

@dataclass(frozen=True)
class Filter:
    bandwidth:  int     # Hz
    command:    bytes   # b'W\x0a'

@dataclass(frozen=True)
class AGCMode:
    name:       str
    command:    bytes

@dataclass(frozen=True)
class VolumeTarget:
    name:       str     # 'Line'
    command:    bytes   # b'A'; the level is appended when sent

@dataclass(frozen=True)
class SerialSettings:
    baudrate:   int = 1200
    bytesize:   int = 8
    parity:     str = 'N'
    timeout:    float = 0.75

MODES = (
    Mode('AM',  b'M0',  0),
    Mode('USB', b'M1',  1),
    Mode('LSB', b'M2', -1),
    Mode('CW',  b'M3', -1)
)

FILTERS = (
    Filter(300, b'\x57\x20'),       #W + binary(0-33)
    Filter(330,  b'\x57\x1F'),
    Filter(375,  b'\x57\x1E'),
    Filter(450,  b'\x57\x1D'),
    Filter(525,  b'\x57\x1C'),
    Filter(600,  b'\x57\x1B'),
    Filter(675,  b'\x57\x1A'),
    Filter(750,  b'\x57\x19'),
    Filter(900,  b'\x57\x18'),
    Filter(1050, b'\x57\x17'),
    Filter(1200, b'\x57\x16'),
    Filter(1350, b'\x57\x15'),
    Filter(1500, b'\x57\x14'),
    Filter(1650, b'\x57\x13'),
    Filter(1800, b'\x57\x12'),
    Filter(1950, b'\x57\x11'),
    Filter(2100, b'\x57\x10'),
    Filter(2250, b'\x57\x0F'),
    Filter(2400, b'\x57\x0E'),
    Filter(2550, b'\x57\x0D'),
    Filter(2700, b'\x57\x0C'),
    Filter(2850, b'\x57\x0B'),
    Filter(3000, b'\x57\x0A'),
    Filter(3300, b'\x57\x09'),
    Filter(3600, b'\x57\x08'),
    Filter(3900, b'\x57\x07'),
    Filter(4200, b'\x57\x06'),
    Filter(4500, b'\x57\x05'),
    Filter(4800, b'\x57\x04'),
    Filter(5100, b'\x57\x03'),
    Filter(5400, b'\x57\x02'),
    Filter(5700, b'\x57\x01'),
    Filter(6000, b'\x57\x00'),
    Filter(8000, b'\x57\x21')
)

AGC_MODES = (
    AGCMode('Slow',   b'G1'),
    AGCMode('Medium', b'G2'),
    AGCMode('Fast',   b'G3')
)

# Sent as <command> 0x00 <attenuation 0-63>
VOLUME_TARGETS = (
    VolumeTarget('Line',    b'A'),
    VolumeTarget('Speaker', b'V'),
    VolumeTarget('Both',    b'C')
)

MINFREQ = 0.5   # MHz
MAXFREQ = 30.0  # MHz

# Power-up state the driver programs, and the GUI's initial settings
DEFAULT_MODE = 'AM'
DEFAULT_FILTER = 8000     # Hz
DEFAULT_AGC = 'Medium'    # also the radio's own power-up default
DEFAULT_FREQ = 0.5        # MHz

# Volume: attenuation codes 0 (loudest) to 63 (quietest), 96 dB range
ATTENUATION_MAX = 63
ATTENUATION_RANGE_DB = 96

SIGNAL_MAX = 10000        # full-scale signal strength reading (measured)
