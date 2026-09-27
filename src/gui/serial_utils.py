"""Serial-port discovery helpers."""

from serial.tools import list_ports


def get_serial_ports():
    # Lists (device, description) for the serial ports on the system, USB
    # adapters first (the likeliest to be the radio), then by name. The
    # description is None when the OS knows nothing about the port.
    # Uses the OS device list rather than opening each port, so probing
    # does not disturb whatever is attached.
    ports = sorted(list_ports.comports(), key=lambda p: (p.vid is None, p.device))
    return [(port.device, _describe(port)) for port in ports]


def _describe(port):
    # e.g. 'FT232R USB UART (FTDI), serial AB0N3GLA'. pyserial's own
    # description repeats the product name on Linux, so build it from parts.
    if port.product:
        text = port.product
        if port.manufacturer:
            text += f' ({port.manufacturer})'
        if port.serial_number:
            text += f', serial {port.serial_number}'
        return text
    if port.description and port.description != 'n/a':
        return port.description  # e.g. 'Communications Port (COM1)' on Windows
    return None
