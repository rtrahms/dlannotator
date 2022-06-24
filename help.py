from PyQt6 import QtWidgets, QtCore, QtGui, uic
from PyQt6.QtCore import QDir, Qt, QSize, QRect, QPoint
from PyQt6.QtGui import QImage, QPainter, QPalette, QPixmap, QBrush, QPen

class HelpDialog(QtWidgets.QDialog):
    def __init__(self):
        super(HelpDialog, self).__init__()

        # enable custom window hint
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.CustomizeWindowHint)

        # disable (but not hide) close and context help buttons
        #self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint & ~QtCore.Qt.WindowCloseButtonHint)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)

    def loadUi(self, help_qt_ui, help_image, app_icon):
        uic.loadUi(help_qt_ui, self)
        self.setWindowIcon(QtGui.QIcon(app_icon))

        self.controls_image_pane = self.findChild(QtWidgets.QLabel,"controls_image_pane")
        self.control_image_pane_width = 800
        self.control_image_pane_height = 600

        # load image from file
        self.image = QImage(help_image)
        self.image = self.image.scaled(QSize(self.control_image_pane_width,self.control_image_pane_height))

        self.img_pixmap = QPixmap.fromImage(self.image)

        # blit pixmap to image pane
        self.controls_image_pane.setPixmap(self.img_pixmap)
