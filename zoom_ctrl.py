from PyQt6.QtCore import Qt, QRect, QLine, QPoint
from PyQt6.QtGui import QBrush, QPen

class ZoomControl:
    def __init__(self,ul_x,ul_y,w,h):
        self.ul_x = ul_x
        self.ul_y = ul_y
        self.width = w
        self.height = h
        self.lr_x = self.ul_x + self.width
        self.lr_y = self.ul_y + self.height

        self.img_width = w
        self.img_height = h

        self.zoom_enable_x = True
        self.zoom_enable_y = True

        self.color = Qt.GlobalColor.blue
        self.line_type = Qt.PenStyle.SolidLine

    def updateImgDims(self, w, h):
        self.img_width = w
        self.img_height = h
        self.resetBoxDims()

    def updateBoxDims(self, cx, cy):
        # create zoom box and limit it to image if necessary
        self.ul_x = cx - int(self.width/2)
        self.ul_y = cy - int(self.height/2)
        self.lr_x = self.ul_x + self.width
        self.lr_y = self.ul_y + self.height

        # box x,y limits (less than 0)
        if self.ul_x < 0:
            self.ul_x = 0
        if self.ul_y < 0:
            self.ul_y = 0

        # box x,y limits (greater than image width and height)
        if self.lr_x > self.img_width-1:
            self.ul_x = self.ul_x - (self.lr_x - (self.img_width-1))
            if self.ul_x < 0:
                self.ul_x = 0
            self.lr_x = self.img_width-1
        if self.lr_y > self.img_height-1:
            self.ul_y = self.ul_y - (self.lr_y - (self.img_height-1))
            if self.ul_y < 0:
                self.ul_y = 0
            self.lr_y = self.img_height-1

        # box w,h limits
        if self.width > self.img_width:
            self.width = self.img_width
        if self.height > self.img_height:
            self.height = self.img_height

        #print("ul_x, ul_y = (" + str(self.ul_x) + "," + str(self.ul_y) + ") cx,cy = (" + str(cx) + "," + str(cy) + ") w,h = (" + str(self.width) + "," + str(self.height) + ")")

    def resetBoxDims(self):
        self.ul_x = 0
        self.ul_y = 0
        self.width = self.img_width
        self.height = self.img_height

    def setZoom(self,cx, cy, multiplier):

        self.width = int(self.width * multiplier)
        self.height = int(self.height * multiplier)
        self.updateBoxDims(cx,cy)

    def draw(self,qpainter):
        qpainter.setPen(QPen(QBrush(self.color), 1, self.line_type))

        # draw bounding box
        qpainter.drawRect(self.ul_x, self.ul_y, self.width, self.height)

        return True

    def getCropRect(self):
        rect = QRect(self.ul_x,self.ul_y,self.width,self.height)
        return rect

    # returns full img-context coordinates (zoom -> full img)
    def getZoomLens(self, x, y):

        zoomFactor_x = self.width/self.img_width
        zoomFactor_y = self.height/self.img_height

        adj_x = self.ul_x + int(x * zoomFactor_x)
        adj_y = self.ul_y + int(y * zoomFactor_y)

        # limits on adjusted point coords
        if adj_x > self.img_width-1:
            adj_x = self.img_width-1
        if adj_y > self.img_height-1:
            adj_y = self.img_height-1

        #print("reg pt = (" + str(x) + "," + str(y) + ") zoom pt = (" + str(adj_x) + "," + str(adj_y) + ")")

        return adj_x, adj_y

    def adjustBrushSize(self, brush_size):
        zoomFactor = self.width/self.img_width
        new_brush_size = brush_size * zoomFactor
        return new_brush_size

    # returns zoom-context coords (full img -> zoom)
    def getFullLens(self, x, y):
        adj_x = (x - self.ul_x) * (self.img_width/self.width)
        adj_y = (y - self.ul_y) * (self.img_height/self.height)

        return adj_x, adj_y