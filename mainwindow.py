from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QVBoxLayout
from tools import FPGAControl
import pyqtgraph as pg
import numpy as np


class Ui(QMainWindow):
    conv_config = {"Free run": 0, "Low": 2, "High": 3}
    ddc_clk_config = {"Running": 1, "Low": 0}
    dclk_config = {"Running": 1, "Low": 0}
    hardware_trigger = {"Disabled": 0, "Enabled": 1}

    def __init__(self):
        super().__init__()

        uic.loadUi("mainwindow.ui", self)

        self.setWindowTitle("DDC264EVM_UI")

        self.ConvLowInt.setText("320")
        self.ConvHighInt.setText("320")

        self.ConvConfig.addItem("Free run")
        self.ConvConfig.addItem("Low")
        self.ConvConfig.addItem("High")

        self.MCLKFreq.setText("80.0")
        self.MCLKFreq.setDisabled(True)

        self.CLKHigh.setText("7")
        self.CLKLow.setText("7")

        self.DDCCLKConfig.addItem("Running")
        self.DDCCLKConfig.addItem("Low")

        self.Format.addItem("20 bit")
        self.Format.addItem("16 bit")

        self.ChannelCount.addItem("0")
        self.ChannelCount.addItem("16")
        self.ChannelCount.addItem("32")
        self.ChannelCount.addItem("64")
        self.ChannelCount.addItem("128")
        self.ChannelCount.addItem("256")
        self.ChannelCount.addItem("512")
        self.ChannelCount.addItem("1024")
        self.ChannelCount.setCurrentText("256")

        self.nDVALIDIgnore.setText("255")
        self.nDVALIDRead.setText("1024")

        self.DCLKHigh.setText("0")
        self.DCLKLow.setText("0")

        self.DCLKConfig.addItem("Running")
        self.DCLKConfig.addItem("Low")

        self.DCLKWait.setText("13000")

        self.HardwareTrigger.addItem("Disabled")
        self.HardwareTrigger.addItem("Enabled")

        self.CLK_CFGHigh.setText("3")
        self.CLK_CFGLow.setText("3")

        self.ADCrange.addItem("150.0")
        self.ADCrange.addItem("100.0")
        self.ADCrange.addItem("50.0")
        self.ADCrange.addItem("12.5")

        self.progressBar.setMinimum(0)
        self.progressBar.setValue(0)

        self.progressBar.hide()

        self.nFiles.setText("1")

        self.traceNumber.addItem("--")
        self.traceNumber.addItem("Mean value")
        for letter in ["A", "B"]:
            for i in range(256):
                self.traceNumber.addItem(f"{i+1}{letter}")
        self.graphWidget = pg.PlotWidget()
        layout = QVBoxLayout(self.tracePlot)
        layout.addWidget(self.graphWidget)
        self.graphWidget.setLabel("left", "Charge", units="C")
        self.graphWidget.setLabel("bottom", "Time")

        self.file_data = []
        self.filePath.setText("")

        self.fpga = None

        self.getData.clicked.connect(self.record_data)
        self.ConvLowInt.textChanged.connect(self.update_time)
        self.ConvHighInt.textChanged.connect(self.update_time)
        self.readFileButton.clicked.connect(self.load_file)
        self.traceNumber.currentTextChanged.connect(self.plot_trace)

        self.show()

    def update_registers(self):
        try:
            if (
                5 * int(self.ConvLowInt.text()) < 1600
                or 5 * int(self.ConvHighInt.text()) < 1600
            ):
                raise ValueError

            self.fpga = FPGAControl(
                5 * int(self.ConvLowInt.text()),
                5 * int(self.ConvHighInt.text()),
                self.conv_config[self.ConvConfig.currentText()],
                int(self.CLKHigh.text()),
                int(self.CLKLow.text()),
                self.ddc_clk_config[self.DDCCLKConfig.currentText()],
                int(self.ChannelCount.currentText()),
                int(self.nDVALIDIgnore.text()),
                int(self.nDVALIDRead.text()),
                int(self.DCLKHigh.text()),
                int(self.DCLKLow.text()),
                self.dclk_config[self.DCLKConfig.currentText()],
                int(self.DCLKWait.text()),
                self.ADCrange.currentText(),
                int(self.Format.currentText()[:-4]),
            )
        except ValueError:
            self.statusBar().showMessage("Invalid input")

    def update_time(self):
        try:
            if self.ConvHighInt.text():
                self.conv_high_int_text.setText(
                    f"us = {int(self.ConvHighInt.text())*5}"
                )
            if self.ConvLowInt.text():
                self.conv_low_int_text.setText(f"us = {int(self.ConvLowInt.text())*5}")
        except ValueError:
            self.statusBar().showMessage("Invalid input")

    def record_data(self):
        self.update_registers()
        if self.fpga:
            try:
                numFiles = int(self.nFiles.text())
                if numFiles <= 0:
                    raise ValueError
                self.progressBar.setMaximum(numFiles)
                self.progressBar.show()
                options = QFileDialog.Options()
                folder_path = QFileDialog.getExistingDirectory(
                    self, "Select Folder", options=options
                )
                for i in range(numFiles):
                    collection_result = self.fpga.get_data(folder_path, i)
                    self.statusBar().showMessage(collection_result)
                    self.progressBar.setValue(i + 1)
                self.progressBar.hide()
                self.statusBar().showMessage("Data read successfully")
            except ValueError:
                self.statusBar().showMessage("Invalid number of files")

    def load_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            "",
            "Text Files (*.txt);;All Files (*)",
            options=options,
        )
        if file_path:
            try:
                self.filePath.setText(file_path.split("/")[-1])
                with open(file_path) as f:
                    lines = f.readlines()
                for line in lines[:512]:
                    self.file_data.append([float(num) for num in line.split()])

                for i, line in enumerate(lines[512:1024]):
                    for j, num in enumerate(line.split()):
                        self.file_data[i].append(float(num))
            except ValueError:
                self.statusBar().showMessage("Invalid file")

    def plot_trace(self):
        if not len(self.file_data) == 0:
            self.graphWidget.clear()
            trace = self.traceNumber.currentText()
            if not (trace == "--"):
                if trace == "Mean value":
                    x = list(range(512))
                    y = [
                        1e-12 * np.mean([row[i] for row in self.file_data])
                        for i in range(512)
                    ]
                    self.graphWidget.plot(
                        x,
                        y,
                        pen=pg.mkPen("r", width=1),
                        symbol="o",
                        symbolSize=10,
                        symbolBrush="r",
                    )
                else:
                    if trace.endswith("A"):
                        column = int(trace[:-1]) - 1
                        x = list(range(512))
                        y = [1e-12 * row[column] for row in self.file_data[:512]]
                    elif trace.endswith("B"):
                        column = int(trace[:-1]) - 1
                        x = list(range(512))
                        y = [1e-12 * row[column] for row in self.file_data[512:1024]]
                    self.graphWidget.plot(
                        x,
                        y,
                        pen=pg.mkPen("b", width=1),
                        symbol="o",
                        symbolSize=10,
                        symbolBrush="b",
                    )
