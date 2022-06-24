import os

from PyQt6 import QtWidgets, QtCore, QtGui, uic
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import QSettings

import yaml
from yaml import FullLoader, Dumper

class SetupDialog(QtWidgets.QDialog):
    def __init__(self):
        super(SetupDialog, self).__init__()

        # enable custom window hint
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.CustomizeWindowHint)

        # disable (but not hide) context help buttons
        #self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint & ~QtCore.Qt.WindowCloseButtonHint)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)

    def loadUi(self,setup_qt_ui, app_icon):
        uic.loadUi(setup_qt_ui, self)
        self.setWindowIcon(QtGui.QIcon(app_icon))

        # setup fields
        self.a5000_yaml_path = "DL Annotator Settings YAML Path Unassigned"
        self.label_a5000_yaml_path = self.findChild(QtWidgets.QLineEdit,"a5000_yaml_path")
        self.label_a5000_yaml_path.setText(self.a5000_yaml_path)
        self.label_a5000_yaml_path.setReadOnly(True)

        self.img_file_path = "Image Folder Unassigned"
        self.label_img_file_path = self.findChild(QtWidgets.QLineEdit,"img_file_path")
        self.label_img_file_path.setText(self.img_file_path)
        self.label_img_file_path.setReadOnly(True)

        self.gt_load_file_path = "GT Load File Path Unassigned"
        self.label_gt_load_file_path = self.findChild(QtWidgets.QLineEdit,"gt_load_file_path")
        self.label_gt_load_file_path.setText(self.gt_load_file_path)
        self.label_gt_load_file_path.setReadOnly(True)

        self.gt_save_file_path = "GT Save File Path Unassigned"
        self.label_gt_save_file_path = self.findChild(QtWidgets.QLineEdit,"gt_save_file_path")
        self.label_gt_save_file_path.setText(self.gt_save_file_path)
        self.label_gt_save_file_path.setReadOnly(True)

        self.label_file_path = "Label File Path Unassigned"
        self.label_labels_file_path = self.findChild(QtWidgets.QLineEdit,"label_file_path")
        self.label_labels_file_path.setText(self.label_file_path)
        self.label_labels_file_path.setReadOnly(True)

        self.dnn_cfg_file_path = "DNN Config File Path Unassigned"
        self.label_dnn_cfg_file_path = self.findChild(QtWidgets.QLineEdit,"dnn_cfg_file_path")
        self.label_dnn_cfg_file_path.setText(self.dnn_cfg_file_path)
        self.label_dnn_cfg_file_path.setReadOnly(True)

        self.dnn_model_file_path = "DNN Model File Path Unassigned"
        self.label_dnn_model_file_path = self.findChild(QtWidgets.QLineEdit,"dnn_model_file_path")
        self.label_dnn_model_file_path.setText(self.dnn_model_file_path)
        self.label_dnn_model_file_path.setReadOnly(True)

        self.event_log_file_path = "Event Log File Path Unassigned"
        self.label_event_log_file_path = self.findChild(QtWidgets.QLineEdit,"event_log_file_path")
        self.label_event_log_file_path.setText(self.event_log_file_path)
        self.label_event_log_file_path.setReadOnly(True)

        self.load_a5000_yaml_button = self.findChild(QtWidgets.QPushButton,"a5000_yaml_load")
        self.load_a5000_yaml_button.clicked.connect(self.load_a5000_yaml)

        self.gt_load_file_path_browse_button = self.findChild(QtWidgets.QPushButton,"gt_load_file_path_browse")
        self.gt_load_file_path_browse_button.clicked.connect(self.browse_gt_load_file_path)

        self.gt_save_file_path_browse_button = self.findChild(QtWidgets.QPushButton,"gt_save_file_path_browse")
        self.gt_save_file_path_browse_button.clicked.connect(self.browse_gt_save_file_path)

    def get_settings_yaml_file_path(self):
        return self.a5000_yaml_path

    def get_img_file_path(self):
        return self.img_file_path

    def get_label_file_path(self):
        return self.label_file_path

    def get_gt_load_file_path(self):
        return self.gt_load_file_path

    def get_gt_save_file_path(self):
        return self.gt_save_file_path

    def get_dnn_cfg_file_path(self):
        return self.dnn_cfg_file_path

    def get_dnn_model_file_path(self):
        return self.dnn_model_file_path

    def get_event_log_file_path(self):
        return self.event_log_file_path

    def refresh_labels(self):
        self.label_a5000_yaml_path.setText(self.a5000_yaml_path)
        self.label_img_file_path.setText(self.img_file_path)
        self.label_labels_file_path.setText(self.label_file_path)
        self.label_gt_load_file_path.setText(self.gt_load_file_path)
        self.label_gt_save_file_path.setText(self.gt_save_file_path)
        self.label_dnn_cfg_file_path.setText(self.dnn_cfg_file_path)
        self.label_dnn_model_file_path.setText(self.dnn_model_file_path)
        self.label_event_log_file_path.setText(self.event_log_file_path)

    def load_a5000_yaml(self):
        #print("load_a5000_yaml() called...")

        # reference last path (if it exists)
        settings = QSettings("Trahms Technologies LLC", "DL Annotator")
        last_path = settings.value("LAST_PATH",".")
        new_yaml_path, _  = QFileDialog.getOpenFileName(self, "DL Annotator YAML File", last_path, "YAML Files (*.yml *.yaml)")

        if new_yaml_path == '':
            return

        # if path selected, save to last path settings var
        settings.setValue("LAST_PATH",os.path.dirname(new_yaml_path))

        # load and read yaml file
        self.a5000_yaml_path = new_yaml_path
        yaml_stream = open(self.a5000_yaml_path, 'r')
        self.dictionary = yaml.load(yaml_stream, Loader=FullLoader)
        yaml_stream.close()

        self.img_file_path = self.dictionary.get("img_file_path")
        self.gt_load_file_path = self.dictionary.get("gt_load_file_path")
        self.gt_save_file_path = self.dictionary.get("gt_save_file_path")
        self.label_file_path = self.dictionary.get("label_file_path")
        self.dnn_cfg_file_path = self.dictionary.get("dnn_cfg_file_path")
        self.dnn_model_file_path = self.dictionary.get("dnn_model_file_path")
        self.event_log_file_path = self.dictionary.get("event_log_file_path")

        for key,value in self.dictionary.items():
            print(key + " : " + str(value))

        self.refresh_labels()

    def browse_gt_load_file_path(self):

        # reference last path (if it exists)
        settings = QSettings("Trahms Technologies LLC", "DL Annotator")
        last_path = settings.value("LAST_PATH",".")

        new_gt_file_path, _  = QFileDialog.getOpenFileName(self, "GT Load File Path", last_path, "Comma-Separated Files (*.csv)")

        if new_gt_file_path == '':
            return

        # if path selected, save to last path settings var
        settings.setValue("LAST_PATH",os.path.dirname(new_gt_file_path))

        self.gt_load_file_path = new_gt_file_path
        self.refresh_labels()

    def browse_gt_save_file_path(self):

        # reference last path (if it exists)
        settings = QSettings("Trahms Technologies LLC", "DL Annotator")
        last_path = settings.value("LAST_PATH",".")

        new_gt_file_path, _  = QFileDialog.getSaveFileName(self, "GT Save File Path", last_path, "Comma-Separated Files (*.csv)")

        if new_gt_file_path == '':
            return

        # if path selected, save to last path settings var
        settings.setValue("LAST_PATH",os.path.dirname(new_gt_file_path))

        self.gt_save_file_path = new_gt_file_path
        self.refresh_labels()
