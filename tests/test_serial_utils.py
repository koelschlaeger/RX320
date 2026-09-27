from types import SimpleNamespace

from gui import serial_utils


def port(device, vid=None, product=None, manufacturer=None, serial_number=None,
         description='n/a'):
    return SimpleNamespace(device=device, vid=vid, product=product,
                           manufacturer=manufacturer, serial_number=serial_number,
                           description=description)


def test_ports_are_listed_usb_first_with_descriptions(monkeypatch):
    monkeypatch.setattr(serial_utils.list_ports, 'comports', lambda: [
        port('/dev/ttyAMA10'),  # Pi's built-in UART: no details at all
        port('/dev/ttyUSB1', vid=0x0403, product='FT232R USB UART'),
        port('/dev/ttyUSB0', vid=0x0403, product='FT232R USB UART',
             manufacturer='FTDI', serial_number='AB0N3GLA',
             description='FT232R USB UART - FT232R USB UART'),
    ])
    assert serial_utils.get_serial_ports() == [
        ('/dev/ttyUSB0', 'FT232R USB UART (FTDI), serial AB0N3GLA'),
        ('/dev/ttyUSB1', 'FT232R USB UART'),
        ('/dev/ttyAMA10', None),
    ]


def test_description_used_when_there_is_no_product_name(monkeypatch):
    # Typical of built-in ports on Windows
    monkeypatch.setattr(serial_utils.list_ports, 'comports', lambda: [
        port('COM1', description='Communications Port (COM1)'),
    ])
    assert serial_utils.get_serial_ports() == [('COM1', 'Communications Port (COM1)')]
