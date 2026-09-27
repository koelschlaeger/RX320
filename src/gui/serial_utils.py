"""Serial-port discovery helpers."""

from serial.tools import list_ports


def get_serial_ports():
    # Lists serial port names available on the system, USB adapters first
    # (the likeliest to be the radio), then by name.
    # Uses the OS device list rather than opening each port, so probing
    # does not disturb whatever is attached.
    ports = sorted(list_ports.comports(), key=lambda p: (p.vid is None, p.device))
    return [port.device for port in ports]
