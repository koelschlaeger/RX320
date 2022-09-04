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

import sys

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
        pushButtonMute = QPushButton('Mute')
        self.bottomLayout.addWidget(pushButtonQuit)
        self.bottomLayout.addWidget(pushButtonMute)
        
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

        sliderLine = QSlider(Qt.Vertical, self.sliderGroupBox)
        sliderLine.setRange(-96, 0)
        sliderLine.setTickInterval(12)
        sliderLine.setTickPosition(QSlider.TicksLeft)
        sliderLine.setValue(-64)

        sliderVol = QSlider(Qt.Vertical, self.sliderGroupBox)
        sliderVol.setRange(-96, 0)
        sliderVol.setTickInterval(12)
        sliderVol.setTickPosition(QSlider.TicksLeft)
        sliderVol.setValue(-64)

        sliderBW = QSlider(Qt.Vertical, self.sliderGroupBox)
        sliderBW.setRange(0,31)
        sliderBW.setValue(31)

        sliderPBT = QSlider(Qt.Vertical, self.sliderGroupBox)
        sliderPBT.setRange(0,300)
        sliderPBT.setValue(0)

        checkBoxLink = QCheckBox("&Link")

        layout = QGridLayout()
        layout.addWidget(labelLine, 0, 0)
        layout.addWidget(labelVol, 0, 1)
        layout.addWidget(labelBW, 0, 2)
        layout.addWidget(labelPBT, 0, 3)
        layout.addWidget(sliderLine, 1, 0)
        layout.addWidget(sliderVol, 1, 1)
        layout.addWidget(checkBoxLink, 2, 0, 1, 2)
        layout.addWidget(sliderBW, 1, 2, 2, 1)
        layout.addWidget(sliderPBT, 1, 3, 2, 1)
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
