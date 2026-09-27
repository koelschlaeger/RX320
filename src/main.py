#!/usr/bin/env python
"""Entry point for the RX320 GUI application."""

import sys

from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow
from RX320.RX320 import RX320

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow(RX320())
    window.show()
    sys.exit(app.exec())
