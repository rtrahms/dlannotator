from PyQt6.QtCore import Qt, QRect, QLine, QPoint
from PyQt6.QtGui import QBrush, QPen
from math import sqrt

class BBox_Line:
    def __init__(self, qp1, qp2):
        self.line = QLine(qp1,qp2)

        self.proximity_thresh = 5

        self.color = Qt.GlobalColor.blue
        self.line_type = Qt.PenStyle.DashDotDotLine

    def setPoints(self, pt1, pt2):
        self.line = QLine(pt1,pt2)

    def setStyle(self, color, line_type):
        self.color = color
        self.line_type = line_type

    # perpendicular distance of point to line
    def calc_distance(self, pt):

        aligned = False

        # check x alignment
        if self.line.p1().x() < self.line.p2().x():
            if self.line.p1().x() <= pt.x() <= self.line.p2().x():
                aligned = True
        else:
            if self.line.p2().x() <= pt.x() <= self.line.p1().x():
                aligned  = True

        # check y alignment
        if self.line.p1().y() < self.line.p2().y():
            if self.line.p1().y() <= pt.y() <= self.line.p2().y():
                aligned = True
        else:
            if self.line.p2().y() <= pt.y() <= self.line.p1().y():
                aligned = True

        # if point is not at all aligned with line, just return very large number
        very_large_number = 100000
        if aligned == False:
            return very_large_number

        x_diff = self.line.p2().x() - self.line.p1().x()
        y_diff = self.line.p2().y() - self.line.p1().y()
        cross1 = self.line.p2().x() * self.line.p1().y()
        cross2 = self.line.p1().x() * self.line.p2().y()

        numerator = abs(y_diff*pt.x() - x_diff*pt.y() + cross1 - cross2)
        denominator = sqrt(y_diff ** 2 + x_diff ** 2)

        return numerator / denominator

    def is_near(self, pt):
        if self.calc_distance(pt) < self.proximity_thresh:
            return True
        else:
            return False

    def draw(self, qpainter):
        qpainter.setPen(QPen(QBrush(self.color), 1, self.line_type))
        qpainter.drawLine(self.line)


class BBox:
    def __init__(self):
        self.class_name = "unassigned"
        self.cx = 0
        self.cy = 0
        self.w = 0
        self.h = 0

        self.ul = QPoint(0,0)
        self.lr = QPoint(0,0)
        self.ur = QPoint(0,0)
        self.ll = QPoint(0,0)
        self.setLines()

        self.img_width = 800
        self.img_height = 600

        self.disp_width = 800
        self.disp_height = 600

        self.x_scale = 1.0
        self.y_scale = 1.0

        self.color = Qt.GlobalColor.green
        self.line_type = Qt.PenStyle.DashLine

        self.move_mode = False
        self.resize_mode = False

        # if resize, which sides are valid to move
        self.top_move = False
        self.bottom_move = False
        self.left_move = False
        self.right_move = False

        self.anchor_point = QPoint()

    def contains(self, point):
        myRect = QRect(self.ul,self.lr)
        return myRect.contains(point)

    def center_from_point(self, point):
        center_x = (self.ul.x() + self.lr.x())/2
        center_y = (self.ul.y() + self.lr.y())/2
        dist_x_sq = (point.x() - center_x) ** 2
        dist_y_sq = (point.y() - center_y) ** 2
        return sqrt(dist_x_sq + dist_y_sq)

    def shortest_proximity(self,point):
        line_prox = []
        line_prox.append(self.top_line.calc_distance(point))
        line_prox.append(self.bottom_line.calc_distance(point))
        line_prox.append(self.left_line.calc_distance(point))
        line_prox.append(self.right_line.calc_distance(point))
        return min(line_prox)

    def setAnchor(self,point):
        self.anchor_point = point

    def move(self,point):
        #print("move x = " + str(point.x()) + ", y = " + str(point.y()))

        # calculate movement from anchor (last touch point)
        delta_x = point.x() - self.anchor_point.x()
        delta_y = point.y() - self.anchor_point.y()

        top_left_x = self.ul.x() + delta_x
        top_left_y = self.ul.y() + delta_y
        bottom_right_x = self.lr.x() + delta_x
        bottom_right_y = self.lr.y() + delta_y

        # update bbox points
        self.ul = QPoint(top_left_x,top_left_y)
        self.lr = QPoint(bottom_right_x,bottom_right_y)
        self.align_ll_ur()

        # update anchor point
        self.anchor_point = point

    def resize(self, point):
        #print("resize x = " + str(point.x()) + ", y = " + str(point.y()))

        # calculate movement from anchor (last touch point)
        delta_x = point.x() - self.anchor_point.x()
        delta_y = point.y() - self.anchor_point.y()

        if self.top_move == True:
            top_left_x = self.ul.x()
            top_left_y = self.ul.y() + delta_y
            top_right_x = self.ur.x()
            top_right_y = self.ur.y() + delta_y

            self.ul = QPoint(top_left_x,top_left_y)
            self.ur = QPoint(top_right_x,top_right_y)

        elif self.bottom_move == True:
            bottom_left_x = self.ll.x()
            bottom_left_y = self.ll.y() + delta_y
            bottom_right_x = self.lr.x()
            bottom_right_y = self.lr.y() + delta_y

            self.ll = QPoint(bottom_left_x,bottom_left_y)
            self.lr = QPoint(bottom_right_x,bottom_right_y)

        elif self.left_move == True:
            top_left_x = self.ul.x() + delta_x
            top_left_y = self.ul.y()
            bottom_left_x = self.ll.x() + delta_x
            bottom_left_y = self.ll.y()

            self.ul = QPoint(top_left_x,top_left_y)
            self.ll = QPoint(bottom_left_x,bottom_left_y)

        elif self.right_move == True:
            top_right_x = self.ur.x() + delta_x
            top_right_y = self.ur.y()
            bottom_right_x = self.lr.x() + delta_x
            bottom_right_y = self.lr.y()

            self.ur = QPoint(top_right_x,top_right_y)
            self.lr = QPoint(bottom_right_x,bottom_right_y)

        self.setLines()
        self.setStyle(Qt.GlobalColor.yellow, Qt.PenStyle.DashLine)

        if self.top_move == True:
            self.top_line.setStyle(Qt.GlobalColor.red,Qt.PenStyle.DashLine)
        elif self.bottom_move == True:
            self.bottom_line.setStyle(Qt.GlobalColor.red,Qt.PenStyle.DashLine)
        elif self.left_move == True:
            self.left_line.setStyle(Qt.GlobalColor.red,Qt.PenStyle.DashLine)
        elif self.right_move == True:
            self.right_line.setStyle(Qt.GlobalColor.red,Qt.PenStyle.DashLine)

        # update anchor point
        self.anchor_point = point

    def finish_change(self):
        self.setStyle(Qt.GlobalColor.green, Qt.PenStyle.SolidLine)

        self.top_move = False
        self.bottom_move = False
        self.left_move = False
        self.right_move = False

        self.move_mode = False
        self.resize_mode = False

    def check_proximity(self,point):
        if self.top_line.is_near(point):
            self.setStyle(Qt.GlobalColor.yellow, Qt.PenStyle.DashLine)
            self.top_line.setStyle(Qt.GlobalColor.red,Qt.PenStyle.DashLine)
            self.top_move = True
            self.resize_mode = True
            self.move_mode = False
            return True
        elif self.bottom_line.is_near(point):
            self.setStyle(Qt.GlobalColor.yellow, Qt.PenStyle.DashLine)
            self.bottom_line.setStyle(Qt.GlobalColor.red,Qt.PenStyle.DashLine)
            self.bottom_move = True
            self.resize_mode = True
            self.move_mode = False
            return True
        elif self.left_line.is_near(point):
            self.setStyle(Qt.GlobalColor.yellow, Qt.PenStyle.DashLine)
            self.left_line.setStyle(Qt.GlobalColor.red,Qt.PenStyle.DashLine)
            self.left_move = True
            self.resize_mode = True
            self.move_mode = False
            return True
        elif self.right_line.is_near(point):
            self.setStyle(Qt.GlobalColor.yellow, Qt.PenStyle.DashLine)
            self.right_line.setStyle(Qt.GlobalColor.red,Qt.PenStyle.DashLine)
            self.right_move = True
            self.resize_mode = True
            self.move_mode = False
            return True

        if self.move_mode == True:
            # no resizing but moving, set style for whole box
            self.setStyle(Qt.GlobalColor.red, Qt.PenStyle.DashLine)
        else:
            # default: set standard style for whole box (static)
            self.setStyle(Qt.GlobalColor.green, Qt.PenStyle.SolidLine)

        return False

    def setTopLeft(self, topLeft):
        self.ul = topLeft
        self.align_ll_ur()

    def setBottomRight(self, bottomRight):
        self.lr = bottomRight
        self.align_ll_ur()

    def setLines(self):
        self.top_line = BBox_Line(self.ul,self.ur)
        self.bottom_line = BBox_Line(self.ll,self.lr)
        self.left_line = BBox_Line(self.ul, self.ll)
        self.right_line = BBox_Line(self.ur,self.lr)

    def setStyle(self, color, line_type):
        self.color = color
        self.line_type = line_type

        # update style to all children lines of bbox
        self.top_line.setStyle(self.color,self.line_type)
        self.bottom_line.setStyle(self.color,self.line_type)
        self.left_line.setStyle(self.color,self.line_type)
        self.right_line.setStyle(self.color,self.line_type)

    # method to convert to inbound scales (usually used for displaying bboxes)
    def update_ul_lr(self):

        x_scale = self.disp_width/self.img_width
        y_scale = self.disp_height/self.img_height

        ul_x = self.cx - (self.w/2)
        ul_y = self.cy - (self.h/2)
        lr_x = self.cx + (self.w/2)
        lr_y = self.cy + (self.h/2)

        # inbound scale adjustment
        ul_x = int(ul_x * x_scale)
        ul_y = int(ul_y * y_scale)
        lr_x = int(lr_x * x_scale)
        lr_y = int(lr_y * y_scale)

        self.ul = QPoint(ul_x, ul_y)
        self.lr = QPoint(lr_x, lr_y)
        self.align_ll_ur()

    # method to store native image dimensions for scaling of bbox dimensions
    def set_img_dims(self, img_width, img_height):
        self.img_width = img_width
        self.img_height = img_height

    def set_disp_dims(self, disp_width, disp_height):
        self.disp_width = disp_width
        self.disp_height = disp_height

    # method to convert to outbound scales (usually prior to saving GT data to file)
    def update_cx_cy_w_h(self, normalize=False):

        # outbound scale adjustment
        if normalize == True:
            x_scale = 1.0/self.disp_width
            y_scale = 1.0/self.disp_height
        else:
            x_scale = self.img_width/self.disp_width
            y_scale = self.img_height/self.disp_height

        center_x = (self.ul.x() + self.lr.x())/2
        center_y = (self.ul.y() + self.lr.y())/2
        width = abs(self.lr.x() - self.ul.x())
        height = abs(self.lr.y() - self.ul.y())

        self.cx = center_x * x_scale
        self.cy = center_y * y_scale
        self.w = width * x_scale
        self.h = height * y_scale

    def align_ll_ur(self):
        self.ll = QPoint(self.ul.x(),self.lr.y())
        self.ur = QPoint(self.lr.x(),self.ul.y())

        # construct ROI lines
        self.setLines()

        # update style to all children lines of bbox
        self.setStyle(self.color,self.line_type)

    def align_corners(self):
        # check left and right corners, swap if necessary
        if self.ul.x() > self.lr.x():
            ul = self.ul
            ll = self.ll
            self.ul = self.ur
            self.ll = self.lr
            self.ur = ul
            self.lr = ll
        # check top and bottom corners, swap if necessary
        if self.ul.y() > self.lr.y():
            ul = self.ul
            ur = self.ur
            self.ul = self.ll
            self.ur = self.lr
            self.ll = ul
            self.lr = ur

    def draw(self, qpainter):
        qpainter.setPen(QPen(QBrush(self.color), 1, self.line_type))

        # draw class for object
        x = self.ul.x()
        y = self.ul.y() - 10
        textPos = QPoint(x, y)
        qpainter.drawText(textPos, self.class_name)

        # draw bounding box
        self.top_line.draw(qpainter)
        self.bottom_line.draw(qpainter)
        self.left_line.draw(qpainter)
        self.right_line.draw(qpainter)

        # draw center point
        cx = int((self.ul.x() + self.lr.x())/2)
        cy = int((self.ul.y() + self.lr.y())/2)
        qpainter.drawRect(cx-1,cy-1,2,2)

        return True