"""Main application window for the RX320 GUI."""

import serial
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QSignalBlocker, QTimer
from PyQt6.QtWidgets import (QAbstractSpinBox, QCheckBox, QComboBox, QDial,
        QDialog, QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
        QMessageBox, QPushButton, QRadioButton, QButtonGroup, QSlider,
        QVBoxLayout)

from RX320.RX320 import RX320

from .constants import IMG_DIR, TuningSteps
from .radio_controller import RadioController
from .serial_utils import getSerialPorts


def _format_hz(hz):
    # 10.0 -> '10 Hz', 5000.0 -> '5 kHz'
    if hz >= 1000:
        return f'{hz / 1000:g} kHz'
    return f'{hz:g} Hz'


class MainWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Create SDR instance
        self.sdr = RX320()
        self.radio = RadioController(self.sdr)

        self.Modes = self.sdr.Modes
        self.Target = self.sdr.Target
        self.AGCModes = self.sdr.AGCModes
        self.Filters = self.sdr.Filters

        self.dialStart = 0

        # Watches for the radio connection dropping (e.g. USB unplugged)
        self.connectionTimer = QTimer(self)
        self.connectionTimer.setInterval(500)
        self.connectionTimer.timeout.connect(self._check_connection)

        self.modeGroupBox, self.modeButtonGroup = self._make_radio_group(
            'Mode', self.Modes, 0, self.modeButtonGroup_ButtonClicked)
        self.agcGroupBox, self.agcButtonGroup = self._make_radio_group(
            'AGC', ('Slow', 'Med', 'Fast'), 1, self.agcButtonGroup_ButtonClicked)
        self.stepGroupBox, self.stepButtonGroup = self._make_radio_group(
            'Step', [_format_hz(hz) for hz in TuningSteps], 3,
            self.stepButtonGroup_ButtonClicked)
        self.createVFOGroupBox()
        self.createSliderGroupBox()
        self.createStatusGroupBox()

        self.createTopLayout()
        self.createBottomLayout()

        self._controls = [self.modeGroupBox, self.agcGroupBox, self.stepGroupBox,
                           self.vfoGroupBox, self.sliderGroupBox,
                           self.pushButtonMute, self.spinBoxVFOA]

        mainLayout = QGridLayout()
        mainLayout.addLayout(self.topLayout, 0, 0, 1, 5)
        mainLayout.addWidget(self.modeGroupBox, 1, 0)
        mainLayout.addWidget(self.agcGroupBox, 1, 1)
        mainLayout.addWidget(self.stepGroupBox, 1, 2)
        mainLayout.addWidget(self.vfoGroupBox, 1, 3)
        mainLayout.addWidget(self.sliderGroupBox, 1, 4)
        mainLayout.addLayout(self.bottomLayout, 2, 0, 1, 4)
        self.setLayout(mainLayout)
        self.setWindowTitle("RX320")

        self.set_controls_enabled(False)

        self.stepButtonGroup_ButtonClicked(self.stepButtonGroup.checkedId())

    def _make_button(self, text='', icon=None, slot=None) -> QPushButton:
        btn = QPushButton(text)
        if icon:
            btn.setIcon(QIcon(icon))
        btn.setDefault(False)
        btn.setAutoDefault(False)
        if slot:
            btn.clicked.connect(slot)
        return btn

    def _make_radio_group(self, title, labels, checked, slot):
        # A group box of exclusive radio buttons with ids 0..n-1.
        # slot receives the clicked button's id.
        box = QGroupBox(title)
        group = QButtonGroup(self)
        layout = QVBoxLayout()
        for i, label in enumerate(labels):
            radioButton = QRadioButton(label)
            radioButton.setChecked(i == checked)
            group.addButton(radioButton, i)
            layout.addWidget(radioButton)
        layout.addStretch(1)
        box.setLayout(layout)
        group.idClicked.connect(slot)
        return box, group

    def _make_freq_box(self) -> QDoubleSpinBox:
        spinBox = QDoubleSpinBox()
        spinBox.setRange(self.sdr.MinFreq, self.sdr.MaxFreq)
        spinBox.setDecimals(6)
        spinBox.setSuffix(' MHz')
        return spinBox

    def _refresh_serial_ports(self):
        current = self.comboBoxSerialPort.currentText()
        ports = getSerialPorts()
        self.comboBoxSerialPort.clear()
        self.comboBoxSerialPort.addItems(ports)
        if current in ports:
            self.comboBoxSerialPort.setCurrentText(current)

    def createTopLayout(self):
        labelLogo = QLabel()
        labelLogo.setPixmap(QPixmap(str(IMG_DIR / 'ttrx320.xpm')))

        self.topLayout = QHBoxLayout()
        self.topLayout.addWidget(labelLogo)
        self.topLayout.addWidget(self.statusGroupBox)
        self.topLayout.addStretch(1)

    def createBottomLayout(self):
        self.bottomLayout = QHBoxLayout()
        self.comboBoxSerialPort = QComboBox()
        self.comboBoxSerialPort.setMinimumWidth(120)
        self._refresh_serial_ports()

        pushButtonQuit = self._make_button('Quit', slot=self._quit)
        pushButtonConnect = self._make_button('Connect', slot=self._connect)
        pushButtonDisconnect = self._make_button('Disconnect', slot=self._disconnect)
        self.pushButtonMute = self._make_button('Mute', slot=self.pushButtonMute_Clicked)
        pushButtonRefreshSerialPorts = self._make_button('Refresh', slot=self._refresh_serial_ports)

        self.bottomLayout.addWidget(pushButtonQuit)
        self.bottomLayout.addWidget(self.comboBoxSerialPort)
        self.bottomLayout.addWidget(pushButtonRefreshSerialPorts)
        self.bottomLayout.addWidget(pushButtonConnect)
        self.bottomLayout.addWidget(pushButtonDisconnect)
        self.bottomLayout.addWidget(self.pushButtonMute)

    def createVFOGroupBox(self):
        self.vfoGroupBox = QGroupBox()

        pushButtonStepUpUp = self._make_button(icon=str(IMG_DIR / 'up2.xpm'),
                                               slot=lambda: self.pushButtonStep_ButtonClicked(self.tuningStepMHz * 10.0))

        pushButtonStepUp = self._make_button(icon=str(IMG_DIR / 'up.xpm'),
                                             slot=lambda: self.pushButtonStep_ButtonClicked(self.tuningStepMHz * 1.0))

        pushButtonStepDownDown = self._make_button(icon=str(IMG_DIR / 'down2.xpm'),
                                                   slot=lambda: self.pushButtonStep_ButtonClicked(self.tuningStepMHz * -10.0))

        pushButtonStepDown = self._make_button(icon=str(IMG_DIR / 'down.xpm'),
                                               slot=lambda: self.pushButtonStep_ButtonClicked(self.tuningStepMHz * -1.0))

        pushButtonVFOSwap = self._make_button('A / B', slot=self.pushButtonVFOSwap_ButtonClicked)
        pushButtonVFOStore = self._make_button('A -> B', slot=self.pushButtonVFOStore_ButtonClicked)

        self.dial = QDial()
        self.dial.setValue(0)
        self.dial.setMinimum(-100)
        self.dial.setMaximum(100)
        self.dial.setNotchesVisible(True)
        self.dial.setWrapping(True)
        self.dial.valueChanged.connect(self.dial_ValueChanged)

        layout = QGridLayout()
        layout.addWidget(pushButtonStepUpUp, 0, 0)
        layout.addWidget(pushButtonStepUp, 1, 0)
        layout.addWidget(pushButtonStepDown, 2, 0)
        layout.addWidget(pushButtonStepDownDown, 3, 0)
        layout.addWidget(self.dial, 0, 1, 4, 3)
        layout.addWidget(pushButtonVFOStore, 4, 0, 1, 2)
        layout.addWidget(pushButtonVFOSwap, 4, 2, 1, 2)
        self.vfoGroupBox.setLayout(layout)

    def createSliderGroupBox(self):
        self.sliderGroupBox = QGroupBox()

        labelLine = QLabel('Line')
        labelVol = QLabel('Vol')
        labelBW = QLabel('BW')
        labelPBT = QLabel('PBT')

        self.sliderLine = QSlider(Qt.Orientation.Vertical)
        self.sliderLine.setRange(-96, 0)
        self.sliderLine.setTickPosition(QSlider.TickPosition.TicksLeft)
        self.sliderLine.setValue(-96)
        self.sliderLine.valueChanged.connect(self.sliderLine_ValueChange)

        self.sliderVol = QSlider(Qt.Orientation.Vertical)
        self.sliderVol.setRange(-96, 0)
        self.sliderVol.setTickPosition(QSlider.TickPosition.TicksLeft)
        self.sliderVol.setValue(-96)
        self.sliderVol.valueChanged.connect(self.sliderVol_ValueChange)

        self.sliderBW = QSlider(Qt.Orientation.Vertical)
        self.sliderBW.setRange(0, 33)
        self.sliderBW.setValue(33)
        # Only send the filter (and the retune it triggers) on release, so a
        # fast drag doesn't queue up seconds of serial commands.
        self.sliderBW.setTracking(False)
        self.sliderBW.valueChanged.connect(self.sliderBW_ValueChange)
        self.sliderBW.sliderMoved.connect(self.sliderBW_Moved)

        self.sliderPBT = QSlider(Qt.Orientation.Vertical)
        self.sliderPBT.setRange(0, 300)
        self.sliderPBT.setValue(0)

        self.checkBoxLink = QCheckBox("&Link")
        self.checkBoxLink.toggled.connect(self.checkBoxLink_Toggled)

        layout = QGridLayout()
        layout.addWidget(labelLine, 0, 0)
        layout.addWidget(labelVol, 0, 1)
        layout.addWidget(labelBW, 0, 2)
        layout.addWidget(labelPBT, 0, 3)
        layout.addWidget(self.sliderLine, 1, 0)
        layout.addWidget(self.sliderVol, 1, 1)
        layout.addWidget(self.checkBoxLink, 2, 0, 1, 2)
        layout.addWidget(self.sliderBW, 1, 2, 2, 1)
        layout.addWidget(self.sliderPBT, 1, 3, 2, 1)

        self.sliderGroupBox.setLayout(layout)

    def createStatusGroupBox(self):
        self.statusGroupBox = QGroupBox()

        labelMode = QLabel('Mode: ')
        labelAGC = QLabel('AGC: ')
        labelBW = QLabel('BW: ')
        labelVFOA = QLabel('VFO A: ')
        labelVFOB = QLabel('VFO B: ')

        self.spinBoxVFOA = self._make_freq_box()
        # Only emit on Enter/focus-out while typing, not on every keystroke;
        # arrows and the mouse wheel still tune immediately.
        self.spinBoxVFOA.setKeyboardTracking(False)

        self.spinBoxVFOB = self._make_freq_box()
        self.spinBoxVFOB.setReadOnly(True)
        self.spinBoxVFOB.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spinBoxVFOB.setDisabled(True)

        self._show_vfo()
        self.spinBoxVFOA.valueChanged.connect(self.spinBoxVFOA_ValueChanged)

        self.labelMode_Act = QLabel()
        self.labelMode_Act.setText(self.Modes[self.modeButtonGroup.checkedId()])
        self.labelAGC_Act = QLabel()
        self.labelAGC_Act.setText(self.AGCModes[self.agcButtonGroup.checkedId()])
        self.labelBW_Act = QLabel()
        self.labelBW_Act.setText(str(self.Filters[self.sliderBW.value()]))

        layout = QGridLayout()
        layout.addWidget(labelVFOA, 0, 0, 2, 1)
        layout.addWidget(self.spinBoxVFOA, 0, 1, 2, 1)
        layout.addWidget(labelVFOB, 2, 0, 2, 1)
        layout.addWidget(self.spinBoxVFOB, 2, 1, 2, 1)
        layout.addWidget(labelMode, 0, 2)
        layout.addWidget(labelAGC, 1, 2)
        layout.addWidget(labelBW, 2, 2)
        layout.addWidget(self.labelMode_Act, 0, 3)
        layout.addWidget(self.labelAGC_Act, 1, 3)
        layout.addWidget(self.labelBW_Act, 2, 3)

        self.statusGroupBox.setLayout(layout)

    def _show_vfo(self):
        # Display the controller's VFO values. Signals are blocked so that
        # showing a value doesn't send it to the radio a second time.
        with QSignalBlocker(self.spinBoxVFOA):
            self.spinBoxVFOA.setValue(self.radio.vfo_a)
        self.spinBoxVFOB.setValue(self.radio.vfo_b)

    def spinBoxVFOA_ValueChanged(self, freq):
        self.radio.set_vfo_a(freq)

    def pushButtonMute_Clicked(self):
        self.sliderLine.setValue(-96)
        self.sliderVol.setValue(-96)

    def dial_ValueChanged(self, value):
        span = self.dial.maximum() - self.dial.minimum()
        delta = value - self.dialStart
        if delta > span / 2:
            delta -= span
        elif delta < -span / 2:
            delta += span
        self.dialStart = value

        if delta:
            self.radio.step_vfo_a(delta * self.tuningStepMHz)
            self._show_vfo()

    def sliderLine_ValueChange(self, value):
        if self.checkBoxLink.isChecked():
            self.sliderVol.setValue(value)
        self.sdr.SetAttenuation(value, 'Line')

    def sliderVol_ValueChange(self, value):
        if self.checkBoxLink.isChecked():
            self.sliderLine.setValue(value)
        self.sdr.SetAttenuation(value, 'Speaker')

    def sliderBW_ValueChange(self, filter_id):
        self.sdr.SetFilter(self.Filters[filter_id])
        self.labelBW_Act.setText(str(self.Filters[filter_id]))

    def sliderBW_Moved(self, position):
        # Keep the BW label live while dragging; the radio updates on release
        self.labelBW_Act.setText(str(self.Filters[position]))

    def checkBoxLink_Toggled(self, checked):
        if checked:
            min_value = min(self.sliderVol.value(), self.sliderLine.value())
            self.sliderVol.setValue(min_value)
            self.sliderLine.setValue(min_value)

    def modeButtonGroup_ButtonClicked(self, mode_id):
        self.sdr.SetMode(self.Modes[mode_id])
        self.labelMode_Act.setText(self.Modes[mode_id])

    def agcButtonGroup_ButtonClicked(self, agc_id):
        self.sdr.SetAGC(self.AGCModes[agc_id])
        self.labelAGC_Act.setText(self.AGCModes[agc_id])

    def stepButtonGroup_ButtonClicked(self, step_id):
        self.tuningStepMHz = TuningSteps[step_id] / 1000000.0
        # The VFO A spin box arrows and mouse wheel follow the tuning step
        self.spinBoxVFOA.setSingleStep(self.tuningStepMHz)

    def pushButtonStep_ButtonClicked(self, step):
        self.radio.step_vfo_a(step)
        self._show_vfo()

    def pushButtonVFOStore_ButtonClicked(self):
        self.radio.store_a_to_b()
        self._show_vfo()

    def pushButtonVFOSwap_ButtonClicked(self):
        self.radio.swap_vfo()
        self._show_vfo()

    def set_controls_enabled(self, enabled: bool):
        for widget in self._controls:
            widget.setDisabled(not enabled)

    def _quit(self):
        self.close()

    def done(self, result):
        # Every way a QDialog closes (Quit, window X, Esc) ends up here.
        # Stop the serial worker thread, otherwise the non-daemon thread
        # keeps the process alive after the window is gone.
        self._disconnect()
        super().done(result)

    def _connect(self):
        serialPort = self.comboBoxSerialPort.currentText()
        if not serialPort:
            QMessageBox.warning(self, 'No port selected',
                               'No serial port is selected. Click Refresh and try again.')
            return
        try:
            self.sdr.Connect(serialPort)
        except (OSError, serial.SerialException) as e:
            QMessageBox.critical(self, 'Connection failed',
                                 f'Could not connect to {serialPort}:\n{e}')
            return
        if not self.sdr.Connected:
            QMessageBox.critical(self, 'Connection failed',
                                 f'Could not open {serialPort}.')
            return

        self._sync_radio_to_gui()

        # Enable control surfaces
        self.set_controls_enabled(True)
        self.connectionTimer.start()

    def _sync_radio_to_gui(self):
        # Push every GUI setting to the radio, which the driver has just reset
        # to its power-up defaults. Mode and filter go before the VFO because
        # the tuning command depends on them; volume goes last so the radio
        # doesn't briefly play audio at the wrong frequency.
        self.sdr.SetMode(self.Modes[self.modeButtonGroup.checkedId()])
        self.sdr.SetFilter(self.Filters[self.sliderBW.value()])
        self.sdr.SetAGC(self.AGCModes[self.agcButtonGroup.checkedId()])
        self.radio.set_vfo_a(self.radio.vfo_a)
        self.sdr.SetAttenuation(self.sliderLine.value(), 'Line')
        self.sdr.SetAttenuation(self.sliderVol.value(), 'Speaker')

    def _disconnect(self):
        self.connectionTimer.stop()

        # Disable control surfaces
        self.set_controls_enabled(False)

        # Always close the port, even if the connection was already lost
        self.sdr.Disconnect()

    def _check_connection(self):
        if not self.sdr.Connected:
            self._disconnect()
            QMessageBox.warning(self, 'Connection lost',
                                'Lost connection to the radio. Check the cable and reconnect.')
