from dataclasses import dataclass

@dataclass
class Modes():
    AM:  bytes = b'M0'  #M0
    USB: bytes = b'M1'  #M1
    LSB: bytes = b'M2'  #M2
    CW:  bytes = b'M3'  #M3

@dataclass
class Serial():
    BAUDRATE: int = 1200
    BYTESIZE: int = 8
    PARITY:   str = 'N'

@dataclass
class Filters():
    ...

@dataclass
class AGC():
    Slow:   bytes = b'G1'   #G1
    Medium: bytes = b'G2'   #G2
    Fast:   bytes = b'G3'   #G3

@dataclass
class VolumeTarget():
    Line:    bytes = b'A'  #A <00> <volume 0-63>
    Speaker: bytes = b'V'  #V <00> <volume 0-63>
    Both:    bytes = b'C'  #C <00> <volume 0-63>

@dataclass
class ModeCorrection():
    Modes.AM:  int = 0
    Modes.USB: int = 1
    Modes.LSB: int = -1
    Modes.CW:  int = -1

@dataclass
class Mode():
    Label: str = ''
    ByteString: bytes = b'00'
    Correction: int = 0
