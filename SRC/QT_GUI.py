#!/usr/bin/env python

from PyQt5 import * 
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QDateTime, Qt, QTimer, QSize
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
        QDial, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QProgressBar, QPushButton, QRadioButton, QScrollBar, QSizePolicy,
        QSlider, QSpinBox, QStyleFactory, QTableWidget, QTabWidget, QTextEdit,
        QVBoxLayout, QWidget)
#from PyQt5.QtChart import (QChart, QChartView, QHorizontalBarSeries, QBarSet, 
#        QBarCategoryAxis, QValueAxis)

import sys, glob
from MySDR.MySDR import * # was SDR but apparently that is a namespace collision!?!

Modes = ('AM', 'LSB', 'USB', 'CW')
Target = ('Line', 'Speaker', 'Both')
AGCModes = ('Slow', 'Medium', 'Fast')

class MainWindow(QDialog):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.createModeGroupBox()
        self.createAGCGroupBox()
        self.createStepGroupBox()
        self.createVFOGroupBox()
        self.createSliderGroupBox()
        self.createStatusGroupBox()

        self.createTopLayout()
        self.createBottomLayout()
        
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

        self.disableControls()
        # Create SDR instance
        self.sdr = MySDR()

    def createTopLayout(self):
        labelLogo = QLabel()
        labelLogo.setPixmap(QPixmap('IMG/ttrx320.xpm'))

        self.topLayout = QHBoxLayout()
        self.topLayout.addWidget(labelLogo)
        self.topLayout.addWidget(self.statusGroupBox)
        self.topLayout.addStretch(1)

    def createBottomLayout(self):
        self.bottomLayout = QHBoxLayout()
        pushButtonQuit = QPushButton('Quit')
        pushButtonQuit.clicked.connect(self._quit)
        pushButtonConnect = QPushButton('Connect')
        pushButtonConnect.clicked.connect(self._connect)
        pushButtonDisconnect = QPushButton('Disconnect')
        pushButtonDisconnect.clicked.connect(self._disconnect)
        self.pushButtonMute = QPushButton('Mute')
        self.pushButtonMute.clicked.connect(self.pushButtonMute_Clicked)
        self.bottomLayout.addWidget(pushButtonQuit)
        self.bottomLayout.addWidget(pushButtonConnect)
        self.bottomLayout.addWidget(pushButtonDisconnect)
        self.bottomLayout.addWidget(self.pushButtonMute)
        
    def createModeGroupBox(self):
        self.modeGroupBox = QGroupBox("Mode")

        radioButton1 = QRadioButton("AM")
        radioButton2 = QRadioButton("LSB")
        radioButton3 = QRadioButton("USB")
        radioButton4 = QRadioButton("CW")
        radioButton1.setChecked(True)

        layout = QVBoxLayout()
        layout.addWidget(radioButton1)
        layout.addWidget(radioButton2)
        layout.addWidget(radioButton3)
        layout.addWidget(radioButton4)
        layout.addStretch(1)
        self.modeGroupBox.setLayout(layout)

    def createAGCGroupBox(self):
        self.agcGroupBox = QGroupBox("AGC")

        radioButton1 = QRadioButton("Slow")
        radioButton2 = QRadioButton("Med")
        radioButton3 = QRadioButton("Fast")
        radioButton2.setChecked(True)

        layout = QVBoxLayout()
        layout.addWidget(radioButton1)
        layout.addWidget(radioButton2)
        layout.addWidget(radioButton3)
        layout.addStretch(1)
        self.agcGroupBox.setLayout(layout)

    def createVFOGroupBox(self):
        self.vfoGroupBox = QGroupBox()

        pushButtonStepUpUp = QPushButton()
        pushButtonStepUpUp.setIcon(QIcon('IMG/up2.xpm'))

        pushButtonStepUp = QPushButton()
        pushButtonStepUp.setIcon(QIcon('IMG/up.xpm'))

        pushButtonStepDownDown = QPushButton()
        pushButtonStepDownDown.setIcon(QIcon('IMG/down2.xpm'))

        pushButtonStepDown = QPushButton()
        pushButtonStepDown.setIcon(QIcon('IMG/down.xpm'))

        pushButtonVFOSwap = QPushButton('A / B')
        pushButtonVFOStore = QPushButton('A -> B')

        dial = QDial(self.vfoGroupBox)
        dial.setValue(30)
        dial.setNotchesVisible(True)
        dial.setWrapping(True)

        layout = QGridLayout()
        layout.addWidget(pushButtonStepUpUp, 0, 0)
        layout.addWidget(pushButtonStepUp, 1, 0)
        layout.addWidget(pushButtonStepDown, 2, 0)
        layout.addWidget(pushButtonStepDownDown, 3, 0)
        layout.addWidget(dial, 0, 1, 4, 3)
        layout.addWidget(pushButtonVFOStore, 4, 0, 1, 2)
        layout.addWidget(pushButtonVFOSwap, 4, 2, 1, 2)
        #layout.setRowStretch(5, 1)
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

        self.sliderLine = QSlider(Qt.Vertical, self.sliderGroupBox)
        self.sliderLine.setRange(-96, 0)
        self.sliderLine.setTickInterval(12)
        self.sliderLine.setTickPosition(QSlider.TicksLeft)
        self.sliderLine.setValue(-64)
        self.sliderLine.valueChanged.connect(self.sliderLine_ValueChange)

        self.sliderVol = QSlider(Qt.Vertical, self.sliderGroupBox)
        self.sliderVol.setRange(-96, 0)
        self.sliderVol.setTickInterval(12)
        self.sliderVol.setTickPosition(QSlider.TicksLeft)
        self.sliderVol.setValue(-64)
        self.sliderVol.valueChanged.connect(self.sliderVol_ValueChange)

        self.sliderBW = QSlider(Qt.Vertical, self.sliderGroupBox)
        self.sliderBW.setRange(0,31)
        self.sliderBW.setValue(31)

        self.sliderPBT = QSlider(Qt.Vertical, self.sliderGroupBox)
        self.sliderPBT.setRange(0,300)
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
        #layout.setRowStretch(5, 1)

        self.sliderGroupBox.setLayout(layout)

    def createStatusGroupBox(self):
        self.statusGroupBox = QGroupBox()

        labelMode = QLabel('Mode: ')
        labelAGC = QLabel('AGC: ')
        labelBW = QLabel('BW: ')
        labelVFOA = QLabel('VFO A: 0.000.000')
        labelVFOB = QLabel('VFO B: 0.000.000')

        # set0 = QBarSet('X0')
        # set0.append([1, 2, 3, 4, 5, 6])

        # series = QHorizontalBarSeries()
        # series.append(set0)
        
        # chart = QChart()
        # chart.addSeries(series)
        # chart.setAnimationOptions(QChart.SeriesAnimations)
        
        # axisX = QValueAxis()
        # chart.addAxis(axisX, Qt.AlignBottom)
        # series.attachAxis(axisX)
        # chart.legend().setVisible(False)

        # chartView = QChartView(chart)

        layout = QGridLayout()
        layout.addWidget(labelVFOA, 0, 0, 2, 2)
        layout.addWidget(labelVFOB, 2, 0, 2, 2)
        layout.addWidget(labelMode, 0, 2)
        layout.addWidget(labelAGC, 1, 2)
        layout.addWidget(labelBW, 2, 2)
        # layout.addWidget(chartView, 0, 3, 4, 3)


        self.statusGroupBox.setLayout(layout)

    def pushButtonMute_Clicked(self):
        self.sliderLine.setValue(-96)
        self.sliderVol.setValue(-96)
        # self.sdr.SetAttenuation(-96, 'Both')
    
    def sliderLine_ValueChange(self):
        if self.checkBoxLink.isChecked():
            self.sliderVol.setValue(self.sliderLine.value())
        self.sdr.SetAttenuation(self.sliderLine.value(), 'Line')
        
    def sliderVol_ValueChange(self):
        if self.checkBoxLink.isChecked():
            self.sliderLine.setValue(self.sliderVol.value())
        self.sdr.SetAttenuation(self.sliderVol.value(), 'Speaker')

    def checkBoxLink_Toggled(self):
        if self.checkBoxLink.isChecked():
            Min = min(self.sliderVol.value(), self.sliderLine.value())
            self.sliderVol.setValue(Min)
            self.sliderLine.setValue(Min)

    def enableControls(self):
        self.modeGroupBox.setDisabled(False)
        self.agcGroupBox.setDisabled(False)
        self.stepGroupBox.setDisabled(False)
        self.vfoGroupBox.setDisabled(False)
        self.sliderGroupBox.setDisabled(False)
        self.pushButtonMute.setDisabled(False)

    def disableControls(self):
        self.modeGroupBox.setDisabled(True)
        self.agcGroupBox.setDisabled(True)
        self.stepGroupBox.setDisabled(True)
        self.vfoGroupBox.setDisabled(True)
        self.sliderGroupBox.setDisabled(True)
        self.pushButtonMute.setDisabled(True)

    def _quit(self):
        # Check if serial port still in use
        if self.sdr.Connected:
            self._disconnect()
        
        # QApplication.instance().quit()
        self.close()
    
    def _connect(self):
        # Get Serial Ports
        serialPorts = getSerialPorts()
        self.sdr.Connect('/dev/tty.usbserial-AB0N3GLA')
        
        # Enable control surfaces
        self.enableControls()

    def _disconnect(self):
        # Disable control surfaces
        self.disableControls()

        # Check if serial port still in use
        if self.sdr.Connected:
            self.sdr.Disconnect()

def getSerialPorts():
    # Lists serial port names
    #     :raises EnvironmentError:
    #         On unsupported or unknown platforms
    #     :returns:
    #         A list of the serial ports available on the system
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
