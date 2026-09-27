"""Main application window for the RX320 GUI."""

import serial
from PyQt6.QtGui import QIcon, QPixmap, QDoubleValidator
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDial, QDialog, QGridLayout,
        QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
        QRadioButton, QButtonGroup, QSlider, QVBoxLayout)

from RX320.RX320 import RX320

from .constants import IMG_DIR, TuningSteps
from .radio_controller import RadioController
from .serial_utils import getSerialPorts


class MainWindow(QDialog):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
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

        self.createModeGroupBox()
        self.createAGCGroupBox()
        self.createStepGroupBox()
        self.createVFOGroupBox()
        self.createSliderGroupBox()
        self.createStatusGroupBox()

        self.createTopLayout()
        self.createBottomLayout()

        self._controls = [self.modeGroupBox, self.agcGroupBox, self.stepGroupBox,
                           self.vfoGroupBox, self.sliderGroupBox,
                           self.pushButtonMute, self.lineEditVFOA]

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

        self.tuningStepMHz = TuningSteps[self.stepButtonGroup.checkedId()] / 1000000.0

    def _make_button(self, text='', icon=None, slot=None) -> QPushButton:
        btn = QPushButton(text)
        if icon:
            btn.setIcon(QIcon(icon))
        btn.setDefault(False)
        btn.setAutoDefault(False)
        if slot:
            btn.clicked.connect(slot)
        return btn

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

    def createModeGroupBox(self):
        self.modeGroupBox = QGroupBox("Mode")
        self.modeButtonGroup = QButtonGroup(self)
        layout = QVBoxLayout()
        n = 0
        for mode in self.Modes:
            radioButton = QRadioButton(mode)
            self.modeButtonGroup.addButton(radioButton, n)
            if n == 0:
                radioButton.setChecked(True)
            layout.addWidget(radioButton)
            n += 1

        self.modeButtonGroup.buttonClicked.connect(self.modeButtonGroup_ButtonClicked)
        layout.addStretch(1)
        self.modeGroupBox.setLayout(layout)

    def createAGCGroupBox(self):
        self.agcGroupBox = QGroupBox("AGC")

        radioButton1 = QRadioButton("Slow")
        radioButton2 = QRadioButton("Med")
        radioButton3 = QRadioButton("Fast")
        radioButton2.setChecked(True)

        self.agcButtonGroup = QButtonGroup(self)
        self.agcButtonGroup.addButton(radioButton1, 0)
        self.agcButtonGroup.addButton(radioButton2, 1)
        self.agcButtonGroup.addButton(radioButton3, 2)
        self.agcButtonGroup.buttonClicked.connect(self.agcButtonGroup_ButtonClicked)

        layout = QVBoxLayout()
        layout.addWidget(radioButton1)
        layout.addWidget(radioButton2)
        layout.addWidget(radioButton3)
        layout.addStretch(1)
        self.agcGroupBox.setLayout(layout)

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

        self.dial = QDial(self.vfoGroupBox)
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

    def createStepGroupBox(self):
        self.stepGroupBox = QGroupBox('Step')

        layout = QVBoxLayout()

        radioButton1 = QRadioButton("10 Hz")
        radioButton2 = QRadioButton("100 Hz")
        radioButton3 = QRadioButton("1 kHz")
        radioButton4 = QRadioButton("5 kHz")
        radioButton5 = QRadioButton("10 kHz")
        radioButton4.setChecked(True)

        self.stepButtonGroup = QButtonGroup(self)
        self.stepButtonGroup.addButton(radioButton1, 0)
        self.stepButtonGroup.addButton(radioButton2, 1)
        self.stepButtonGroup.addButton(radioButton3, 2)
        self.stepButtonGroup.addButton(radioButton4, 3)
        self.stepButtonGroup.addButton(radioButton5, 4)
        self.stepButtonGroup.buttonClicked.connect(self.stepButtonGroup_ButtonClicked)

        layout.addWidget(radioButton1)
        layout.addWidget(radioButton2)
        layout.addWidget(radioButton3)
        layout.addWidget(radioButton4)
        layout.addWidget(radioButton5)

        self.stepGroupBox.setLayout(layout)

    def createSliderGroupBox(self):
        self.sliderGroupBox = QGroupBox()

        labelLine = QLabel('Line')
        labelVol = QLabel('Vol')
        labelBW = QLabel('BW')
        labelPBT = QLabel('PBT')

        self.sliderLine = QSlider(Qt.Orientation.Vertical, self.sliderGroupBox)
        self.sliderLine.setRange(-96, 0)
        self.sliderLine.setTickPosition(QSlider.TickPosition.TicksLeft)
        self.sliderLine.setValue(-96)
        self.sliderLine.valueChanged.connect(self.sliderLine_ValueChange)

        self.sliderVol = QSlider(Qt.Orientation.Vertical, self.sliderGroupBox)
        self.sliderVol.setRange(-96, 0)
        self.sliderVol.setTickPosition(QSlider.TickPosition.TicksLeft)
        self.sliderVol.setValue(-96)
        self.sliderVol.valueChanged.connect(self.sliderVol_ValueChange)

        self.sliderBW = QSlider(Qt.Orientation.Vertical, self.sliderGroupBox)
        self.sliderBW.setRange(0, 33)
        self.sliderBW.setValue(33)
        self.sliderBW.valueChanged.connect(self.sliderBW_ValueChange)

        self.sliderPBT = QSlider(Qt.Orientation.Vertical, self.sliderGroupBox)
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

        self.lineEditVFOA = QLineEdit(self)
        self.lineEditVFOA.setValidator(QDoubleValidator())
        self.lineEditVFOA.returnPressed.connect(self.lineEditVFOA_ReturnPressed)
        self.lineEditVFOA.setText(f'{self.radio.vfo_a:6f}')

        self.lineEditVFOB = QLineEdit(self)
        self.lineEditVFOB.setText(f'{self.radio.vfo_b:6f}')
        self.lineEditVFOB.setDisabled(True)

        self.labelMode_Act = QLabel()
        self.labelMode_Act.setText(self.Modes[self.modeButtonGroup.checkedId()])
        self.labelAGC_Act = QLabel()
        self.labelAGC_Act.setText(self.AGCModes[self.agcButtonGroup.checkedId()])
        self.labelBW_Act = QLabel()
        self.labelBW_Act.setText(str(self.Filters[self.sliderBW.value()]))

        layout = QGridLayout()
        layout.addWidget(labelVFOA, 0, 0, 2, 1)
        layout.addWidget(self.lineEditVFOA, 0, 1, 2, 1)
        layout.addWidget(labelVFOB, 2, 0, 2, 1)
        layout.addWidget(self.lineEditVFOB, 2, 1, 2, 1)
        layout.addWidget(labelMode, 0, 2)
        layout.addWidget(labelAGC, 1, 2)
        layout.addWidget(labelBW, 2, 2)
        layout.addWidget(self.labelMode_Act, 0, 3)
        layout.addWidget(self.labelAGC_Act, 1, 3)
        layout.addWidget(self.labelBW_Act, 2, 3)

        self.statusGroupBox.setLayout(layout)

    def lineEditVFOA_ReturnPressed(self):
        freq = self.radio.set_vfo_a(float(self.lineEditVFOA.text()))
        self.lineEditVFOA.setText(f'{freq:6f}')

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
            freq = self.radio.step_vfo_a(delta * self.tuningStepMHz)
            self.lineEditVFOA.setText(f'{freq:6f}')

    def sliderLine_ValueChange(self):
        if self.checkBoxLink.isChecked():
            self.sliderVol.setValue(self.sliderLine.value())
        self.sdr.SetAttenuation(self.sliderLine.value(), 'Line')

    def sliderVol_ValueChange(self):
        if self.checkBoxLink.isChecked():
            self.sliderLine.setValue(self.sliderVol.value())
        self.sdr.SetAttenuation(self.sliderVol.value(), 'Speaker')

    def sliderBW_ValueChange(self):
        filter_id = self.sliderBW.value()
        self.sdr.SetFilter(self.Filters[filter_id])
        self.labelBW_Act.setText(str(self.Filters[filter_id]))

    def checkBoxLink_Toggled(self):
        if self.checkBoxLink.isChecked():
            min_value = min(self.sliderVol.value(), self.sliderLine.value())
            self.sliderVol.setValue(min_value)
            self.sliderLine.setValue(min_value)

    def modeButtonGroup_ButtonClicked(self):
        mode_id = self.modeButtonGroup.checkedId()
        self.sdr.SetMode(self.Modes[mode_id])
        self.labelMode_Act.setText(self.Modes[mode_id])

    def agcButtonGroup_ButtonClicked(self):
        agc_id = self.agcButtonGroup.checkedId()
        self.sdr.SetAGC(self.AGCModes[agc_id])
        self.labelAGC_Act.setText(self.AGCModes[agc_id])

    def stepButtonGroup_ButtonClicked(self):
        step_id = self.stepButtonGroup.checkedId()
        self.tuningStepMHz = TuningSteps[step_id] / 1000000.0

    def pushButtonStep_ButtonClicked(self, step):
        freq = self.radio.step_vfo_a(step)
        self.lineEditVFOA.setText(f'{freq:6f}')

    def pushButtonVFOStore_ButtonClicked(self):
        vfo_b = self.radio.store_a_to_b()
        self.lineEditVFOB.setText(f'{vfo_b:6f}')

    def pushButtonVFOSwap_ButtonClicked(self):
        vfo_a, vfo_b = self.radio.swap_vfo()
        self.lineEditVFOA.setText(f'{vfo_a:6f}')
        self.lineEditVFOB.setText(f'{vfo_b:6f}')

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
