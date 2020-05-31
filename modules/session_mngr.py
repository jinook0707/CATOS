# coding: UTF-8

"""
This is for managing an experimental session procedure in CATOS.

* This file was coded for running training and experimental
sessions with common marmoset monkeys by Jinook Oh
in CogBio dept. University of Vienna in 2016
"""

from time import sleep, time
from random import randint
import queue

import wx
from modules.misc_funcs import writeFile, get_time_stamp, update_log_file_path, show_msg, chk_msg_q, make_b_curve_coord

# ======================================================

class ESessionManager:
    def __init__(self, parent):
        self.parent = parent
        
        self.ITI = 19900 # Inter Trial Interval; End-Trial > Feeder getting ready (time varies) > ITI > Begin-Trial
        self.msg_q = queue.Queue()
        self.session_type = 'movements' # feed: simply activating feeder with random interval, static: static image, movements: moving dots only on the center screen without sound, immersion: surround_display+sound 
        self.state = 'pause'
        self.ctrFOResetTime = -1 # last time FO track was set in center screen while subject was detected around center screen.
        self.last_feed_time = -1
        wx.CallLater(500, self.init_timer)
        wx.CallLater(1000, self.init_trial)

    # --------------------------------------------
    
    def init_timer(self):
        ### set timer for processing message
        self.timer = wx.Timer(self.parent)
        self.parent.Bind(wx.EVT_TIMER, self.onTimer, self.timer)
        self.timer.Start(10)

    # --------------------------------------------

    def init_trial(self):
        if self.state == 'inTrial': return
        if self.session_type == 'feed':
            self.feed_intv = randint(10000, 30000)/1000.0 # random feeding interval in seconds
        elif self.session_type == 'static':
            self.parent.mods['videoOut'].init_static_img()
        elif self.session_type == 'movements' or \
          self.session_type == 'immersion':
            self.parent.mods["videoOut"].init_floating_obj(1)
        if self.session_type == 'immersion':
            self.parent.mods["audioOut"].play(0)
        writeFile(self.parent.log_file_path, 
                  '%s, [session_mngr], Trial init.\n'%(get_time_stamp()))
        wx.CallLater(100, self.init_trial_state)

    # --------------------------------------------
            
    def init_trial_state(self):
        self.state = 'inTrial'

    # --------------------------------------------
    
    def onTimer(self, event):
        ''' Timer for checking message and processing with the current state
        '''
        ### retrieve messages
        flag_foMove = False
        flag_stim_touched = False
        close_to_rScreen = False
        close_to_cScreen = False
        close_to_lScreen = False
        while not self.msg_q.empty():
            # listen to a message
            msg_src, msg_body, msg_details = chk_msg_q(self.msg_q) 
            if msg_body == 'foMove':
                flag_foMove = True
                fo_pos = [int(msg_details[0]), 
                          int(msg_details[1]), 
                          int(msg_details[2])]
            elif msg_body == 'close_to_screen': 
            # movement happened around a screen
                if msg_details[0] == 'left': close_to_lScreen = True
                if msg_details[0] == 'center': close_to_cScreen = True
                if msg_details[0] == 'right': close_to_rScreen = True
            elif msg_body == 'stim_touched':
                flag_stim_touched = True
                
        ### processing with the current state and received messages
        if self.state == 'inTrial':
            if flag_foMove == True:
            # group FOs is located in a differect section of the screen, 
            # sound source should move accordingly
                if self.session_type == 'immersion':
                    # move sound source position
                    self.parent.mods["audioOut"].move(fo_pos) 
                
            if flag_stim_touched == True: # stimulus was touched
                if self.session_type == 'immersion':
                    self.parent.mods["audioOut"].stop()
                    # play positive feedback sound
                    self.parent.mods["audioOut"].play(1, False) 
                if self.parent.mods["videoOut"].timer != None:
                    self.parent.mods["videoOut"].timer.Stop()
                self.parent.mods["videoOut"].flag_trial = False
                self.parent.mods["videoOut"].panel.Refresh()
                #self.parent.stop_mods(mod='videoIn') # stop webcam
                writeFile(self.parent.log_file_path, 
                  '%s, [session_mngr], Trial finished.\n'%(get_time_stamp()))
                self.parent.mods["arduino"].send("feed".encode())
                writeFile(self.parent.log_file_path, 
                  '%s, [session_mngr], Feed message sent.\n'%(get_time_stamp()))
                self.state = 'pause' # pause for ITI
                wx.CallLater(self.ITI, self.init_trial)
          
            if self.session_type == 'feed':
                if time()-self.last_feed_time >= self.feed_intv:
                    self.parent.mods["arduino"].send("feed".encode())
                    log = "%s, [session_mngr],"%(get_time_stamp())
                    log += "Feed message sent.\n"
                    writeFile(self.parent.log_file_path, log)
                    self.state = 'pause' # pause for ITI
                    wx.CallLater(self.ITI, self.init_trial)
                    self.last_feed_time = time()

            if self.session_type == 'immersion':
                if close_to_lScreen or close_to_cScreen or close_to_rScreen:
                # subject is close to a screen
                    voMod = self.parent.mods["videoOut"]
                    screenCtr = voMod.wSize[0]/2
                    dest = ( randint(voMod.ctr_rect[0], voMod.ctr_rect[2]), 
                             randint(voMod.ctr_rect[1], voMod.ctr_rect[3]) )
                    #print close_to_lScreen, close_to_cScreen, close_to_rScreen
                    if (close_to_rScreen and \
                            voMod.gctr[0] > (voMod.s_w[0]+voMod.s_w[1])) or \
                       (close_to_lScreen and \
                            voMod.gctr[0] < voMod.s_w[0]): 
                        steps = randint(30, 40) # determine steps to travel 
                          # (shorter = faster movement) 
                        ### set a new destination which should be 
                        ###   in the center screen / line, not a curve
                        for i in xrange(len(voMod.fo)):
                            orig_ = (voMod.fo[i]['track'][0][0], 
                                     voMod.fo[i]['track'][0][1] )
                            dest_ = (randint(dest[0]-50,dest[0]+50),
                                     randint(dest[1]-50,dest[1]+50))
                            tl = []
                            xstep = int(abs(dest_[0]-orig_[0])/steps)
                            ystep = int(abs(dest_[1]-orig_[1])/steps)
                            for j in xrange(steps):
                                if orig_[0] < dest_[0]: x = orig_[0]+xstep*j
                                else: x = orig_[0]-xstep*j
                                if orig_[1] < dest_[1]: y = orig_[1]+ystep*j
                                else: y = orig_[1]-ystep*j
                                tl.append((x,y))
                            voMod.fo[i]['track'] = tl
                    elif close_to_cScreen and \
                      (voMod.s_w[0] <= voMod.gctr[0] <= voMod.s_w[0]+voMod.s_w[1]):
                    # subject is close to the center screen and 
                    # the stimulus is already on the screen. 
                        if self.ctrFOResetTime == -1 or \
                          (time()-self.ctrFOResetTime)>1:
                        # FO track was set before a half second ago.
                            steps = randint(70, 120) # steps to travel 
                              # (shorter = faster movement) 
                            h1 = (randint(voMod.ctr_rect[0]-50, 
                                          voMod.ctr_rect[2]+50), 
                                  randint(voMod.ctr_rect[1]-50, 
                                          voMod.ctr_rect[3]+50))
                            h2 = (randint(voMod.ctr_rect[0]-50,
                                          voMod.ctr_rect[2]+50), 
                                  randint(voMod.ctr_rect[1]-50, 
                                          voMod.ctr_rect[3]+50))
                            for i in xrange(len(voMod.fo)):
                                orig_ = (voMod.fo[i]['track'][0][0], 
                                         voMod.fo[i]['track'][0][1])
                                dest_ = (randint(dest[0]-50,dest[0]+50),
                                         randint(dest[1]-50,dest[1]+50))
                                h1_ = (randint(h1[0]-50, h1[0]+50),
                                       randint(h1[1]-50, h1[1]+50))
                                h2_ = (randint(h2[0]-50, h2[0]+50),
                                       randint(h2[1]-50, h2[1]+50))
                                voMod.fo[i]['track'] = make_b_curve_coord( 
                                                orig_, h1_, h2_, dest_, steps
                                                )
                                self.ctrFOResetTime = time()
    
    # --------------------------------------------
    
    def quit(self):
        self.timer.Stop()

    # --------------------------------------------
    
# ======================================================




