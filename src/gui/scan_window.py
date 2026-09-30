"""Scan window: sweeps a frequency range and plots signal strength live."""

import math

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
        QProgressBar, QPushButton, QSpinBox, QVBoxLayout, QWidget)
import pyqtgraph as pg  # after PyQt6, so pyqtgraph uses the same binding

from .constants import (DEFAULT_SCAN_SAMPLES, DEFAULT_SCAN_SETTLE,
        DEFAULT_SCAN_START, DEFAULT_SCAN_STEP, DEFAULT_SCAN_STOP)
from .scanner import MIN_STEP_HZ, Scanner

POLL_INTERVAL_MS = 20


def format_duration(seconds):
    # 25.4 -> '25 s', 125 -> '2 min 5 s', 3900 -> '1 h 5 min'
    seconds = max(1, round(seconds))
    if seconds < 60:
        return f'{seconds} s'
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f'{minutes} min {seconds} s'
    hours, minutes = divmod(minutes, 60)
    return f'{hours} h {minutes} min'


class ScanWindow(QWidget):
    """Separate window for signal-strength scans. It tunes the radio itself
    while scanning; the main window listens to the signals below to lock its
    own controls and restore the radio afterwards."""

    scanStarted = pyqtSignal()          # emitted before the first tune
    scanFinished = pyqtSignal()         # done, stopped, failed or closed
    tuneRequested = pyqtSignal(float)   # MHz, from clicking the plot

    def __init__(self, sdr, parent=None):
        super().__init__(parent)
        self.sdr = sdr
        self.scanner = None
        self.setWindowTitle('RX320 Scan')

        self.pollTimer = QTimer(self)
        self.pollTimer.setInterval(POLL_INTERVAL_MS)
        self.pollTimer.timeout.connect(self._poll)

        self._create_inputs()
        self._create_plot()

        self.labelStatus = QLabel()
        self.labelRemaining = QLabel()
        self.progressBar = QProgressBar()
        self.progressBar.setFormat('%v / %m')

        status = QHBoxLayout()
        status.addWidget(self.labelStatus)
        status.addWidget(self.progressBar, 1)
        status.addWidget(self.labelRemaining)

        layout = QVBoxLayout()
        layout.addLayout(self.inputLayout)
        layout.addWidget(self.plot, 1)
        layout.addLayout(status)
        self.setLayout(layout)
        self.resize(800, 500)

        self._update_estimate()

    def _create_inputs(self):
        self.spinStart = self._make_freq_box(DEFAULT_SCAN_START)
        self.spinStop = self._make_freq_box(DEFAULT_SCAN_STOP)

        self.spinStep = QDoubleSpinBox()
        self.spinStep.setDecimals(2)
        self.spinStep.setRange(MIN_STEP_HZ / 1000, 1000)
        self.spinStep.setSuffix(' kHz')
        self.spinStep.setValue(DEFAULT_SCAN_STEP)

        self.spinSamples = QSpinBox()
        self.spinSamples.setRange(1, 50)
        self.spinSamples.setValue(DEFAULT_SCAN_SAMPLES)

        self.spinSettle = QSpinBox()
        self.spinSettle.setRange(0, 2000)
        self.spinSettle.setSingleStep(50)
        self.spinSettle.setSuffix(' ms')
        self.spinSettle.setValue(DEFAULT_SCAN_SETTLE)

        self._inputs = [self.spinStart, self.spinStop, self.spinStep,
                        self.spinSamples, self.spinSettle]
        for spin in self._inputs:
            spin.valueChanged.connect(self._update_estimate)

        self.buttonStart = QPushButton('Start')
        self.buttonStart.clicked.connect(self.start_scan)
        self.buttonStop = QPushButton('Stop')
        self.buttonStop.clicked.connect(self.stop_scan)
        self.buttonStop.setEnabled(False)
        self.labelEstimate = QLabel()

        form = QFormLayout()
        form.addRow('Start:', self.spinStart)
        form.addRow('Stop:', self.spinStop)
        form.addRow('Step:', self.spinStep)
        settings = QFormLayout()
        settings.addRow('Samples:', self.spinSamples)
        settings.addRow('Settle:', self.spinSettle)
        buttons = QVBoxLayout()
        buttons.addWidget(self.buttonStart)
        buttons.addWidget(self.buttonStop)
        buttons.addStretch(1)

        self.inputLayout = QHBoxLayout()
        self.inputLayout.addLayout(form)
        self.inputLayout.addLayout(settings)
        self.inputLayout.addWidget(self.labelEstimate, 1)
        self.inputLayout.addLayout(buttons)

    def _make_freq_box(self, value):
        spin = QDoubleSpinBox()
        spin.setRange(self.sdr.MIN_FREQ, self.sdr.MAX_FREQ)
        spin.setDecimals(6)
        spin.setSingleStep(0.1)
        spin.setSuffix(' MHz')
        spin.setValue(value)
        return spin

    def _create_plot(self):
        self.plot = pg.PlotWidget()
        self.plot.setLabel('bottom', 'Frequency', units='MHz')
        self.plot.setLabel('left', 'Signal')
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        # Unreadable steps are NaN: leave a gap rather than a line through them
        self.curve = self.plot.plot(connect='finite')
        # Where click-to-tune tuned the radio; usually right on a peak, so
        # dashed, coloured and labelled to stand out from the curve
        self.marker = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen('#ffb000', width=2, style=Qt.PenStyle.DashLine),
            label='{value:.6f} MHz',
            labelOpts={'position': 0.97, 'color': '#ffb000', 'anchors': [(0, 0), (0, 0)]})
        self.marker.hide()
        self.plot.addItem(self.marker)
        self.plot.scene().sigMouseClicked.connect(self._on_plot_clicked)

    def _plan(self):
        # A Scanner for the current inputs; raises ValueError if they're invalid
        return Scanner(self.sdr, self.spinStart.value(), self.spinStop.value(),
                       self.spinStep.value() / 1000, self.spinSamples.value(),
                       self.spinSettle.value() / 1000)

    def _update_estimate(self):
        try:
            plan = self._plan()
        except ValueError as error:
            self.labelEstimate.setText(f'Invalid scan: {error}')
            self.buttonStart.setEnabled(False)
            return
        steps = len(plan.frequencies)
        self.labelEstimate.setText(
            f'{steps} steps, about {format_duration(plan.estimated_duration())}')
        self.buttonStart.setEnabled(self.scanner is None or self.scanner.finished)

    def _set_scanning(self, scanning):
        for spin in self._inputs:
            spin.setEnabled(not scanning)
        self.buttonStart.setEnabled(not scanning)
        self.buttonStop.setEnabled(scanning)

    def start_scan(self):
        self.scanner = self._plan()
        self._xs, self._ys = [], []
        self.curve.setData([], [])
        self.marker.hide()
        self.plot.setXRange(self.scanner.frequencies[0], self.scanner.frequencies[-1])
        self.progressBar.setRange(0, len(self.scanner.frequencies))
        self.progressBar.setValue(0)
        self.labelStatus.setText('Scanning')
        self._set_scanning(True)

        self.scanStarted.emit()     # before the first tune
        self.scanner.start()
        self.pollTimer.start()
        self._poll()

    def stop_scan(self):
        if self.scanner is not None and not self.scanner.finished:
            self.scanner.stop()
            self._finish()

    def _poll(self):
        if self.scanner.finished:
            self._finish()
            return
        # On the real radio at most one step is ready per tick; loop anyway,
        # so instant measurements (e.g. in tests) don't wait for the timer
        while (point := self.scanner.poll()) is not None:
            self._xs.append(point.freq)
            self._ys.append(math.nan if point.mean is None else point.mean)
        self.curve.setData(self._xs, self._ys)
        self.progressBar.setValue(self.scanner.progress[0])
        if self.scanner.finished:
            self._finish()
        else:
            self.labelRemaining.setText(
                f'about {format_duration(self.scanner.remaining_time())} left')

    def _finish(self):
        self.pollTimer.stop()
        self.labelRemaining.clear()
        if self.scanner.state == 'failed':
            self.labelStatus.setText(f'Connection lost: {self.scanner.error}')
        else:
            self.labelStatus.setText({'done': 'Done', 'stopped': 'Stopped'}
                                     [self.scanner.state])
        self._set_scanning(False)
        self.scanFinished.emit()

    def tune_to(self, freq):
        """Tune to the measured point nearest freq (MHz). Only after a scan:
        while scanning, the scan owns the tuning."""
        if self.scanner is None or not self.scanner.finished:
            return
        point = self.scanner.nearest_point(freq)
        if point is None:
            return
        # Label on the side of the line with room: left of it in the right half
        low, high = self.plot.plotItem.vb.viewRange()[0]
        side = 1 if point.freq > (low + high) / 2 else 0
        self.marker.label.anchors = [(side, 0), (side, 0)]
        self.marker.show()  # first: a hidden marker doesn't update its label
        self.marker.setValue(point.freq)
        self.tuneRequested.emit(point.freq)

    def _on_plot_clicked(self, event):
        view = self.plot.plotItem.vb
        if not view.sceneBoundingRect().contains(event.scenePos()):
            return  # clicked on an axis or label, not the plot area
        self.tune_to(view.mapSceneToView(event.scenePos()).x())

    def closeEvent(self, event):
        self.stop_scan()
        super().closeEvent(event)
