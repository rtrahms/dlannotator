from PyQt6.QtCore import QDir, Qt, QSize, QRect, QPoint, QThread, QTimer, QUrl
from PyQt6 import QtWidgets, QtCore, QtGui, uic
from PyQt6.QtGui import QImage, QPainter, QPalette, QPixmap, QBrush, QPen, QFont, QDesktopServices
from PyQt6.QtWidgets import (QApplication, QFileDialog, QLabel,
        QMainWindow, QGraphicsView, QMenu, QMessageBox, QScrollArea, QSizePolicy,
        QWidget, QStackedWidget)

import pyautogui

import glob
import sys, os
import time

from zoom_ctrl import ZoomControl
from bbox import BBox
from gt import GT, GT_Image
from dnn_tracker import DNNTracker
from help import HelpDialog
from setup import SetupDialog
from logger import Logger

class GT_Load_Process(QThread):
    def __init__(self):
        QThread.__init__(self)

        self.num_processed = 0
        self.lines = []
        self.gt_image_list = []
        self.base_filename_list = []
        self.disp_width = 0
        self.disp_height = 0

    def __del__(self):
        self.wait()

    def check_progress(self):
        return self.num_processed

    def load_params(self, lines, gt_image_list, base_filename_list, disp_width, disp_height):
        self.lines = lines
        self.gt_image_list = gt_image_list
        self.base_filename_list = base_filename_list
        self.disp_width = disp_width
        self.disp_height = disp_height

    def run(self):

        self.num_processed = 0

        for l in self.lines:

            # strip newline and split line into elements
            curr_list = l.rstrip().split(',')
            img_filename = curr_list[0]
            num_detects = int(curr_list[1])

            # use the alpha order index of the found image files to place the GT info
            gt_index = self.base_filename_list.index(img_filename)

            if gt_index >= 0 and gt_index < len(self.gt_image_list):

                ctr = 2
                for n in range(0,num_detects):
                    # create new BBox
                    new_bbox = BBox()
                    new_bbox.cx = float(curr_list[ctr])
                    new_bbox.cy = float(curr_list[ctr+1])
                    new_bbox.w = float(curr_list[ctr+2])
                    new_bbox.h = float(curr_list[ctr+3])

                    new_bbox.class_name = curr_list[ctr+4]
                    new_bbox.setStyle(Qt.GlobalColor.green,Qt.PenStyle.SolidLine)
                    # note: we cannot tell the bbox the actual image size yet, image hasn't been loaded yet - so defaults to 800x600
                    # bbox image dims get updated just prior to image being displayed - see file_slider_changed()
                    new_bbox.set_disp_dims(self.disp_width, self.disp_height)
                    new_bbox.update_ul_lr()

                    # add it to the list for this image
                    self.gt_image_list[gt_index].gt.bbox_list.append(new_bbox)
                    ctr += 5

            # strobe current img dims to all newly created BBoxes
            self.gt_image_list[gt_index].refresh_gt_img_dims()

            #time.sleep(0.01)
            self.num_processed += 1

        print("gt load thread complete.")

        return


class GT_Save_Process(QThread):
    def __init__(self):
        QThread.__init__(self)

        self.num_processed = 0
        self.save_path = "unknown"
        self.gt_image_list = []

    def __del__(self):
        self.wait()

    def check_progress(self):
        return self.num_processed

    def load_params(self,save_path, gt_image_list):
        self.save_path = save_path
        self.gt_image_list = gt_image_list

    def run(self):

        self.num_processed = 0

        gt_filestream = open(self.save_path,"w")
        for gt_img in self.gt_image_list:
            gt = gt_img.gt
            num_bboxes = len(gt.bbox_list)
            if num_bboxes > 0:
                new_string = gt_img.base_filename + "," + str(num_bboxes)
                for bb in gt.bbox_list:
                    bb_cx_str = "{:.0f}".format(bb.cx)
                    bb_cy_str = "{:.0f}".format(bb.cy)
                    bb_w_str = "{:.0f}".format(bb.w)
                    bb_h_str = "{:.0f}".format(bb.h)

                    new_string = new_string + "," + bb_cx_str + "," + bb_cy_str + "," + bb_w_str + "," + bb_h_str + "," + bb.class_name
                new_string = new_string + "\n"

                #print(new_string)
                gt_filestream.write(new_string)

             # time.sleep(0.01)
            self.num_processed += 1

        gt_filestream.close()

        # wait to be killed
        print("gt save thread complete.")

        return


class Ui(QtWidgets.QMainWindow):

    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi(main_qt_ui, self)
        self.setMouseTracking(True)

        # Trial version flags
        self.tool_version = "1.0.3"
        self.trial_version = False

        if self.trial_version is True:
            self.version_string = "Trial Version"
        else:
            self.version_string = "Licensed Version"

        self.logger = None

        self.label_version_info = self.findChild(QtWidgets.QLabel,"label_version_info")
        self.label_version_info.setText(self.version_string)

        if self.trial_version is True:
            self.label_version_info.setStyleSheet('color: red')
        else:
            self.label_version_info.setStyleSheet('color: green')

        # UI element initialization
        self.img_file_name = "Image File Unassigned"
        self.label_img_file_name = self.findChild(QtWidgets.QLineEdit,"img_file_name")
        self.label_img_file_name.setText(self.img_file_name)
        self.label_img_file_name.setReadOnly(True)
        self.base_img_file_name = self.img_file_name

        self.img_file_num = 0
        self.label_img_file_num = self.findChild(QtWidgets.QLabel,"img_file_num")
        self.label_img_file_num.setText(str(self.img_file_num))

        self.img_files_max = 0
        self.label_img_files_max = self.findChild(QtWidgets.QLabel,"img_files_max")
        self.label_img_files_max.setText("Total Image Files: " + str(self.img_files_max))

        self.img_file_path = "Image Folder Unassigned"

        self.gt_load_file_path = "GT Load File Path Unassigned"
        self.gt_save_file_path = "GT Save File Path Unassigned"
        self.gt_image_list = []
        self.base_img_file_list = []  # used for quick indexing
        self.num_gt_entries = 0
        self.num_gt_processed = 0
        self.gt_loader = None
        self.gt_saver = None
        self.gt_progressbar = self.findChild(QtWidgets.QProgressBar,"gt_progressbar")
        self.gt_progressbar.setValue(0)

        self.current_bbox = None
        self.mod_bbox = None

        self.label_file_path = "Label File Path Unassigned"
        self.label_list = []
        self.class_name = "Unassigned"
        self.label_num = 0
        self.label_class_name = self.findChild(QtWidgets.QLabel,"label_class_name")
        self.label_class_name.setText(self.class_name)
        self.label_class_name.setStyleSheet('color: blue')

        self.dnn_cfg_file_path = "DNN Config File Path Unassigned"
        self.dnn_model_file_path = "DNN Model File Path Unassigned"

        self.num_annotations = "0"
        self.label_num_annotations = self.findChild(QtWidgets.QLineEdit,"num_annotations")
        self.label_num_annotations.setText(self.num_annotations)

        self.cursor_x = 0
        self.cursor_y = 0
        self.label_cur_pos = self.findChild(QtWidgets.QLabel,"label_cur_pos")
        self.label_cursor_pos.setText("(" + str(self.cursor_x) + "," + str(self.cursor_y) + ")")
        self.crosshairs_visible = True

        self.label_native_img_dims = self.findChild(QtWidgets.QLabel,"label_native_img_dims")
        self.label_native_img_dims.setText("Native Image Dims: (0,0)")

        self.image_pane = self.findChild(QtWidgets.QLabel,"image_pane")
        self.image_pane.installEventFilter(self)

        self.image = None
        self.img_pixmap = None
        self.img_pane_width = 800
        self.img_pane_height = 600
        self.label_display_dims = self.findChild(QtWidgets.QLabel,"label_display_dims")
        self.label_display_dims.setText("Display Dims: (" + str(self.img_pane_width) + "," + str(self.img_pane_height) + ")")

        self.load_title()

        self.zoom_ctrl = ZoomControl(0,0,self.img_pane_width, self.img_pane_height)
        self.zoom_mode = False

        self.change_mode = False

        self.setup_button = self.findChild(QtWidgets.QPushButton,"setup_button")
        self.setup_button.clicked.connect(self.setup_mode)
        self.load_files_button = self.findChild(QtWidgets.QPushButton,"load_files_button")
        self.load_files_button.clicked.connect(self.use_settings)
        self.help_button = self.findChild(QtWidgets.QPushButton,"help_button")
        self.help_button.clicked.connect(self.help_mode)

        self.auto_key_mode = False
        self.switch_auto_key_mode = self.findChild(QtWidgets.QCheckBox,"switch_auto_key_mode")
        self.switch_auto_key_mode.toggled.connect(lambda: self.change_auto_key_state(self.switch_auto_key_mode))

        # trial version doesn't have DNN tracking
        if self.trial_version is True:
            self.prediction_methods = ["none"]
        else:
            #self.prediction_methods = ["copy", "track", "dnn"]
            self.prediction_methods = ["copy", "track"]
        self.predict_index = 0
        self.label_prediction_method = self.findChild(QtWidgets.QLabel,"label_prediction_method")
        self.label_prediction_method.setText(self.prediction_methods[self.predict_index])
        if self.trial_version is False:
            self.label_prediction_method.setStyleSheet('color: green')
        else:
            self.label_prediction_method.setStyleSheet('color: red')


        self.save_gt_file_button = self.findChild(QtWidgets.QPushButton,"gt_file_save")
        self.save_gt_file_button.clicked.connect(self.save_gt_data)

        self.normalize_gt_coords = False

        self.file_slider = self.findChild(QtWidgets.QSlider,"file_slider")
        self.file_slider.valueChanged[int].connect(self.file_slider_changed)

        self.label_privacy_policy_url = self.findChild(QtWidgets.QLabel,"label_privacy_policy_url")
        self.label_privacy_policy_url.linkActivated.connect(self.privacy_link)
        self.label_privacy_policy_url.setText('<a href="http://trahmstechnologies.com/index.php/privacy-policy/">Trahms Technologies LLC Data Privacy Policy URL')

        self.help_dialog = HelpDialog()
        self.help_dialog.loadUi(help_qt_ui, help_image, app_icon)
        self.help_dialog.setFixedSize(self.help_dialog.size())  # prevent resizing
        self.help_dialog.hide()

        self.setup_dialog = SetupDialog()
        self.setup_dialog.loadUi(setup_qt_ui,app_icon)
        #self.setup_dialog.setFixedSize(self.setup_dialog.size())  # prevent resizing
        self.setup_dialog.hide()

        self.show()

        self.confThresh = 0.2
        self.dnnTracker = None  #not yet loaded (loaded from YAML config read)

    def load_title(self):
        # load image from file
        self.image = QImage(title_image)
        self.image = self.image.scaled(QSize(self.img_pane_width, self.img_pane_height))
        self.img_pixmap = QPixmap.fromImage(self.image)

        # blit pixmap to image pane
        self.image_pane.setPixmap(self.img_pixmap)

    def privacy_link(self, linkStr):
        QDesktopServices.openUrl(QUrl(linkStr))

    def refresh_labels(self):

        self.label_img_file_num.setText(str(self.img_file_num))
        self.label_img_files_max.setText("Total Image Files: " + str(self.img_files_max))
        self.label_class_name.setText(self.class_name)
        self.label_prediction_method.setText(self.prediction_methods[self.predict_index])
        self.label_display_dims.setText("Display Dims: (" + str(self.img_pane_width) + "," + str(self.img_pane_height) + ")")

        if len(self.gt_image_list) > 0:
            self.label_img_file_name.setText(self.gt_image_list[self.img_file_num].base_filename)
            self.num_annotations = len(self.gt_image_list[self.img_file_num].gt.bbox_list)
            self.label_num_annotations.setText(str(self.num_annotations))
            self.label_native_img_dims.setText("Native Image Dims: (" + str(self.gt_image_list[self.img_file_num].image_width) + "," + str(self.gt_image_list[self.img_file_num].image_height) + ")")

        disp_x, disp_y = self.zoom_ctrl.getZoomLens(self.cursor_x, self.cursor_y)
        self.label_cursor_pos.setText("(" + str(disp_x) + "," + str(disp_y) + ")")

    def change_auto_key_state(self, b):
        if self.logger is not None:
            self.logger.log("Auto key set")

        self.auto_key_mode = not self.auto_key_mode

    def update_image(self):
        #print("update_image...")
        # grab new pixmap from current image
        self.img_pixmap = QPixmap.fromImage(self.image)
        self.img_pixmap = self.img_pixmap.scaled(QSize(self.img_pane_width,self.img_pane_height))

        self.mask_overlay = QPixmap(self.img_pane_width, self.img_pane_height)
        self.mask_overlay.fill(Qt.GlobalColor.transparent)

        self.crosshair_overlay = QPixmap(self.img_pane_width, self.img_pane_height)
        self.crosshair_overlay.fill(Qt.GlobalColor.transparent)

        # draw bboxes on mask overlay
        qp = QtGui.QPainter(self.mask_overlay)
        #qp.begin(self)    # redundant with creating QPainter

        # set font for labeling
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        qp.setFont(font)

        # draw current (adding) bbox
        if self.current_bbox is not None:
            self.current_bbox.draw(qp)

        # draw current (modding) bbox
        if self.mod_bbox is not None:
            self.mod_bbox.draw(qp)

        # draw current GT from the gt list
        if len(self.gt_image_list) > 0:
            self.gt_image_list[self.img_file_num].set_disp_dims(self.img_pane_width,self.img_pane_height)
            self.gt_image_list[self.img_file_num].gt.draw(qp)

        qp.end()

        qp = QtGui.QPainter(self.crosshair_overlay)

        # draw zoombox - debug only
        #self.zoom_ctrl.draw(qp)

        # draw crosshairs on crosshair overlay
        qp.setPen(QPen(QBrush(Qt.GlobalColor.yellow), 1, Qt.PenStyle.DashLine))
        qp.drawLine(0,int(self.cursor_y),self.img_pane_width-1,int(self.cursor_y))
        qp.drawLine(int(self.cursor_x),0,int(self.cursor_x),self.img_pane_height-1)
        qp.end()

        # combine image with mask overlay
        result = QPixmap(self.img_pane_width, self.img_pane_height)
        qp = QtGui.QPainter(result)
        #qp.begin(self)   # redundant with creating QPainter

        qp.drawPixmap(0,0,self.img_pixmap)
        qp.setOpacity(1.0)
        qp.drawPixmap(0,0,self.mask_overlay)
        qp.end()

        # apply zoom box
        rect = self.zoom_ctrl.getCropRect()
        result = result.copy(rect).scaled(QSize(self.img_pane_width,self.img_pane_height))

        # final step: overlay crosshair overlay
        result2 = QPixmap(self.img_pane_width, self.img_pane_height)
        qp = QtGui.QPainter(result2)
        #qp.begin(self)   # redundant with creating QPainter

        qp.drawPixmap(0,0,result)
        qp.setOpacity(1.0)
        if self.crosshairs_visible == True:
            qp.drawPixmap(0,0,self.crosshair_overlay)
        qp.end()

        # blit pixmap to image pane
        self.image_pane.setPixmap(result2)

        self.refresh_labels()

    def load_image_file_util(self, value):

        # bounds check
        if value < 0 or value > self.img_files_max - 1:
             return None

        # construct file path
        full_path_img_file_name = self.gt_image_list[value].full_path
        q_image = QImage(full_path_img_file_name)
        #q_image = q_image.convertToFormat(QImage.Format_Grayscale8)
        q_image = q_image.convertToFormat(QImage.Format.Format_RGB888)

        return q_image


    def load_image_file(self, value):
        self.img_file_num = value
        self.image = self.load_image_file_util(value)

        # record actual native image dimensions before rescale
        img_width = self.image.width()
        img_height = self.image.height()

        if img_width == 0 or img_height == 0:
            self.logger.log("WARNING: file " + self.gt_image_list[value].base_filename + " has zero dimension, using temp dimension")
            print("WARNING: file " + self.gt_image_list[value].base_filename + " has zero dimension, using temp dimension")
            # put stand-in dims for GT
            img_width = 404    # code for no image dim
            img_height = 404   # code for no image dim

        # store actual image dims in GT entry for this image
        self.gt_image_list[value].set_img_dims(img_width,img_height)

        return

    def load_image_file_list(self):

        if os.path.isdir(self.img_file_path) == False:
            return

        self.logger.log("Reading JPG filenames from directory: " + self.img_file_path)

        img_file_list = sorted(glob.glob(self.img_file_path + "/*.jpg"))
        #print(img_file_list)

        for img_fullpath in img_file_list:
            gt_img = GT_Image()
            gt_img.full_path = img_fullpath
            gt_img.base_filename = os.path.basename(img_fullpath)
            self.gt_image_list.append(gt_img)
            self.base_img_file_list.append(gt_img.base_filename)     # used only for quick searching/indexing

        self.img_files_max = len(self.gt_image_list)
        self.img_file_num = 0
        self.logger.log("Number of JPG files identified: " + str(self.img_files_max))

        self.file_slider.setMinimum(0)
        self.file_slider.setMaximum(self.img_files_max-1)
        self.file_slider.setValue(0)

        if self.img_files_max > 0:
            self.load_image_file(0)

        #print("current image native dims = (" + str(self.gt_list[0].image_width) + "," + str(self.gt_list[0].image_height) + ")")

        self.update_image()
        self.refresh_labels()

    def load_dnn(self):
        self.logger.log("Reading DNN - Config file path: " + self.dnn_cfg_file_path)
        self.logger.log("Reading DNN - Model file path: " + self.dnn_model_file_path)

        if os.path.isfile(self.dnn_cfg_file_path) == False:
            self.logger.log(self.dnn_cfg_file_path + " file not found!")
            return

        if os.path.isfile(self.dnn_model_file_path) == False:
            self.logger.log(self.dnn_model_file_path + " file not found!")
            return

        try:
            self.dnnTracker = DNNTracker(self.dnn_cfg_file_path, self.dnn_model_file_path, self.confThresh)
        except (FileNotFoundError):
            return

    def load_label_list(self):
        # reset label_list
        self.label_list = []

        self.label_file_path = self.setup_dialog.get_label_file_path()

        self.logger.log("Reading labels from " + self.label_file_path)

        try:
            label_stream = open(self.label_file_path, "r")
        except (FileNotFoundError):
            self.logger.log(self.label_file_path + " file not found!")
            return

        label = label_stream.readline()
        while label:
            self.label_list.append(label.strip())
            label = label_stream.readline()
        label_stream.close()

        self.logger.log("Number of class labels identified: " + str(len(self.label_list)))
        self.logger.log("Labels:")
        for l in self.label_list:
            self.logger.log(l)

        print(self.label_list)

        if len(self.label_list) > 0:
            self.class_name = self.label_list[0]

        self.refresh_labels()

    def load_gt_data(self):

        # reload gt file path from the setup panel
        # (in case user has changed the name to something different than previously used)
        self.gt_load_file_path = self.setup_dialog.get_gt_load_file_path()

        self.logger.log("loading GT from " + self.gt_load_file_path)

        try:
            fp = open(self.gt_load_file_path)
            lines = fp.readlines()
            fp.close()
            #gt_df = pd.read_csv(self.gt_load_file_path)
        except (FileNotFoundError):
            self.logger.log(self.gt_load_file_path + " file not found!")
            return

        self.num_gt_entries = len(lines)
        self.num_gt_processed = 0
        self.gt_progressbar = self.findChild(QtWidgets.QProgressBar,"gt_progressbar")
        self.gt_progressbar.setValue(0)

        self.logger.log("Number of GT entries identified: " + str(len(lines)))
        print("Number of GT entries identified: " + str(len(lines)))

        # start up gt load thread
        self.gt_loader = GT_Load_Process()
        self.gt_loader.load_params(lines, self.gt_image_list,self.base_img_file_list,self.img_pane_width,self.img_pane_height)
        self.gt_loader.start()

        # start up status timer
        self.generateTimer = QTimer()
        self.generateTimer.timeout.connect(self.check_gt_load)
        self.generateTimer.start(100)

        #self.update_image()
        #self.refresh_labels()

    def check_gt_load(self):
        self.num_gt_processed = self.gt_loader.check_progress()
        percent_done = int((self.num_gt_processed * 100)/self.num_gt_entries)
        self.gt_progressbar = self.findChild(QtWidgets.QProgressBar,"gt_progressbar")
        self.gt_progressbar.setValue(percent_done)

        if self.num_gt_processed < self.num_gt_entries:
            # reset status timer
            self.generateTimer = QTimer()
            self.generateTimer.timeout.connect(self.check_gt_load)
            self.generateTimer.start(100)
        else:
            # all done - stop timer and force redraw
            self.generateTimer.stop()
            self.update_image()
            self.refresh_labels()

        return


    def save_gt_data(self):

        # reload gt file path from the setup panel
        # (in case user has changed the name to something different than previously used)
        self.gt_save_file_path = self.setup_dialog.get_gt_save_file_path()

        if self.gt_save_file_path == "GT Save File Path Unassigned":
            return

        print("save_gt_data() called.  Saving GT to " + self.gt_save_file_path)
        if self.logger is not None:
            self.logger.log("save_gt_data() called.  Saving GT to " + self.gt_save_file_path)

        self.num_gt_processed = 0
        self.gt_progressbar = self.findChild(QtWidgets.QProgressBar,"gt_progressbar")
        self.gt_progressbar.setValue(0)

        # start up gt save thread
        self.gt_saver = GT_Save_Process()
        self.gt_saver.load_params(self.gt_save_file_path,self.gt_image_list)
        self.gt_saver.start()

        # start up status timer
        self.generateTimer = QTimer()
        self.generateTimer.timeout.connect(self.check_gt_save)
        self.generateTimer.start(100)

    def check_gt_save(self):
        self.num_gt_processed = self.gt_saver.check_progress()
        percent_done = int((self.num_gt_processed * 100)/len(self.gt_image_list))
        self.gt_progressbar = self.findChild(QtWidgets.QProgressBar,"gt_progressbar")
        self.gt_progressbar.setValue(percent_done)

        if self.num_gt_processed < len(self.gt_image_list):
            # reset status timer
            self.generateTimer = QTimer()
            self.generateTimer.timeout.connect(self.check_gt_save)
            self.generateTimer.start(100)
        else:
            # all done, stop timer
            self.generateTimer.stop()


        return

    def use_settings(self):

        # reset all variables
        self.image_file_list = []
        self.gt_image_list = []
        self.base_img_file_list = []
        self.label_list = []
        self.img_file_num = 0
        self.img_files_max = 0
        self.file_slider.setValue(0)

        settings_yaml_file_path = self.setup_dialog.get_settings_yaml_file_path()
        if settings_yaml_file_path == "DL Annotator Settings YAML Path Unassigned":
            return


        # load in paths from tool setup panel
        self.img_file_path = self.setup_dialog.get_img_file_path()
        self.label_file_path = self.setup_dialog.get_label_file_path()
        self.gt_load_file_path = self.setup_dialog.get_gt_load_file_path()
        self.gt_save_file_path = self.setup_dialog.get_gt_save_file_path()
        self.dnn_cfg_file_path = self.setup_dialog.get_dnn_cfg_file_path()
        self.dnn_model_file_path = self.setup_dialog.get_dnn_model_file_path()
        self.event_log_file_path = self.setup_dialog.get_event_log_file_path()

        self.logger = Logger(self.event_log_file_path)
        self.logger.log("DL Annotator Event Log")
        self.logger.log("Version " + self.tool_version + " Trial = " + str(self.trial_version))

        self.logger.log("Loading setup file information...")

        # load 'em up!
        self.load_image_file_list()
        self.load_label_list()
        self.load_gt_data()
        self.load_dnn()

    def help_mode(self):
        if self.logger is not None:
            self.logger.log("Help mode, calling up dialog")

        self.help_dialog.show()
        self.help_dialog.raise_()

    def setup_mode(self):
        if self.logger is not None:
            self.logger.log("Setup mode, calling up dialog")

        self.setup_dialog.show()
        self.setup_dialog.raise_()

    def file_slider_changed(self, value):
        if self.img_files_max == 0:
            return

        self.load_image_file(value)

        #print("current image native dims = (" + str(self.gt_list[value].image_width) + "," + str(self.gt_list[value].image_height) + ")")

        self.update_image()

    def draw_processing(self, event):
        if self.image is not None:
            self.update_image()

    def paintEvent(self,event):
        #print("paintEvent x = " + str(self.cursor_x) + ", y = " + str(self.cursor_y))
        return

    def mouse_press_processing(self, event):
        self.cursor_x = event.position().x()
        self.cursor_y = event.position().y()
        disp_x, disp_y = self.zoom_ctrl.getZoomLens(self.cursor_x, self.cursor_y)

        if event.button() is QtCore.Qt.MouseButton.LeftButton:
            #print("Left Mouse Button Press! x = " + str(event.x()) + ", y = " + str(event.y()))

            if self.change_mode is False:
                self.current_bbox = BBox()
                self.current_bbox.setStyle(Qt.GlobalColor.cyan, Qt.PenStyle.DashLine)
                self.current_bbox.setTopLeft(QPoint(disp_x, disp_y))
                self.current_bbox.setBottomRight(QPoint(disp_x, disp_y))
            else:
                cursor_pt = QPoint(disp_x, disp_y)
                # proximity calc all boxes and return one that has the closest edge to the point
                self.mod_bbox = self.gt_image_list[self.img_file_num].gt.bbox_closest_proximity(cursor_pt)
                if self.mod_bbox is not None:
                    self.mod_bbox.setAnchor(QPoint(disp_x, disp_y))
                    # check if box is close *enough* for a resize
                    if self.mod_bbox.check_proximity(cursor_pt) is True:
                        # Remove current copy from list and proceed to resize
                        self.gt_image_list[self.img_file_num].gt.remove(self.mod_bbox)
                        self.mod_bbox.resize_mode = True
                        self.mod_bbox.move_mode = False
                    else:
                        # no edges close enough for a resize, check for any boxes that contain point (moving)
                        self.mod_bbox = self.gt_image_list[self.img_file_num].gt.bbox_contain(cursor_pt)
                        if self.mod_bbox is not None:
                            # Remove current copy from list and proceed to move
                            self.gt_image_list[self.img_file_num].gt.remove(self.mod_bbox)
                            self.mod_bbox.setAnchor(QPoint(disp_x, disp_y))
                            self.mod_bbox.move_mode = True
                            self.mod_bbox.resize_mode = False
                            self.mod_bbox.setStyle(Qt.GlobalColor.red, Qt.PenStyle.DashLine)

        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            #print("Right Mouse Button Press! x =" + str(event.x()) + ", y = " + str(event.y()))

            bbox = self.gt_image_list[self.img_file_num].gt.bbox_contain(QPoint(disp_x, disp_y))
            if bbox is not None:
                self.logger.log("Deleting BBox")
                self.gt_image_list[self.img_file_num].gt.remove(bbox)

        self.draw_processing(event)
        return True

    def mouse_release_processing(self, event):
        self.cursor_x = event.position().x()
        self.cursor_y = event.position().y()
        disp_x, disp_y = self.zoom_ctrl.getZoomLens(self.cursor_x, self.cursor_y)

        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            #print("Left Mouse Button Release! x = " + str(event.x()) + ", y = " + str(event.y()))
            if self.change_mode is False and self.current_bbox is not None:
                self.current_bbox.setStyle(Qt.GlobalColor.green, Qt.PenStyle.SolidLine)
                self.current_bbox.setBottomRight(QPoint(disp_x, disp_y))
                self.current_bbox.class_name = self.class_name

                # update scale on the new bbox
                self.current_bbox.set_img_dims(self.gt_image_list[self.img_file_num].image_width, self.gt_image_list[self.img_file_num].image_height)
                self.current_bbox.set_disp_dims(self.img_pane_width, self.img_pane_height)
                self.current_bbox.update_cx_cy_w_h()

                # add bbox to list and delete the working copy
                self.logger.log("Add new BBox")
                self.gt_image_list[self.img_file_num].gt.add(self.current_bbox)
                self.current_bbox = None
            else:
                if self.mod_bbox != None:
                    # finish move or resize operation
                    self.mod_bbox.finish_change()

                    # update scale on the new bbox
                    self.mod_bbox.set_img_dims(self.gt_image_list[self.img_file_num].image_width, self.gt_image_list[self.img_file_num].image_height)
                    self.mod_bbox.set_disp_dims(self.img_pane_width, self.img_pane_height)
                    self.mod_bbox.update_cx_cy_w_h()

                    # add to the list and delete the working copy
                    self.logger.log("Finish move or change of BBox")
                    self.gt_image_list[self.img_file_num].gt.add(self.mod_bbox)
                    self.mod_bbox = None

        self.draw_processing(event)
        return True

    def mouse_motion_processing(self, event):
        self.cursor_x = event.position().x()
        self.cursor_y = event.position().y()
        disp_x, disp_y = self.zoom_ctrl.getZoomLens(self.cursor_x,self.cursor_y)

        #print("Mouse motion: (" + str(self.cursor_x) + "," + str(self.cursor_y) + ")")

        if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
            if self.change_mode == False and self.current_bbox != None:
                self.current_bbox.setBottomRight(QPoint(disp_x, disp_y))
            else:
                if self.mod_bbox != None:
                    cursor_pt = QPoint(disp_x, disp_y)
                    if self.mod_bbox.move_mode == True:
                        self.mod_bbox.move(cursor_pt)
                    elif self.mod_bbox.resize_mode == True:
                        self.mod_bbox.resize(cursor_pt)

        self.draw_processing(event)
        self.refresh_labels()
        return True

    def resize_processing(self, event):
        self.img_pane_width = event.size().width()
        self.img_pane_height = event.size().height()

        #print("resize event: Image pane : (" + str(self.img_pane_width) + "," + str(self.img_pane_height) + ")")

        if self.logger != None:
            self.logger.log("Image pane resize: (" + str(self.img_pane_width) + "," + str(self.img_pane_height) + ")")

        if self.zoom_ctrl != None:
            self.zoom_ctrl.updateImgDims(self.img_pane_width, self.img_pane_height)

        if self.img_files_max > 0:
            self.draw_processing(event)

        self.refresh_labels()

        return True


    # event method used by the image pane
    def eventFilter(self, source, event):

        if event.type() == QtCore.QEvent.Type.Resize:
            self.resize_processing(event)

        if self.img_files_max == 0:
            return super(Ui, self).eventFilter(source, event)

        if event.type() == QtCore.QEvent.Type.MouseMove:
            self.mouse_motion_processing(event)
        elif event.type() == QtCore.QEvent.Type.Wheel:
            y = event.angleDelta().y()
            if y > 0:
                if self.zoom_mode == True:
                    self.change_zoom(0.75)
                else:
                    self.decrement_label()
            else:
                if self.zoom_mode == True:
                    self.change_zoom(1.5)
                else:
                    self.increment_label()
        elif event.type() == QtCore.QEvent.Type.MouseButtonPress:
            self.mouse_press_processing(event)
        elif event.type() == QtCore.QEvent.Type.MouseButtonRelease:
            self.mouse_release_processing(event)

        return super(Ui, self).eventFilter(source, event)

    def decrement_image(self, event, prediction):
        currVal = self.file_slider.value()
        if (currVal > 0):
            nextVal = currVal - 1
            self.img_file_num = nextVal
            self.file_slider.setValue(nextVal)

            # look at prev and next images
            prev_q_image = self.load_image_file_util(currVal)
            next_q_image = self.load_image_file_util(nextVal)

            if prediction == True:
                if self.prediction_methods[self.predict_index] != "dnn":
                    self.gt_image_list[nextVal].gt.predict_annotation(self.gt_image_list[currVal].gt, prev_q_image, next_q_image, self.prediction_methods[self.predict_index])
                elif self.dnnTracker != None:
                    self.gt_image_list[nextVal].set_disp_dims(self.img_pane_width,self.img_pane_height)
                    self.gt_image_list[nextVal].gt.predict_dnn_annotation(next_q_image, self.dnnTracker, self.confThresh, self.label_list)

            self.draw_processing(event)

    def increment_image(self, event, prediction):
        currVal = self.file_slider.value()
        if (currVal < self.img_files_max - 1):
            nextVal = currVal + 1
            self.img_file_num = nextVal
            self.file_slider.setValue(nextVal)

            # look at prev and next images
            prev_q_image = self.load_image_file_util(currVal)
            next_q_image = self.load_image_file_util(nextVal)

            if prediction == True:
                if self.prediction_methods[self.predict_index] != "dnn":
                    self.gt_image_list[nextVal].gt.predict_annotation(self.gt_image_list[currVal].gt, prev_q_image, next_q_image, self.prediction_methods[self.predict_index])
                elif self.dnnTracker != None:
                    self.gt_image_list[nextVal].set_disp_dims(self.img_pane_width,self.img_pane_height)
                    self.gt_image_list[nextVal].gt.predict_dnn_annotation(next_q_image, self.dnnTracker, self.confThresh, self.label_list)

            self.draw_processing(event)

    def decrement_label(self):
        currVal = self.label_num
        if (currVal > 0):
            self.label_num = currVal - 1
            self.class_name = self.label_list[self.label_num]
            self.logger.log("Changed label to " + self.class_name)
            self.refresh_labels()

    def increment_label(self):
        currVal = self.label_num
        if (currVal < len(self.label_list) - 1):
            self.label_num = currVal + 1
            self.class_name = self.label_list[self.label_num]
            self.logger.log("Changed label to " + self.class_name)
            self.refresh_labels()

    def change_zoom(self, value):
        self.logger.log("Changed zoom: " + str(value))
        disp_x, disp_y = self.zoom_ctrl.getZoomLens(self.cursor_x,self.cursor_y)
        self.zoom_ctrl.setZoom(disp_x, disp_y, value)

        self.update_image()
        self.refresh_labels()

    def keyPressEvent(self, event):
        if self.img_files_max == 0:
            return super(Ui, self).keyPressEvent(event)

        key = event.key()

        if key == Qt.Key.Key_Control:
            self.change_mode = True

            if self.trial_version != True:
                self.zoom_mode = True

        # forward one image - no prediction
        if key == Qt.Key.Key_D:
            self.increment_image(event, False)
            if self.auto_key_mode:
                pyautogui.PAUSE = 0.0
                pyautogui.keyDown("D")

        # back one image - no prediction
        if key == Qt.Key.Key_A:
            self.decrement_image(event, False)
            if self.auto_key_mode:
                pyautogui.PAUSE = 0.0
                pyautogui.keyDown("A")

        # increment label
        if key == Qt.Key.Key_S:
            self.increment_label()

        # decrement label
        if key == Qt.Key.Key_W:
            self.decrement_label()

        # forward one image - with prediction
        if key == Qt.Key.Key_E:
            if self.trial_version == False:
                self.increment_image(event, True)
            else:
                self.increment_image(event,False)

            if self.auto_key_mode:
                pyautogui.PAUSE = 0.0
                pyautogui.keyDown("E")

        # back one image - with prediction
        if key == Qt.Key.Key_Q:
            if self.trial_version == False:
                self.decrement_image(event, True)
            else:
                self.decrement_image(event, False)

            if self.auto_key_mode:
                pyautogui.PAUSE = 0.0
                pyautogui.keyDown("Q")

        # delete last added annotation (regardless of mouse location)
        if key == Qt.Key.Key_R:
            if self.img_files_max > 0:
                self.gt_image_list[self.img_file_num].gt.delete_last()
                self.draw_processing(event)

        # delete all annotations for current image
        if key == Qt.Key.Key_F:
            self.logger.log("Delete all annotations for image " + self.gt_image_list[self.img_file_num].base_filename)
            self.gt_image_list[self.img_file_num].gt.delete_all()
            self.draw_processing(event)

        if key == Qt.Key.Key_X:
            self.crosshairs_visible = not self.crosshairs_visible
            self.draw_processing(event)

        # select tracking method
        if key == Qt.Key.Key_T:

            mod_factor = len(self.prediction_methods)

            self.predict_index = (self.predict_index + 1) % mod_factor

            if self.prediction_methods[self.predict_index] == "copy":
                self.label_prediction_method.setStyleSheet('color: green')
            elif self.prediction_methods[self.predict_index] == "track":
                self.label_prediction_method.setStyleSheet('color: blue')
            elif self.prediction_methods[self.predict_index] == "dnn":
                self.label_prediction_method.setStyleSheet('color: red')

            self.logger.log("GT prediction method set: " + self.prediction_methods[self.predict_index])

            self.refresh_labels()
            self.draw_processing(event)

        return super(Ui, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self.img_files_max == 0:
            return super(Ui, self).keyReleaseEvent(event)

        key = event.key()

        if key == Qt.Key.Key_Control:

            # clean up any move or resize in process
            if self.current_bbox != None:
                self.current_bbox.setStyle(Qt.GlobalColor.green, Qt.PenStyle.SolidLine)
                self.current_bbox.setBottomRight(QPoint(self.cursor_x, self.cursor_y))
                self.current_bbox.class_name = self.class_name

                # add current bbox to list and create a new one
                self.gt_image_list[self.img_file_num].gt.add(self.current_bbox)
                self.current_bbox = None
            elif self.mod_bbox != None:
                # finish move or resize, add to the list and delete the working copy
                self.mod_bbox.finish_change()
                self.gt_image_list[self.img_file_num].gt.add(self.mod_bbox)
                self.mod_bbox = None

            self.change_mode = False
            self.zoom_mode = False

        #self.draw_processing()

        return super(Ui, self).keyReleaseEvent(event)

if __name__ == '__main__':
    resource_base = 'resources/'
    main_qt_ui = resource_base + 'main_window.ui'
    help_qt_ui = resource_base + 'help_dialog.ui'
    setup_qt_ui = resource_base + 'setup_dialog.ui'
    title_image = resource_base + 'dlannotator_titlepage.png'
    help_image = resource_base + 'dlannotator_controls.png'
    app_icon = resource_base + 'TT_Icon.png'

    app = QApplication(sys.argv)
    window = Ui()
    window.setWindowIcon(QtGui.QIcon(app_icon))
    window.show()
    sys.exit(app.exec())
