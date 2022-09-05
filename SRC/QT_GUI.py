#!/usr/bin/env python

from PyQt5 import * 
from PyQt5.QtGui import QIcon, QPixmap, QDoubleValidator
from PyQt5.QtCore import QDateTime, Qt, QTimer, QSize
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
        QDial, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QProgressBar, QPushButton, QRadioButton, QButtonGroup, QSizePolicy,
        QSlider, QSpinBox, QStyleFactory, QTableWidget, QTabWidget, QTextEdit,
        QVBoxLayout, QWidget)
#from PyQt5.QtChart import (QChart, QChartView, QHorizontalBarSeries, QBarSet, 
#        QBarCategoryAxis, QValueAxis)

import sys, glob
from MySDR.MySDR import * # was SDR but apparently that is a namespace collision!?!

Modes = ('AM', 'LSB', 'USB', 'CW')
Target = ('Line', 'Speaker', 'Both')
AGCModes = ('Slow', 'Medium', 'Fast')
TuningSteps = (10.0, 100.0, 1000.0, 5000.0, 10000.0)
Filters = (300, 330, 375, 450, 525, 600, 675, 750, 900, 1050, 1200,
    1350, 1500, 1650, 1800, 1950, 2100, 2250, 2400, 2550, 2700, 2850,
    3000, 3300, 3600, 3900, 4200, 4500, 4800, 5100, 5400, 5700, 6000, 8000)

class MainWindow(QDialog):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        # Create SDR instance
        self.sdr = MySDR()
        self.VFO_A = 0.500;     # MHz
        self.VFO_B = 0.500;     # MHz
        self.dialStart = 0
        self.dialStop = 0

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
        
        self.tuningStepMHz = TuningSteps[self.stepButtonGroup.checkedId()] / 1000000.0

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
        pushButtonQuit.setDefault(False)
        pushButtonQuit.setAutoDefault(False)
        pushButtonQuit.clicked.connect(self._quit)
        pushButtonConnect = QPushButton('Connect')
        pushButtonConnect.setDefault(False)
        pushButtonConnect.setAutoDefault(False)
        pushButtonConnect.clicked.connect(self._connect)
        pushButtonDisconnect = QPushButton('Disconnect')
        pushButtonDisconnect.setDefault(False)
        pushButtonDisconnect.setAutoDefault(False)
        pushButtonDisconnect.clicked.connect(self._disconnect)
        self.pushButtonMute = QPushButton('Mute')
        self.pushButtonMute.setDefault(False)
        self.pushButtonMute.setAutoDefault(False)
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

        self.modeButtonGroup = QButtonGroup(self)
        self.modeButtonGroup.addButton(radioButton1, 0)
        self.modeButtonGroup.addButton(radioButton2, 1)
        self.modeButtonGroup.addButton(radioButton3, 2)
        self.modeButtonGroup.addButton(radioButton4, 3)
        self.modeButtonGroup.buttonClicked.connect(self.modeButtonGroup_ButtonClicked)

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

        pushButtonStepUpUp = QPushButton()
        pushButtonStepUpUp.setIcon(QIcon('IMG/up2.xpm'))
        pushButtonStepUpUp.setDefault(False)
        pushButtonStepUpUp.setAutoDefault(False)
        pushButtonStepUpUp.clicked.connect(lambda: self.pushButtonStep_ButtonClicked(self.tuningStepMHz * 10.0))

        pushButtonStepUp = QPushButton()
        pushButtonStepUp.setIcon(QIcon('IMG/up.xpm'))
        pushButtonStepUp.setDefault(False)
        pushButtonStepUp.setAutoDefault(False)
        pushButtonStepUp.clicked.connect(lambda: self.pushButtonStep_ButtonClicked(self.tuningStepMHz * 1.0))

        pushButtonStepDownDown = QPushButton()
        pushButtonStepDownDown.setIcon(QIcon('IMG/down2.xpm'))
        pushButtonStepDownDown.setDefault(False)
        pushButtonStepDownDown.setAutoDefault(False)
        pushButtonStepDownDown.clicked.connect(lambda: self.pushButtonStep_ButtonClicked(self.tuningStepMHz * -10.0))

        pushButtonStepDown = QPushButton()
        pushButtonStepDown.setIcon(QIcon('IMG/down.xpm'))
        pushButtonStepDown.setDefault(False)
        pushButtonStepDown.setAutoDefault(False)
        pushButtonStepDown.clicked.connect(lambda: self.pushButtonStep_ButtonClicked(self.tuningStepMHz * -1.0))

        pushButtonVFOSwap = QPushButton('A / B')
        pushButtonVFOSwap.setDefault(False)
        pushButtonVFOSwap.setAutoDefault(False)
        pushButtonVFOSwap.clicked.connect(self.pushButtonVFOSwap_ButtonClicked)
        pushButtonVFOStore = QPushButton('A -> B')
        pushButtonVFOStore.setDefault(False)
        pushButtonVFOStore.setAutoDefault(False)
        pushButtonVFOStore.clicked.connect(self.pushButtonVFOStore_ButtonClicked)

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

        self.sliderLine = QSlider(Qt.Vertical, self.sliderGroupBox)
        self.sliderLine.setRange(-96, 0)
        #self.sliderLine.setTickInterval(-12)
        self.sliderLine.setTickPosition(QSlider.TicksLeft)
        self.sliderLine.setValue(-96)
        self.sliderLine.valueChanged.connect(self.sliderLine_ValueChange)

        self.sliderVol = QSlider(Qt.Vertical, self.sliderGroupBox)
        self.sliderVol.setRange(-96, 0)
        #self.sliderVol.setTickInterval(-12)
        self.sliderVol.setTickPosition(QSlider.TicksLeft)
        self.sliderVol.setValue(-96)
        self.sliderVol.valueChanged.connect(self.sliderVol_ValueChange)

        self.sliderBW = QSlider(Qt.Vertical, self.sliderGroupBox)
        self.sliderBW.setRange(0,33)
        self.sliderBW.setValue(33)
        self.sliderBW.valueChanged.connect(self.sliderBW_ValueChange)

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
        labelVFOA = QLabel('VFO A: ')
        labelVFOB = QLabel('VFO B: ')
        
        self.lineEditVFOA = QLineEdit(self)
        self.lineEditVFOA.setValidator(QDoubleValidator())
        self.lineEditVFOA.returnPressed.connect(self.lineEditVFOA_ReturnPressed)
        self.lineEditVFOA.setText(f'{self.VFO_A:6f}')

        self.lineEditVFOB = QLineEdit(self)
        self.lineEditVFOB.setText(f'{self.VFO_B:6f}')
        self.lineEditVFOB.setDisabled(True)

        self.labelMode_Act = QLabel()
        self.labelMode_Act.setText(Modes[self.modeButtonGroup.checkedId()])
        self.labelAGC_Act = QLabel()
        self.labelAGC_Act.setText(AGCModes[self.agcButtonGroup.checkedId()])
        self.labelBW_Act = QLabel()
        self.labelBW_Act.setText(str(Filters[self.sliderBW.value()]))
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
        # layout.addWidget(chartView, 0, 3, 4, 3)


        self.statusGroupBox.setLayout(layout)

    def lineEditVFOA_ReturnPressed(self):
        tempVFO = float(self.lineEditVFOA.text())

        if tempVFO < self.sdr.sdr.MinFreq:
            tempVFO = self.sdr.sdr.MinFreq
        
        if tempVFO > self.sdr.sdr.MaxFreq:
            tempVFO = self.sdr.sdr.MaxFreq

        self.sdr.SetVFO(tempVFO)
        self.VFO_A = tempVFO

    def pushButtonMute_Clicked(self):
        self.sliderLine.setValue(-96)
        self.sliderVol.setValue(-96)
    
    def dial_ValueChanged(self):
        self.dialStop = self.dial.value()
        delta = self.dialStop - self.dialStart
        self.dialStart = self.dialStop
    
    def sliderLine_ValueChange(self):
        if self.checkBoxLink.isChecked():
            self.sliderVol.setValue(self.sliderLine.value())
        self.sdr.SetAttenuation(self.sliderLine.value(), 'Line')
        
    def sliderVol_ValueChange(self):
        if self.checkBoxLink.isChecked():
            self.sliderLine.setValue(self.sliderVol.value())
        self.sdr.SetAttenuation(self.sliderVol.value(), 'Speaker')

    def sliderBW_ValueChange(self):
        id = self.sliderBW.value()
        self.sdr.SetFilter(Filters[id])
        self.labelBW_Act.setText(str(Filters[id]))

    def checkBoxLink_Toggled(self):
        if self.checkBoxLink.isChecked():
            Min = min(self.sliderVol.value(), self.sliderLine.value())
            self.sliderVol.setValue(Min)
            self.sliderLine.setValue(Min)

    def modeButtonGroup_ButtonClicked(self):
        id = self.modeButtonGroup.checkedId()
        self.sdr.SetMode(Modes[id])
        self.labelMode_Act.setText(Modes[id])

    def agcButtonGroup_ButtonClicked(self):
        id = self.agcButtonGroup.checkedId()
        self.sdr.SetAGC(AGCModes[id])
        self.labelAGC_Act.setText(AGCModes[id])

    def stepButtonGroup_ButtonClicked(self):
        id = self.stepButtonGroup.checkedId()
        self.tuningStepMHz = TuningSteps[id] / 1000000.0

    def pushButtonStep_ButtonClicked(self, step):
        tempVFO = self.VFO_A + step

        if tempVFO < self.sdr.sdr.MinFreq:
            tempVFO = self.sdr.sdr.MinFreq
        
        if tempVFO > self.sdr.sdr.MaxFreq:
            tempVFO = self.sdr.sdr.MaxFreq

        self.sdr.SetVFO(tempVFO)
        self.VFO_A = tempVFO
        self.lineEditVFOA.setText(f'{self.VFO_A:6f}')

    def pushButtonVFOStore_ButtonClicked(self):
        self.VFO_B = self.VFO_A
        self.lineEditVFOB.setText(f'{self.VFO_B:6f}')

    def pushButtonVFOSwap_ButtonClicked(self):
        tempVFO = self.VFO_A
        self.VFO_A = self.VFO_B
        self.VFO_B = tempVFO
        self.sdr.SetVFO(self.VFO_A)
        self.lineEditVFOA.setText(f'{self.VFO_A:6f}')
        self.lineEditVFOB.setText(f'{self.VFO_B:6f}')

    def enableControls(self):
        self.modeGroupBox.setDisabled(False)
        self.agcGroupBox.setDisabled(False)
        self.stepGroupBox.setDisabled(False)
        self.vfoGroupBox.setDisabled(False)
        self.sliderGroupBox.setDisabled(False)
        self.pushButtonMute.setDisabled(False)
        self.lineEditVFOA.setDisabled(False)

    def disableControls(self):
        self.modeGroupBox.setDisabled(True)
        self.agcGroupBox.setDisabled(True)
        self.stepGroupBox.setDisabled(True)
        self.vfoGroupBox.setDisabled(True)
        self.sliderGroupBox.setDisabled(True)
        self.pushButtonMute.setDisabled(True)
        self.lineEditVFOA.setDisabled(True)

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
