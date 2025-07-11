from PyQt5 import uic
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QVBoxLayout
from tools import FPGAControl
import pyqtgraph as pg
import numpy as np
import os


class ReaderWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    status = pyqtSignal(str)

    def __init__(self, fpga, folder_path, file_name, numFiles):
        super().__init__()
        self.fpga = fpga
        self.folder_path = folder_path
        self.file_name = file_name
        self.numFiles = numFiles
        self.readFilePath = None

    @pyqtSlot()
    def run(self):
        existing_indices = []
        if os.path.isdir(self.folder_path):
            for fname in os.listdir(self.folder_path):
                if fname.startswith(f"{self.file_name}_") and fname.endswith(".txt"):
                    try:
                        idx = int(fname[5:-4])
                        existing_indices.append(idx)
                    except ValueError:
                        continue
        start_index = max(existing_indices) if existing_indices else 0

        for i in range(self.numFiles):
            file_index = start_index + i + 1
            result = self.fpga.get_data(
                f"{self.folder_path}\\{self.file_name}", file_index - 1
            )
            self.status.emit(result)
            self.progress.emit(i + 1)
        self.status.emit("Data read successfully")
        self.finished.emit()
        self.readFilePath = f"{self.file_name}_{start_index + self.numFiles}.txt"


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
        self.CLKHigh.setDisabled(True)
        self.CLKLow.setDisabled(True)

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

        self.edgeLeft.setText("156")
        self.edgeRight.setText("356")

        self.progressBar.setMinimum(0)
        self.progressBar.setValue(0)

        self.progressBar.hide()

        self.nFiles.setText("1")

        public_documents = os.path.join(
            os.environ.get("PUBLIC", r"C:\Users\Public"), "Documents"
        )
        if os.path.isdir(public_documents):
            self.saveFolderLabel.setText(public_documents)
        else:
            self.saveFolderLabel.setText(
                os.path.join(os.path.expanduser("~"), "Documents")
            )

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
        self.graphWidget.setMouseEnabled(x=False, y=False)

        self.imageWidget = pg.GraphicsLayoutWidget()
        layout = QVBoxLayout(self.imagePlot)
        layout.addWidget(self.imageWidget)

        self.image_file = ""
        self.open_beam_file = ""
        self.decoderMatrixLabel.setText("decoder_matrix.txt")
        self.decoder_matrix = np.zeros((16, 16), dtype=int)
        self.load_decoder_matrix(self.decoderMatrixLabel.text())

        self.image_view = self.imageWidget.addViewBox()
        self.image_view.setAspectLocked(False)
        self.img_item = pg.ImageItem(np.zeros((16, 16)))
        self.image_view.addItem(self.img_item)
        self.image_view.setRange(self.img_item.boundingRect(), padding=0)
        self.image_view.setMouseEnabled(x=False, y=False)

        cmap = pg.colormap.get("viridis")
        lut = cmap.getLookupTable(0.0, 1.0, 256)
        self.img_item.setLookupTable(lut)

        self.color_bar = pg.ColorBarItem(
            values=(0, 1), colorMap=cmap, interactive=False
        )

        self.color_bar.setImageItem(self.img_item)

        self.imageWidget.addItem(self.color_bar)

        self.file_data = {}
        self.readFilePath.setText("")

        self.update_registers()

        self.getData.clicked.connect(self.record_data)
        self.ConvLowInt.textChanged.connect(self.update_time)
        self.ConvHighInt.textChanged.connect(self.update_time)
        self.readFileButton.clicked.connect(self.load_trace_file)
        self.traceNumber.currentTextChanged.connect(self.plot_trace)
        self.writeRegisters.clicked.connect(self.update_registers)
        self.saveFolder.clicked.connect(
            lambda: self.saveFolderLabel.setText(
                QFileDialog.getExistingDirectory(self, "Select Folder")
            )
        )
        self.imageFile.clicked.connect(
            lambda: self.load_file("image_file", self.imageFileLabel)
        )
        self.openBeamFile.clicked.connect(
            lambda: self.load_file("open_beam_file", self.openBeamFileLabel)
        )
        self.decoderMatrix.clicked.connect(self.load_decoder_matrix)
        self.buildImage.clicked.connect(self.build_image)

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
            self.statusBar().showMessage("Registers updated successfully")
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
        if self.fpga:
            try:
                numFiles = int(self.nFiles.text())
                if numFiles <= 0:
                    raise ValueError
                folder_path = self.saveFolderLabel.text()
                if folder_path:
                    self.progressBar.setMaximum(numFiles)
                    self.progressBar.setValue(0)
                    self.progressBar.show()
                    file_name = self.saveFileName.text() or "file"
                    self.thread = QThread()
                    self.worker = ReaderWorker(
                        self.fpga, folder_path, file_name, numFiles
                    )
                    self.worker.moveToThread(self.thread)

                    self.thread.started.connect(self.worker.run)
                    self.worker.progress.connect(self.progressBar.setValue)
                    self.worker.status.connect(self.statusBar().showMessage)
                    self.worker.finished.connect(self.thread.quit)
                    self.worker.finished.connect(self.worker.deleteLater)
                    self.worker.finished.connect(
                        lambda: self.readFilePath.setText(self.worker.readFilePath)
                    )
                    self.worker.finished.connect(
                        lambda: self.load_trace_file(
                            f"{folder_path}/{self.readFilePath.text()}"
                        )
                    )

                    self.worker.finished.connect(
                        lambda: self.load_file(
                            "image_file",
                            self.imageFileLabel,
                            f"{folder_path}/{self.readFilePath.text()}",
                        )
                    )
                    self.worker.finished.connect(self.build_image)

                    self.worker.finished.connect(self.build_image)
                    self.thread.finished.connect(self.thread.deleteLater)
                    self.thread.finished.connect(self.progressBar.hide)
                    self.thread.start()

            except ValueError:
                self.statusBar().showMessage("Invalid number of files")
        else:
            self.statusBar().showMessage("Please update registers first")

    def load_trace_file(self, file_path=None):
        self.file_data = {}
        if not file_path:
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select File",
                "",
                "Text Files (*.txt);;All Files (*)",
                options=options,
            )

        try:
            self.readFilePath.setText(file_path.split("/")[-1])
            with open(file_path) as f:
                lines = f.readlines()
                for line in lines:
                    if line.split(",")[0] not in self.file_data:
                        self.file_data[line.split(",")[0]] = [float(line.split(",")[2])]
                    else:
                        self.file_data[line.split(",")[0]].append(
                            float(line.split(",")[2])
                        )
            if self.traceNumber.currentText() == "--":
                self.traceNumber.setCurrentText("Mean value")
            self.plot_trace()
        except ValueError:
            self.statusBar().showMessage("Invalid file")

    def plot_trace(self):
        if not len(self.file_data) == 0:
            self.graphWidget.clear()
            trace = self.traceNumber.currentText()
            if not (trace == "--"):

                if trace == "Mean value":
                    x = list(range(512))
                    sorted_keys = sorted(
                        self.file_data.keys(), key=lambda x: (x[-1], int(x[:-1]))
                    )
                    y = [
                        self.fpga.convert_adc(np.mean(self.file_data[key]))
                        for key in sorted_keys
                    ]
                    color = "r"
                else:
                    prefix = "0" if int(trace[:-1]) < 10 else ""
                    x = list(range(512))
                    y = self.fpga.convert_adc(
                        np.array(self.file_data[f"{prefix}{trace}"])
                    )
                    color = "b"

                self.graphWidget.plot(
                    x,
                    y,
                    pen=pg.mkPen(color, width=1),
                    symbol="o",
                    symbolSize=10,
                    symbolBrush=color,
                )

    def load_file(self, attribute_name, label, file_path=None):
        if not file_path:
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select File",
                "",
                "Text Files (*.txt);;All Files (*)",
                options=options,
            )
        try:
            setattr(self, attribute_name, file_path)
            label.setText(file_path.split("/")[-1])
        except ValueError:
            self.statusBar().showMessage("Invalid file")

    def process_file(self, file_path):
        if file_path:
            with open(file_path) as f:
                peaks = {}
                for i, line in enumerate(f.readlines()):
                    if line.split(",")[0] not in peaks:
                        peaks[line.split(",")[0]] = [
                            self.fpga.convert_adc(float(line.split(",")[2]))
                        ]
                    else:
                        peaks[line.split(",")[0]].append(
                            self.fpga.convert_adc(float(line.split(",")[2]))
                        )
                try:
                    if (
                        int(self.edgeLeft.text()) < 0
                        or int(self.edgeRight.text()) > 512
                        or int(self.edgeLeft.text()) >= int(self.edgeRight.text())
                    ):
                        raise ValueError
                    for key, value in peaks.items():
                        peaks[key] = np.mean(
                            value[int(self.edgeRight.text()) :]
                        ) - np.mean(value[: int(self.edgeLeft.text())])
                except ValueError:
                    self.statusBar().showMessage("Invalid edge values")
                    return np.zeros((16, 16))

                array = np.zeros((16, 16))
                for i in range(16):
                    for j in range(16):
                        if self.decoder_matrix[i, j] >= 10:
                            array[i, j] = peaks[f"{self.decoder_matrix[i,j]}A"]
                        else:
                            array[i, j] = peaks[f"0{self.decoder_matrix[i,j]}A"]
                array = np.fliplr(array)

                return array
        else:
            return np.zeros((16, 16))

    def load_decoder_matrix(self, file_path=None):
        if not file_path:
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select File",
                "",
                "Text Files (*.txt);;All Files (*)",
                options=options,
            )
        try:
            with open(file_path) as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    self.decoder_matrix[i, :] = list(map(int, line.split()))
            self.decoderMatrixLabel.setText(file_path.split("/")[-1])
        except ValueError:
            self.statusBar().showMessage("Invalid file")

    def build_image(self):
        if self.useNormalization.isChecked():
            if (not self.image_file) or (not self.open_beam_file):
                self.statusBar().showMessage(
                    "Please select both image and open beam files"
                )
            else:
                final_image = self.process_file(self.image_file) / self.process_file(
                    self.open_beam_file
                )
                if self.useThreshold.isChecked():
                    final_image[final_image > 1] = 1

                self.img_item.setImage(final_image)
                if np.isnan(final_image.min()) or np.isnan(final_image.max()):
                    self.img_item.setLevels((0, 1))
                    self.color_bar.setLevels((0, 1))
                else:
                    self.img_item.setLevels((final_image.min(), final_image.max()))
                    self.color_bar.setLevels((final_image.min(), final_image.max()))
        else:
            if not self.image_file:
                self.statusBar().showMessage("Please select image file")
            else:
                final_image = self.process_file(self.image_file)
                self.img_item.setImage(final_image)
                if np.isnan(final_image.min()) or np.isnan(final_image.max()):
                    self.img_item.setLevels((0, 1))
                    self.color_bar.setLevels((0, 1))
                else:
                    self.img_item.setLevels((final_image.min(), final_image.max()))
                    self.color_bar.setLevels((final_image.min(), final_image.max()))
