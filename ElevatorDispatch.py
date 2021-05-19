from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QMouseEvent
from PyQt5 import Qt
import ElevatorUI
import sys
from PyQt5.QtWidgets import QApplication


OPEN_DOOR=0 # 开门
CLOSE_DOOR=1 # 关门
DOOR_OPENED=1 # 门在开着
DOOR_CLOSED=0 # 门在关着

class Elevator(QMainWindow,ElevatorUI.Ui_Window):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("Elevator")
        self.setWindowIcon(QIcon("resources/icon/icon.png"))





if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = Elevator()

    win.show()
    sys.exit(app.exec_())