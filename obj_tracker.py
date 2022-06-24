
import cv2

import numpy as np
from PyQt6.QtCore import Qt, QRect, QLine, QPoint, QSize
from PyQt6.QtGui import QImage
import copy
from bbox import BBox

class ObjectTracker:
    def __init__(self):

        # these are the dims used for object detection
        # (completely separate from display dims)
        self.predict_img_width = 800
        self.predict_img_height = 600

        #only choose one type of tracker

        #self.tracker = cv2.TrackerKCF_create()  # bad
        #self.tracker = cv2.TrackerGOTURN_create()  # not very good, requires NN (slow)
        #self.tracker = cv2.TrackerMIL_create()  # good but slow
        #self.tracker = cv2.TrackerBoosting_create()  # good, but HELLA SLOW
        #self.tracker = cv2.TrackerTLD_create()  # fast, but hops around a lot

        #self.tracker = cv2.TrackerMOSSE_create()   # reasonable accuracy, fast
        self.tracker = cv2.legacy.TrackerMedianFlow_create()  # good, and fast - Best for this app
        #self.tracker = cv2.TrackerCSRT_create()    # very good accuracy, not fast

    def QImage2cvMat(self, image):  # (QImage image)
        mat = None  # cv2.Mat

        #image = image.scaled(QSize(800,600))
        image = image.scaled(QSize(self.predict_img_width,self.predict_img_height))

        img_frm = image.format()

        height = image.height()
        width = image.width()
        channels = 3
        #bytecount = image.byteCount()
        bytecount = width*height*channels

        ptr = image.bits()
        ptr.setsize(bytecount)
        mat = np.array(ptr).reshape(height, width, channels)
        mat = cv2.cvtColor(mat, cv2.COLOR_BGR2RGB)

        return mat


    def predict_bbox(self, prevQImg, newQImg, bbox):

        # create opencv Mat imgs from PyQt QImages
        prevMatImg = self.QImage2cvMat(prevQImg)
        newMatImg = self.QImage2cvMat(newQImg)

        # debug - show mat images
        #cv2.imshow("objdetector: prev", prevMatImg)
        #cv2.imshow("objdetector: new", newMatImg)

        # first, make a detect copy of the bbox, and adjust to detect dims
        predict_bbox = copy.deepcopy(bbox)
        predict_bbox.set_img_dims(self.predict_img_width,self.predict_img_height)
        predict_bbox.update_cx_cy_w_h()

        # debug - show prev mat image with bounding box on it
        # pt1 = (int(predict_bbox.cx - (predict_bbox.w/2)), int(predict_bbox.cy - (predict_bbox.h/2)))
        # pt2 = (int(predict_bbox.cx + (predict_bbox.w/2)), int(predict_bbox.cy + (predict_bbox.h/2)))
        # color = (255,255,0)
        # cv2.rectangle(prevMatImg,pt1,pt2,color,2)
        # cv2.imshow("rect_on_image", prevMatImg)

        # create opencv rectangle from bbox
        predict_bbox.align_corners()   # for inverted rectangles, make sure bbox corners are aligned

        # form coordinates of prediction rectangle (IMPORTANT: use float coords for tracker input)
        x = float(predict_bbox.cx) - float(predict_bbox.w)/2
        y = float(predict_bbox.cy) - float(predict_bbox.h)/2
        w = float(predict_bbox.w)
        h = float(predict_bbox.h)

        # initialize tracker with rectangle and predict new bbox
        self.tracker.init(prevMatImg,(x, y, w, h))
        ok, new_box = self.tracker.update(newMatImg)

        if ok == True:
            new_x1 = new_box[0]
            new_y1 = new_box[1]
            new_w = new_box[2]
            new_h = new_box[3]
            new_x2 = new_x1 + new_w
            new_y2 = new_y1 + new_h

            # debug - show new mat image with bounding box on it
            # new_pt1 = (new_x1, new_y1)
            # new_pt2 = (new_x2, new_y2)
            # new_color = (255, 0, 0)
            # cv2.rectangle(newMatImg,pt1,pt2,color,2)
            # cv2.rectangle(newMatImg, new_pt1, new_pt2, new_color, 2)
            # cv2.imshow("rects_on_New_image", newMatImg)

            # round output dims to nearest int and store in new bbox
            predict_bbox.cx = int(round(new_x1 + (new_w/2)))
            predict_bbox.cy = int(round(new_y1 + (new_h/2)))
            predict_bbox.w = int(round(new_w))
            predict_bbox.h = int(round(new_h))
            predict_bbox.update_ul_lr()

            # reset image dims to that of original bbox
            predict_bbox.set_img_dims(bbox.img_width,bbox.img_height)
            predict_bbox.update_cx_cy_w_h()

            #print("bbox: (" + str(bbox.cx) + "," + str(bbox.cy) + ") predict_bbox: (" + str(predict_bbox.cx) + "," + str(predict_bbox.cy) + ")")

        else:
            # if tracking not successful, create deep copy of original bbox
            predict_bbox = copy.deepcopy(bbox)

        return predict_bbox
