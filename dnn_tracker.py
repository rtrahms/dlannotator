import cv2
import numpy as np
from PyQt6.QtCore import Qt, QRect, QLine, QPoint, QSize
from PyQt6.QtGui import QImage
import copy
from bbox import BBox

class DNNTracker:
    def __init__(self, cfgFile, weightsFile, confThresh):

        # these are the dims used for object detection
        # (completely separate from display dims)
        self.predict_img_width = 800
        self.predict_img_height = 600

        self.cfgFile = cfgFile
        self.weightsFile = weightsFile
        self.net = cv2.dnn.readNetFromDarknet(self.cfgFile,self.weightsFile)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self.confThresh = confThresh

        # check if DNN loaded ok
        layer_names = self.net.getLayerNames()
        for l in layer_names:
            print(l)

    def initializeDNN(self,cfgFile, weightsFile, confThresh):
        self.cfgFile = cfgFile
        self.weightsFile = weightsFile
        self.net = cv2.dnn.readNetFromDarknet(self.cfgFile,self.weightsFile)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self.confThresh = confThresh

        # check if DNN loaded ok
        layer_names = self.net.getLayerNames()
        for l in layer_names:
            print(l)

    def QImage2cvMat(self, image):  # (QImage image)
        mat = None  # cv2.Mat

        image = image.scaled(QSize(self.predict_img_width,self.predict_img_height))

        img_frm = image.format()

        height = image.height()
        width = image.width()
        channels = 2
        #bytecount = image.byteCount()
        bytecount = width*height*channels

        ptr = image.bits()
        ptr.setsize(bytecount)
        mat = np.array(ptr).reshape(height, width, channels)
        mat = cv2.cvtColor(mat, cv2.COLOR_BGR2RGB)

        return mat;

    def run_prediction(self, qImg, conf_thresh, label_list):

        # create opencv Mat img from PyQt QImage
        matImg = self.QImage2cvMat(qImg)
        (H, W) = matImg.shape[:2]

        # scale image to input of net
        matImg = cv2.resize(matImg,(416,416))

        # convert Mat img to input blob and assign to net
        inputBlob = cv2.dnn.blobFromImage(matImg, 1/255.0)
        self.net.setInput(inputBlob)

        outputLayerNames = ["yolo_16","yolo_23"]

        # execute inference, combine two output layer groups
        outBlobVec = self.net.forward(outputLayerNames)

        # combine results from both resolutions of yoloV3-Tiny
        outImg = np.concatenate((outBlobVec[0],outBlobVec[1]),axis=0)

        # perform non-maximum suppression to eliminate redundant boxes with lower confidences

        boxes = []
        classIds = []
        confidences = []

        bboxes = []

        for detection in outImg:
            scores = detection[5:]
            classID = np.argmax(scores)
            confidence = scores[classID]

            if confidence > conf_thresh:
                box = detection[0:4] * np.array([W, H, W, H])
                (centerX, centerY, width, height) = box.astype("int")
                x = int(round(float(centerX) - (float(width)/2)))
                y = int(round(float(centerY) - (float(height)/2)))
                w = int(round(width))
                h = int(round(height))

                classIds.append(classID)
                confidences.append(float(confidence))
                boxes.append([x,y,w,h])

        nms_thresh = 0.1
        indices = cv2.dnn.NMSBoxes(boxes,confidences,conf_thresh, nms_thresh)
        for i in indices:
            box = boxes[int(i)]
            classID = classIds[int(i)]
            # TODO: translate confidences

            x = box[0]
            y = box[1]
            w = box[2]
            h = box[3]

            # debug - show new mat image with bounding box on it
            # pt1 = (x, y)
            # pt2 = (x+w, y+h)
            # color = (255, 0, 0)
            # cv2.rectangle(matImg, pt1, pt2, color, 2)

            bbox = BBox()

            bbox.cx = x + (w/2)
            bbox.cy = y + (h/2)
            bbox.w = w
            bbox.h = h
            bbox.update_ul_lr()

            bbox.setStyle(Qt.green, Qt.SolidLine)

            if classID >= 0 and classID < len(label_list):
                bbox.class_name = label_list[classID]
            else:
                bbox.class_name = "Unknown"

            bboxes.append(bbox)

        # debug - show all bboxes on mat img
        #Ecv2.imshow("bboxes_on_mat_image", matImg)

        #print("DNNTracker predictions: " + str(len(bboxes)))
        return bboxes