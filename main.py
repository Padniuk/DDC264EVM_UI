from PyQt5.QtWidgets import QApplication
from mainwindow import Ui
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = Ui()
    app.exec_()
