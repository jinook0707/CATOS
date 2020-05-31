# coding: UTF-8

"""
This is for taking and processing images from cameras in CATOS.

* This file was coded for running training and experimental
sessions with common marmoset monkeys by Jinook Oh
in CogBio dept. University of Vienna in 2016
"""

from time import time, sleep
from datetime import datetime
from copy import copy
from os import path, mkdir
from queue import Queue

import cv2
import numpy as np

from modules.misc_funcs import get_time_stamp, writeFile, chk_fps, chk_msg_q, calc_pt_line_dist

# ======================================================

class VideoIn:
    def __init__(self, parent, cam_idx, pos=(300, 25)):
        self.flagWindow = False # create an opencv window or not
        self.contour_threshold = 40
        # points for Region Of Interest 
        self.roi_pts = [(50,50), (750,50), (750,550), (50,550)] 
        # min & max threshold for wrect (whole bounding rect) of movement
        self.m_wrectTh = (100, 1000) 
        #self.fourcc = cv2.VideoWriter_fourcc('x', 'v', 'i', 'd')
        self.fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
        self.video_rec = None # video recorder
        # time (seconds) of no-motion to stop video recording
        self.time2stop_vr = 3 
        self.parent = parent
        self.cam_idx = cam_idx
        self.cap_cam = cv2.VideoCapture()
        self.cap_cam.open(cam_idx)
        sleep(0.5)
        for i in range(3):
            ret, frame = self.cap_cam.read()
            if ret == True: break
            sleep(0.1)
        self.fSize = (int(frame.shape[1]), int(frame.shape[0]))
        #self.cap_cam.set(3, self.fSize[0]) # set the width of frame
        #self.cap_cam.set(4, self.fSize[1]) # set the height of frame
        self.cap_cam.set(5, 30) # set FPS
        self.msg_q = Queue()
        if self.flagWindow:
            cv2.namedWindow('CATOS_CAM%.2i'%self.cam_idx, cv2.WINDOW_NORMAL)
            cv2.moveWindow('CATOS_CAM%.2i'%self.cam_idx, pos[0], pos[1])
    # --------------------------------------------------

    def run(self, flag_chk_cam_view=False, flag_feeder=False):
        fSz = self.fSize # frame size
        msg = ''
        fps=0; prev_fps=[]; prev_fps_time=time()
        mod_name = 'videoIn-%i'%(self.cam_idx)
        first_run = True
        recent_imgs = [] # buffer to store 60 recent frames
        recent_m = [] # storing whether meaningful movements 
          # happened in the recent 60 frames
        recent_m_time = -1 # time when movements were enough 
          # to start video recording
        log = "%s, [%s],"%(get_time_stamp(), mod_name)
        log += " webcam %i starts."%(self.cam_idx)
        log += " Frame-size: %s\n"%(str(fSz))
        writeFile(self.parent.log_file_path, log)
        sleep(1)
        for i in range(10):
            ret, frame_arr = self.cap_cam.read() # retrieve some images 
              # giving some time to camera to adjust
        ### find ROI with red color 
        ###   (red tape is attached on bottom of side monitors)
        r = (0, 0) + fSz # rect to find the color
        HSV_min = (175,100,90)
        HSV_max = (180,255,255)
        red_col = self.find_color(r, frame_arr, HSV_min, HSV_max, (0,0,0))
        wr, rects = self.chk_contours(red_col, self.contour_threshold)
        if wr == (-1,-1,0,0):
            writeFile(self.parent.log_file_path, "%s, [%s], Red color detection failed.\n"%(get_time_stamp(), mod_name))
            redY = -1
        else:
            redY = int(wr[1]+wr[3]/2) # middle y position of red tape
        bgImg = frame_arr.copy() # store background image
        while True:
            fps, prev_fps, prev_fps_time = chk_fps(mod_name, 
                                                   fps, 
                                                   prev_fps, 
                                                   prev_fps_time, 
                                                   self.parent.log_file_path)
            ret, frame_arr = self.cap_cam.read() # get a new frame
            if ret == False: sleep(0.1); continue

            recent_imgs.append(frame_arr)
            if len(recent_imgs) > 60: recent_imgs.pop(0)
            recent_m.append(False)
            if len(recent_m) > 60: recent_m.pop(0)

            if flag_chk_cam_view == False:
                ### extract subject image by obtaining difference image 
                ###   between the frame_arr and bgImg
                diff = cv2.absdiff(frame_arr, bgImg) 
                diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                __, diff = cv2.threshold(diff, 50, 255, cv2.THRESH_BINARY)
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
                diff = cv2.morphologyEx(diff, 
                                        cv2.MORPH_OPEN, 
                                        kernel, 
                                        iterations=1) # decrease noise and
                                                      # minor features
                #M = cv2.moments(diff)
                #print self.cam_idx, M['m00']/255
                diff = cv2.Canny(diff, 150, 150)
                sbr, rects = self.chk_contours(diff.copy(), 20) # sbr = subject
                                                                # bounding rect
                if sbr != (-1,-1,0,0):
                    cv2.rectangle(frame_arr, 
                                  sbr[:2], 
                                  (sbr[0]+sbr[2],sbr[1]+sbr[3]), 
                                  (0,255,0), 
                                  2)
                    dist_to_s = sbr[1]-redY # distance from red tape(screen) 
                      # to the subject 
                    msg = None
                    if self.cam_idx == 1: # center screen
                        if dist_to_s < 10: msg = 'center'
                        else:
                            sMid = int(sbr[0] + sbr[2]/2)
                            if sMid < int(fSz[0]/6): msg='left'
                            elif sMid > int(fSz[0]-fSz[0]/6): msg='right'
                    else:
                        if dist_to_s < 100: # close to the screen
                            if self.cam_idx == 0: msg='left'
                            else: msg='right'
                            
                    if msg != None and self.parent.mods["session_mngr"] != None:
                        self.parent.mods["session_mngr"].msg_q.put(
                                        "%s/close_to_screen/%s"%(mod_name,msg), 
                                        True, 
                                        None
                                        )
                # red color bottom line
                cv2.line(frame_arr, (0,redY), (640,redY), (0,255,255), 2) 
            else: # chk_cam_view
                pass
                                
            if self.flagWindow:
                if flag_chk_cam_view:
                    cv2.imshow("CATOS_CAM%.2i"%(self.cam_idx), frame_arr)
                else:
                    cv2.imshow("CATOS_CAM%.2i"%(self.cam_idx), frame_arr)
            
            cv2.waitKey(5)
            # listen to a message
            msg_src, msg_body, msg_details = chk_msg_q(self.msg_q) 
            if msg_body == 'quit': break
            
        self.cap_cam.release()
        if self.flagWindow: cv2.destroyWindow("CATOS_CAM%.2i"%(self.cam_idx))
        log = "%s, [%s],"%(get_time_stamp(), mod_name)
        log += " webcam %i stopped.\n"%(self.cam_idx)
        writeFile(self.parent.log_file_path, log)
        if self.video_rec != None: self.video_rec.release()

    # --------------------------------------------------

    def find_color(self, rect, inImage, HSV_min, HSV_max, bgColor=(0,0,0)):
    # Find a color(range: 'HSV_min' ~ 'HSV_max') in an area('rect') of an image('inImage')
    # 'bgcolor' is a background color of the masked image
    # 'rect' here is (x1,y1,x2,y2)
        tmp_grey_img = np.zeros( (inImage.shape[0], inImage.shape[1]) , dtype=np.uint8 )
        tmp_col_img = np.zeros( (inImage.shape[0], inImage.shape[1], 3), dtype=np.uint8 )
        HSV_img = np.zeros( (inImage.shape[0], inImage.shape[1], 3), dtype=np.uint8 )
        tmp_col_img[:,:,:] = bgColor
        tmp_col_img[ rect[1]:rect[3], rect[0]:rect[2], : ] = inImage[ rect[1]:rect[3], rect[0]:rect[2], : ].copy()
        #tmp_col_img = self.preprocessing(tmp_col_img)
        cv2.cvtColor(tmp_col_img, cv2.COLOR_BGR2HSV, HSV_img)
        cv2.inRange(HSV_img, HSV_min, HSV_max, tmp_grey_img)
        return tmp_grey_img

    # --------------------------------------------------

    def chk_contours(self, inImage, contour_threshold):
        contours, hierarchy = cv2.findContours(inImage, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        wrect = [-1,-1,-1,-1] # whole rect, bounding all the contours
        rects = [] # rects, bounding each contour piece
        for ci in range(len(contours)):
            #M = cv2.moments(contours[ci])
            br = cv2.boundingRect(contours[ci])
            if br[2] + br[3] > contour_threshold:
                if wrect[0] == -1 and wrect[1] == -1: wrect[0] = br[0]; wrect[1] = br[1]
                if wrect[2] == -1 and wrect[3] == -1: wrect[2] = br[0]; wrect[3] = br[1]
                if br[0] < wrect[0]: wrect[0] = br[0]
                if br[1] < wrect[1]: wrect[1] = br[1]
                if (br[0]+br[2]) > wrect[2]: wrect[2] = br[0]+br[2]
                if (br[1]+br[3]) > wrect[3]: wrect[3] = br[1]+br[3]
                rects.append(br)
        wrect[2] = wrect[2]-wrect[0]
        wrect[3] = wrect[3]-wrect[1]
        return tuple(wrect), rects
    
    # --------------------------------------------------
