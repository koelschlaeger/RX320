# RX320

A desktop control panel for the Ten-Tec RX-320 PC-controlled shortwave
receiver, written in Python with PyQt6.

The RX-320 has no front-panel controls and stores no settings of its own: it
is programmed entirely over its serial port. This app provides the controls
and keeps the radio in sync with them.

## Features

- Tuning from 0.5 to 30 MHz with a dial, step buttons, or by typing a
  frequency; steps from 10 Hz to 10 kHz
- Two VFOs (store A → B, swap A / B)
- Modes AM, USB, LSB and CW; slow, medium and fast AGC; all 34 filter
  bandwidths from 300 Hz to 8 kHz
- Separate line-out and speaker volume, optionally linked, with mute
- Signal strength meter
- Detects a lost connection (e.g. an unplugged USB adapter)
- Remembers your settings between sessions; volume always starts muted

## Requirements

- An RX-320 connected to a serial port, typically through a USB serial adapter
- Python 3 (developed with Python 3.13)
- PyQt6 and pyserial (see `requirements.txt`)

Developed and tested on a Raspberry Pi running Raspberry Pi OS; it should also
run on other Linux systems, Windows and macOS.

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running

```sh
python src/main.py
```

Pick the radio's serial port from the list at the bottom (USB adapters are
listed first; click **Refresh** after plugging one in) and click **Connect**.
On connect the app sends all of its current settings to the radio, with the
volume last so the radio doesn't play audio before it is tuned.

Settings are saved when you close the window, in
`~/.config/RX320/RX320.conf` on Linux.

## Tests

```sh
pip install -r requirements-dev.txt
pytest
```

The suite runs headless (no display needed) and never touches a real radio or
your saved settings: it uses fake radios, including a pseudo-terminal that
stands in for the serial device (those tests are skipped on Windows).

## Project layout

```
src/
  main.py              entry point
  gui/                 the PyQt6 window and GUI-side logic
    main_window.py
    radio_controller.py    VFO state, independent of Qt
    serial_utils.py        serial port discovery
    constants.py
  RX320/               the radio, independent of the GUI
    RX320.py               high-level interface used by the GUI
    RX320_Driver.py        serial protocol and command queue
    RX320_Data.py          command tables, limits and defaults
  img/                 icons and logo
tests/                 pytest suite
```

The serial protocol follows Ten-Tec's *RX-320 Programmer's Guide*. The
manuals are included in this repository.
