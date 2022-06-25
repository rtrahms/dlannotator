import copy

from obj_tracker import ObjectTracker
from dnn_tracker import DNNTracker

class GT:
    def __init__(self):

        # trial version flag
        #self.trial_version = True
        self.trial_version = False

        self.trial_max_bboxes = 4

        #self.image_filename = "image.jpg"
        self.image_width = 0
        self.image_height = 0

        self.disp_width = 0
        self.disp_height = 0

        self.bbox_list = []

    def add(self, bbox):
        # limit number of bboxes per image if trial version
        if self.trial_version == True and len(self.bbox_list) >= self.trial_max_bboxes:
            return

        self.bbox_list.append(bbox)
        return True

    def remove(self,bbox):
        if bbox != None:
            self.bbox_list.remove(bbox)

    def delete_last(self):
        if len(self.bbox_list) > 0:
            self.bbox_list.pop()

    def delete_all(self):
        self.bbox_list.clear()

    def num_annotations(self):
        return len(self.bbox_list)

    # returns bbox whose center is closest to the given point
    def bbox_closest_center(self,point):
        if len(self.bbox_list) == 0:
            return None

        center_list = []
        for bb in self.bbox_list:
            dist = bb.center_from_point(point)
            center_list.append(dist)

        min_pos = center_list.index(min(center_list))
        bbox = self.bbox_list[min_pos]
        return bbox

    # returns bbox whose edge is closest to the given point
    def bbox_closest_proximity(self,point):
        if len(self.bbox_list) == 0:
            return None

        prox_list = []
        for bb in self.bbox_list:
            dist = bb.shortest_proximity(point)
            prox_list.append(dist)

        min_pos = prox_list.index(min(prox_list))
        bbox = self.bbox_list[min_pos]
        return bbox

    def bbox_contain(self,point):
        contain_list = []

        # check if any bounding boxes contain the point
        for bb in self.bbox_list:
            if bb.contains(point):
                contain_list.append(bb)

        if len(contain_list) == 0:
            return None
        elif len(contain_list) == 1:
            return contain_list[0]
        else:
            return self.bbox_closest_center(point)

    def bbox_proximity(self, point):
        proximity_list = []

        for bb in self.bbox_list:
            if bb.check_proximity(point):
                proximity_list.append(bb)
                #return bb
        if len(proximity_list) == 0:
            return None
        elif len(proximity_list) == 1:
            return proximity_list[0]
        else:
            return self.bbox_closest_proximity(point)

    def predict_dnn_annotation(self, next_img, dnn_tracker, conf_thresh, label_list):
        self.bbox_list = dnn_tracker.run_prediction(next_img, conf_thresh, label_list)

        for bb in self.bbox_list:
            #update bounding box with current native img dims
            bb.set_img_dims(self.image_width, self.image_height)
            bb.update_cx_cy_w_h()

            #update bbox for display
            bb.set_disp_dims(self.disp_width, self.disp_height)
            bb.update_ul_lr()

    def predict_annotation(self, src_gt, prev_img, next_img, prediction_mode):
        self.bbox_list = []

        for bb in src_gt.bbox_list:

            if prediction_mode == "track":
                # use image tracking to determine new bounding box
                obj_track = ObjectTracker()
                new_bb = obj_track.predict_bbox(prev_img, next_img, bb)
            else:
                # nothing fancy - copy bounding box from src gt
                new_bb = copy.deepcopy(bb)

            # add bounding box to list
            self.bbox_list.append(new_bb)

    def set_img_dims(self, img_width, img_height):
        self.image_width = img_width
        self.image_height = img_height

        for bb in self.bbox_list:
            bb.set_img_dims(img_width,img_height)
            bb.update_ul_lr()

    def set_disp_dims(self, disp_width, disp_height):
        self.disp_width = disp_width
        self.disp_height = disp_height

        for bb in self.bbox_list:
            bb.set_disp_dims(disp_width,disp_height)
            bb.update_ul_lr()

    def draw(self, qpainter):
        #print("bbox_list size = " + str(len(self.bbox_list)))
        for bb in self.bbox_list:
            bb.draw(qpainter)


class GT_Image:
    def __init__(self):

        self.full_path = "unknown"
        self.base_filename = "unknown"
        self.image_width = 800
        self.image_height = 600

        self.disp_width = 800
        self.disp_height = 600

        self.gt = GT()

    def get_gt(self):
        return self.gt

    def refresh_gt_img_dims(self):
        # just strobe img dims to bboxes
        if self.gt != None:
            self.gt.set_img_dims(self.image_width, self.image_height)

    def set_img_dims(self, img_width, img_height):
        self.image_width = img_width
        self.image_height = img_height

        if self.gt != None:
            self.gt.set_img_dims(self.image_width, self.image_height)

    def set_disp_dims(self, disp_width, disp_height):
        self.disp_width = disp_width
        self.disp_height = disp_height

        if self.gt != None:
            self.gt.set_disp_dims(self.disp_width, self.disp_height)
