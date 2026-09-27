"""Main application window for the RX320 GUI."""

import serial
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QByteArray, QSettings, QSignalBlocker, QTimer
from PyQt6.QtWidgets import (QAbstractSpinBox, QCheckBox, QComboBox, QDial,
        QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
        QMainWindow, QMessageBox, QProgressBar, QPushButton, QRadioButton,
        QButtonGroup, QSlider, QVBoxLayout, QWidget)

from .constants import IMG_DIR, TuningSteps, DEFAULT_STEP
from .radio_controller import RadioController
from .serial_utils import get_serial_ports


# QSettings (organization, application): stored in ~/.config/RX320/RX320.conf
# on Linux
SETTINGS_SCOPE = ('RX320', 'RX320')


def _format_hz(hz):
    # 10.0 -> '10 Hz', 5000.0 -> '5 kHz'
    if hz >= 1000:
        return f'{hz / 1000:g} kHz'
    return f'{hz:g} Hz'


class MainWindow(QMainWindow):
    def __init__(self, sdr, parent=None):
        super().__init__(parent)
        # sdr: an RX320, or any object with the same interface (e.g. a fake
        # radio for tests)
        self.sdr = sdr
        self.radio = RadioController(self.sdr)

        self.Modes = self.sdr.MODES
        self.AGCModes = self.sdr.AGC_MODES
        self.Filters = self.sdr.FILTERS

        self.dialStart = 0

        # While connected: refreshes the status bar and watches for the
        # connection dropping (e.g. USB unplugged)
        self.statusTimer = QTimer(self)
        self.statusTimer.setInterval(250)
        self.statusTimer.timeout.connect(self._update_status)

        self.modeGroupBox, self.modeButtonGroup = self._make_radio_group(
            'Mode', self.Modes, self.Modes.index(self.sdr.DEFAULT_MODE), self.on_mode_changed)
        self.agcGroupBox, self.agcButtonGroup = self._make_radio_group(
            'AGC', self.AGCModes, self.AGCModes.index(self.sdr.DEFAULT_AGC), self.on_agc_changed)
        self.stepGroupBox, self.stepButtonGroup = self._make_radio_group(
            'Step', [_format_hz(hz) for hz in TuningSteps], TuningSteps.index(DEFAULT_STEP),
            self.on_step_changed)
        self._create_vfo_group()
        self._create_slider_group()
        self._create_status_group()

        self._create_top_layout()
        self._create_bottom_layout()

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
        centralWidget = QWidget()
        centralWidget.setLayout(mainLayout)
        self.setCentralWidget(centralWidget)
        self.setWindowTitle("RX320")

        self.labelConnection = QLabel()
        self.statusBar().addWidget(self.labelConnection)
        self.labelConnection.setText('Disconnected')

        # Signal meter, shown only while connected
        self.progressBarSignal = QProgressBar()
        self.progressBarSignal.setRange(0, self.sdr.SIGNAL_MAX)
        self.progressBarSignal.setFormat('Signal %v')
        self.progressBarSignal.setFixedWidth(160)
        self.progressBarSignal.hide()
        self.statusBar().addPermanentWidget(self.progressBarSignal)

        self.set_controls_enabled(False)

        self._restore_settings()
        self.on_step_changed(self.stepButtonGroup.checkedId())
        self._refresh_labels()

    def _make_button(self, text='', icon=None, slot=None) -> QPushButton:
        btn = QPushButton(text)
        if icon:
            btn.setIcon(QIcon(icon))
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
        spinBox.setRange(self.sdr.MIN_FREQ, self.sdr.MAX_FREQ)
        spinBox.setDecimals(6)
        spinBox.setSuffix(' MHz')
        return spinBox

    def _refresh_serial_ports(self):
        current = self.comboBoxSerialPort.currentText()
        ports = get_serial_ports()
        self.comboBoxSerialPort.clear()
        self.comboBoxSerialPort.addItems(ports)
        if current in ports:
            self.comboBoxSerialPort.setCurrentText(current)

    def _create_top_layout(self):
        labelLogo = QLabel()
        labelLogo.setPixmap(QPixmap(str(IMG_DIR / 'ttrx320.xpm')))

        self.topLayout = QHBoxLayout()
        self.topLayout.addWidget(labelLogo)
        self.topLayout.addWidget(self.statusGroupBox)
        self.topLayout.addStretch(1)

    def _create_bottom_layout(self):
        self.bottomLayout = QHBoxLayout()
        self.comboBoxSerialPort = QComboBox()
        self.comboBoxSerialPort.setMinimumWidth(120)
        self._refresh_serial_ports()

        pushButtonQuit = self._make_button('Quit', slot=self._quit)
        pushButtonConnect = self._make_button('Connect', slot=self._connect)
        pushButtonDisconnect = self._make_button('Disconnect', slot=self._disconnect)
        self.pushButtonMute = self._make_button('Mute', slot=self.on_mute)
        pushButtonRefreshSerialPorts = self._make_button('Refresh', slot=self._refresh_serial_ports)

        self.bottomLayout.addWidget(pushButtonQuit)
        self.bottomLayout.addWidget(self.comboBoxSerialPort)
        self.bottomLayout.addWidget(pushButtonRefreshSerialPorts)
        self.bottomLayout.addWidget(pushButtonConnect)
        self.bottomLayout.addWidget(pushButtonDisconnect)
        self.bottomLayout.addWidget(self.pushButtonMute)

    def _create_vfo_group(self):
        self.vfoGroupBox = QGroupBox()

        pushButtonStepUpUp = self._make_button(icon=str(IMG_DIR / 'up2.xpm'),
                                               slot=lambda: self.on_step_vfo(self.tuningStepMHz * 10.0))

        pushButtonStepUp = self._make_button(icon=str(IMG_DIR / 'up.xpm'),
                                             slot=lambda: self.on_step_vfo(self.tuningStepMHz * 1.0))

        pushButtonStepDownDown = self._make_button(icon=str(IMG_DIR / 'down2.xpm'),
                                                   slot=lambda: self.on_step_vfo(self.tuningStepMHz * -10.0))

        pushButtonStepDown = self._make_button(icon=str(IMG_DIR / 'down.xpm'),
                                               slot=lambda: self.on_step_vfo(self.tuningStepMHz * -1.0))

        pushButtonVFOSwap = self._make_button('A / B', slot=self.on_vfo_swap)
        pushButtonVFOStore = self._make_button('A -> B', slot=self.on_vfo_store)

        self.dial = QDial()
        self.dial.setValue(0)
        self.dial.setMinimum(-100)
        self.dial.setMaximum(100)
        self.dial.setNotchesVisible(True)
        self.dial.setWrapping(True)
        self.dial.valueChanged.connect(self.on_dial_changed)

        layout = QGridLayout()
        layout.addWidget(pushButtonStepUpUp, 0, 0)
        layout.addWidget(pushButtonStepUp, 1, 0)
        layout.addWidget(pushButtonStepDown, 2, 0)
        layout.addWidget(pushButtonStepDownDown, 3, 0)
        layout.addWidget(self.dial, 0, 1, 4, 3)
        layout.addWidget(pushButtonVFOStore, 4, 0, 1, 2)
        layout.addWidget(pushButtonVFOSwap, 4, 2, 1, 2)
        self.vfoGroupBox.setLayout(layout)

    def _create_slider_group(self):
        self.sliderGroupBox = QGroupBox()

        labelLine = QLabel('Line')
        labelVol = QLabel('Vol')
        labelBW = QLabel('BW')

        self.sliderLine = QSlider(Qt.Orientation.Vertical)
        self.sliderLine.setRange(self.sdr.MIN_VOLUME, 0)
        self.sliderLine.setTickPosition(QSlider.TickPosition.TicksLeft)
        self.sliderLine.setValue(self.sdr.MIN_VOLUME)
        self.sliderLine.valueChanged.connect(self.on_line_level_changed)

        self.sliderVol = QSlider(Qt.Orientation.Vertical)
        self.sliderVol.setRange(self.sdr.MIN_VOLUME, 0)
        self.sliderVol.setTickPosition(QSlider.TickPosition.TicksLeft)
        self.sliderVol.setValue(self.sdr.MIN_VOLUME)
        self.sliderVol.valueChanged.connect(self.on_volume_changed)

        self.sliderBW = QSlider(Qt.Orientation.Vertical)
        self.sliderBW.setRange(0, len(self.Filters) - 1)
        self.sliderBW.setValue(self.Filters.index(self.sdr.DEFAULT_FILTER))
        # Only send the filter (and the retune it triggers) on release, so a
        # fast drag doesn't queue up seconds of serial commands.
        self.sliderBW.setTracking(False)
        self.sliderBW.valueChanged.connect(self.on_bandwidth_changed)
        self.sliderBW.sliderMoved.connect(self.on_bandwidth_moved)

        self.checkBoxLink = QCheckBox("&Link")
        self.checkBoxLink.toggled.connect(self.on_link_toggled)

        layout = QGridLayout()
        layout.addWidget(labelLine, 0, 0)
        layout.addWidget(labelVol, 0, 1)
        layout.addWidget(labelBW, 0, 2)
        layout.addWidget(self.sliderLine, 1, 0)
        layout.addWidget(self.sliderVol, 1, 1)
        layout.addWidget(self.checkBoxLink, 2, 0, 1, 2)
        layout.addWidget(self.sliderBW, 1, 2, 2, 1)

        self.sliderGroupBox.setLayout(layout)

    def _create_status_group(self):
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
        self.spinBoxVFOA.valueChanged.connect(self.on_vfo_a_changed)

        # Filled in by _refresh_labels() once settings are restored
        self.labelMode_Act = QLabel()
        self.labelAGC_Act = QLabel()
        self.labelBW_Act = QLabel()

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

    def on_vfo_a_changed(self, freq):
        self.radio.set_vfo_a(freq)

    def on_mute(self):
        self.sliderLine.setValue(self.sdr.MIN_VOLUME)
        self.sliderVol.setValue(self.sdr.MIN_VOLUME)

    def on_dial_changed(self, value):
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

    def on_line_level_changed(self, value):
        if self.checkBoxLink.isChecked():
            self.sliderVol.setValue(value)
        self.sdr.set_attenuation(value, 'Line')

    def on_volume_changed(self, value):
        if self.checkBoxLink.isChecked():
            self.sliderLine.setValue(value)
        self.sdr.set_attenuation(value, 'Speaker')

    def on_bandwidth_changed(self, filter_id):
        self.sdr.set_filter(self.Filters[filter_id])
        self.labelBW_Act.setText(str(self.Filters[filter_id]))

    def on_bandwidth_moved(self, position):
        # Keep the BW label live while dragging; the radio updates on release
        self.labelBW_Act.setText(str(self.Filters[position]))

    def on_link_toggled(self, checked):
        if checked:
            min_value = min(self.sliderVol.value(), self.sliderLine.value())
            self.sliderVol.setValue(min_value)
            self.sliderLine.setValue(min_value)

    def on_mode_changed(self, mode_id):
        self.sdr.set_mode(self.Modes[mode_id])
        self.labelMode_Act.setText(self.Modes[mode_id])

    def on_agc_changed(self, agc_id):
        self.sdr.set_agc(self.AGCModes[agc_id])
        self.labelAGC_Act.setText(self.AGCModes[agc_id])

    def on_step_changed(self, step_id):
        self.tuningStepMHz = TuningSteps[step_id] / 1000000.0
        # The VFO A spin box arrows and mouse wheel follow the tuning step
        self.spinBoxVFOA.setSingleStep(self.tuningStepMHz)

    def on_step_vfo(self, step):
        self.radio.step_vfo_a(step)
        self._show_vfo()

    def on_vfo_store(self):
        self.radio.store_a_to_b()
        self._show_vfo()

    def on_vfo_swap(self):
        self.radio.swap_vfo()
        self._show_vfo()

    def set_controls_enabled(self, enabled: bool):
        for widget in self._controls:
            widget.setDisabled(not enabled)

    def _quit(self):
        self.close()

    def closeEvent(self, event):
        # Quit and the window's X button both end up here
        self._save_settings()
        self._disconnect()
        super().closeEvent(event)

    def _refresh_labels(self):
        self.labelMode_Act.setText(self.Modes[self.modeButtonGroup.checkedId()])
        self.labelAGC_Act.setText(self.AGCModes[self.agcButtonGroup.checkedId()])
        self.labelBW_Act.setText(str(self.Filters[self.sliderBW.value()]))

    def _save_settings(self):
        # Choices are stored by value (e.g. 'USB', 3000 Hz), not by position.
        # Volume is deliberately not saved: the app always starts muted.
        settings = QSettings(*SETTINGS_SCOPE)
        settings.setValue('window/geometry', self.saveGeometry())
        settings.setValue('serial/port', self.comboBoxSerialPort.currentText())
        settings.setValue('vfo/a', self.radio.vfo_a)
        settings.setValue('vfo/b', self.radio.vfo_b)
        settings.setValue('radio/mode', self.Modes[self.modeButtonGroup.checkedId()])
        settings.setValue('radio/agc', self.AGCModes[self.agcButtonGroup.checkedId()])
        settings.setValue('radio/filter', self.Filters[self.sliderBW.value()])
        settings.setValue('tuning/step', TuningSteps[self.stepButtonGroup.checkedId()])
        settings.setValue('audio/link', self.checkBoxLink.isChecked())

    def _restore_settings(self):
        # Runs before any radio is connected, so it only updates widgets
        # (with signals blocked); _sync_radio_to_gui() sends them on connect.
        # Missing or unrecognised values leave the defaults in place.
        settings = QSettings(*SETTINGS_SCOPE)

        def read(key, value_type, default=None):
            # Missing keys and unconvertible values (e.g. a hand-edited file)
            # both give the default instead of stopping the app from starting
            if not settings.contains(key):
                return default
            try:
                return settings.value(key, type=value_type)
            except TypeError:
                return default

        geometry = read('window/geometry', QByteArray)
        if geometry:
            self.restoreGeometry(geometry)  # Ignores invalid data

        port = read('serial/port', str)
        if port and self.comboBoxSerialPort.findText(port) >= 0:
            self.comboBoxSerialPort.setCurrentText(port)

        self.radio.restore(read('vfo/a', float, self.radio.vfo_a),
                           read('vfo/b', float, self.radio.vfo_b))
        self._show_vfo()

        def restore_choice(key, choices, button_group, value_type):
            value = read(key, value_type)
            if value in choices:
                button_group.button(choices.index(value)).setChecked(True)

        restore_choice('radio/mode', self.Modes, self.modeButtonGroup, str)
        restore_choice('radio/agc', self.AGCModes, self.agcButtonGroup, str)
        restore_choice('tuning/step', TuningSteps, self.stepButtonGroup, float)

        bandwidth = read('radio/filter', int)
        if bandwidth in self.Filters:
            with QSignalBlocker(self.sliderBW):
                self.sliderBW.setValue(self.Filters.index(bandwidth))

        with QSignalBlocker(self.checkBoxLink):
            self.checkBoxLink.setChecked(read('audio/link', bool, False))

    def _connect(self):
        serialPort = self.comboBoxSerialPort.currentText()
        if not serialPort:
            QMessageBox.warning(self, 'No port selected',
                               'No serial port is selected. Click Refresh and try again.')
            return
        try:
            self.sdr.connect(serialPort)
        except (OSError, serial.SerialException) as e:
            QMessageBox.critical(self, 'Connection failed',
                                 f'Could not connect to {serialPort}:\n{e}')
            return
        if not self.sdr.connected:
            QMessageBox.critical(self, 'Connection failed',
                                 f'Could not open {serialPort}.')
            return

        self._sync_radio_to_gui()

        # Enable control surfaces
        self.set_controls_enabled(True)
        self.labelConnection.setText(f'Connected: {serialPort}')
        self.progressBarSignal.show()
        self.statusTimer.start()

    def _sync_radio_to_gui(self):
        # Push every GUI setting to the radio, which the driver has just reset
        # to its power-up defaults. Mode and filter go before the VFO because
        # the tuning command depends on them; volume goes last so the radio
        # doesn't briefly play audio at the wrong frequency.
        self.sdr.set_mode(self.Modes[self.modeButtonGroup.checkedId()])
        self.sdr.set_filter(self.Filters[self.sliderBW.value()])
        self.sdr.set_agc(self.AGCModes[self.agcButtonGroup.checkedId()])
        self.radio.set_vfo_a(self.radio.vfo_a)
        self.sdr.set_attenuation(self.sliderLine.value(), 'Line')
        self.sdr.set_attenuation(self.sliderVol.value(), 'Speaker')

    def _disconnect(self):
        self.statusTimer.stop()

        # Disable control surfaces
        self.set_controls_enabled(False)
        self.labelConnection.setText('Disconnected')
        self.progressBarSignal.hide()
        self.progressBarSignal.reset()

        # Always close the port, even if the connection was already lost
        self.sdr.disconnect()

    def _update_status(self):
        if not self.sdr.connected:
            self._disconnect()
            self.labelConnection.setText('Connection lost')
            QMessageBox.warning(self, 'Connection lost',
                                'Lost connection to the radio. Check the cable and reconnect.')
            return
        # Clamp in case the radio ever reports above the measured full scale
        self.progressBarSignal.setValue(min(self.sdr.signal_strength, self.sdr.SIGNAL_MAX))
