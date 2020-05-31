# coding: UTF-8

"""
This is for drawing visual stimuli in CATOS.

* This file was coded for running training and experimental
sessions with common marmoset monkeys by Jinook Oh
in CogBio dept. University of Vienna in 2016
"""

from time import time, sleep
from random import uniform, randint

import wx
import numpy as np
from modules.misc_funcs import writeFile, get_time_stamp, chk_fps, make_b_curve_coord

# ======================================================

class VideoOut(wx.Frame):
    def __init__(self, parent):
        self.parent = parent

        self.fo = []
        self.refresh_rate = 60 
        self.scr_sec = [11, 5] # number of sections in screen [horizontal, vertical]
        self.gr = (-1,-1,-1,-1) # group rect (x,y,w,h)
        self.gctr = (-1,-1) # center point of group
        self.flag_trial = True # in trial or NOT
        self.aPos = (-1,-1) # animal subject's current position. (-1,-1)=out of sight
        self.bgCol = '#777777'
        self.timer = None
        self.fo_min_rad = 15 # minimum radius of an object
        self.fo_max_rad = 25 # maximum radius
        self.fo_min_spd = 25 # minimum number of pixels to move per frame
        self.fo_max_spd = 30 # maximum number of pixels
        self.flag_rad_change = True # random radius change
        mode = 'test'
        
        posX = []
        self.s_w = [] # widths screen of the first 3 screens
        self.s_h = [] # screen heights of the first 3 screens
      
        screenCnt = wx.Display.GetCount() # * Note that this module is meant 
          # to work with three screens, surrounding subject
        for i in range(screenCnt):
            g = wx.Display(i).GetGeometry()
            posX.append(g[0])
            self.s_w.append(g[2])
            self.s_h.append(g[3])
        #self.wPos = (min(posX), 0)
        self.wPos = (-1, 0)
        if mode == 'debug':
            self.wSize = (sum(self.s_w), max(self.s_h)/3*2)
            dp_size = (sum(self.s_w), max(self.s_h)/3*2) 
        else:
            self.wSize = (sum(self.s_w), max(self.s_h)-40)
            dp_size = (sum(self.s_w), max(self.s_h)-40)
        self.ctr_rect = [self.wSize[0]/2-50, self.wSize[1]/2-50, self.wSize[0]/2+50, self.wSize[1]/2+50] # center rect; x1,y1,x2,y2
        wx.Frame.__init__(self, None, -1, '', pos=self.wPos, size=dp_size, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.SetPosition(self.wPos)
        self.SetSize(dp_size)
        self.SetBackgroundColour(self.bgCol)
        self.panel = wx.Panel(self, pos=(0,0), size=self.wSize)
        self.panel.SetBackgroundColour(self.bgCol)
        cursor = wx.Cursor(wx.CURSOR_BLANK)
        self.panel.SetCursor(cursor) # hide cursor
        self.panel.Bind(wx.EVT_PAINT, self.onPaint)
        self.panel.Bind(wx.EVT_LEFT_DOWN, self.onMouseDown)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        ### keyboard binding
        quit_btnId = wx.NewId()
        playStim_btnId = wx.NewId()
        self.Bind(wx.EVT_MENU, self.parent.onStartStopSession, id=quit_btnId)
        accel_tbl = wx.AcceleratorTable([ (wx.ACCEL_CTRL, ord('Q'), quit_btnId) ])
        self.SetAcceleratorTable(accel_tbl)
        
        writeFile(self.parent.log_file_path, '%s, [videoOut], videoOut mod init.\n'%(get_time_stamp()))
        
    # --------------------------------------------------
    
    def init_static_img(self):
        self.panel.Refresh()
        self.time = None
        self.flag_trial = True
    
    # --------------------------------------------------

    def init_floating_obj(self, num_of_fo=5):
        fo = [] 
        self.chance_to_change_rad = 0.3
        if self.parent.mods["session_mngr"].session_type == 'immersion':
            if uniform(0,1) < 0.5:
                minX = self.fo_max_rad
                maxX = self.wSize[0]/self.scr_sec[0]-self.fo_max_rad
            else:
                minX = self.wSize[0]-self.wSize[0]/self.scr_sec[0]+self.fo_max_rad
                maxX = self.wSize[0]-self.fo_max_rad
        else: # stimulus will appear only on the center screen (touchscreen)
            minX = self.ctr_rect[0]
            maxX = self.ctr_rect[2]
        for i in range(num_of_fo):
            x = randint(minX, maxX)
            y = randint(self.fo_max_rad, min(self.s_h)-self.fo_max_rad)
            r = randint(self.fo_min_rad, self.fo_max_rad)
            fo.append( dict(track=[(x,y)], # list of coordinates to move along
                            rad=r, # radius 
                            rad_change=0, # change of radius on each drawing (-1,0 or 1)
                            col='#CCCCCC') # fill color
                     )
        self.fo = fo
        self.calc_group_rect()
        self.fo_pos_idx = [ int(float(self.gctr[0]) / self.wSize[0] * 5) - 2, int(float(self.gctr[1]) / self.wSize[1] * 5) - 2 ] # -2 ~ 2
        if self.timer == None:
            ### set timer for updating floating objects and other processes
            self.timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self.onTimer, self.timer)
        self.timer.Start( 1000/self.refresh_rate )
        self.flag_rad_change = True # random radius change
        self.flag_trial = True

        self.prev_fps_time = time()
        self.prev_fps = []
        self.fps = 0
    
    # --------------------------------------------------

    def calc_group_rect(self):
        margin = 50
        posX = []; posY = []
        for i in range(len(self.fo)):
            posX.append( self.fo[i]['track'][0][0] )
            posY.append( self.fo[i]['track'][0][1] )
        minX = min(posX) - margin
        minY = min(posY) - margin
        w = max(posX) - minX + margin # width of group
        h = max(posY) - minY + margin # height of group
        self.gr = (minX, minY, w, h)
        self.gctr = ( minX+w/2, minY+h/2 )
    
    # --------------------------------------------------    

    def onTimer(self, event):
        ''' refresh panel to redraw FO and updates its data
        '''
        self.fps, self.prev_fps, self.prev_fps_time = chk_fps(
                                                    'videoOut', 
                                                    self.fps, 
                                                    self.prev_fps, 
                                                    self.prev_fps_time, 
                                                    self.parent.log_file_path
                                                    )
        self.calc_group_rect() # calculate center point of the group
        self.panel.Refresh()
        fo_pos_idx_ = [
                int(float(self.gctr[0])/self.wSize[0]*self.scr_sec[0])+1, 
                int(float(self.gctr[1])/self.wSize[1]*self.scr_sec[1])
                ]
        idxAO = [fo_pos_idx_[0] - (self.scr_sec[0]/2), 
                 fo_pos_idx_[1] - (self.scr_sec[1]/2)]
        idxAO[0] *= -1 # change symbol (left <-> right)
        #if idxAO[0] != 0: idxAO[0] = idxAO[0]/2
        #if idxAO[1] != 0: idxAO[1] = idxAO[1]/2
        idxAO.append(0) #idxAO.append( -abs(idxAO[0]) ) # z index depends on 
          # x index in our three screen configuration
        if self.fo_pos_idx != fo_pos_idx_:
        # if FO group's position area is changed
            self.fo_pos_idx = [fo_pos_idx_[0], fo_pos_idx_[1]] # update the info
            self.parent.mods["session_mngr"].msg_q.put(
                    'videoOut/foMove/%i/%i/%i'%(idxAO[0],idxAO[1],idxAO[2]), 
                    True, 
                    None
                    )
        
        tBuff = 50 # buffer (pixels) for determining track
        if len(self.fo[0]['track']) == 1:
        ### ran out of track data. 
        ###   determine a new destination with relevant variables
            if self.parent.mods["session_mngr"].session_type == 'immersion':
                if uniform(0,1) < 0.33:
                    range_ = (tBuff, self.wSize[0]-tBuff)
                else:
                    if self.gctr[0] < self.wSize[0]/2:
                        # remain in left screen
                        range_ = (tBuff, self.s_w[0]-tBuff) 
                    elif self.gctr[0] > self.wSize[0]/2:
                        range_ = (self.s_w[0]+self.s_w[1]+tBuff,
                                  self.wSize[0]-tBuff) # remain in right screen
                    else: range_ = (tBuff, self.wSize[0]-tBuff)
            else: # stimulus moves in the center only
                range_ = (self.ctr_rect[0], self.ctr_rect[2])

            dest = (randint(range_[0], range_[1]), 
                    randint(tBuff, min(self.s_h)-tBuff))
            if self.gctr[0] < dest[0]:
                h1 = (randint(self.gctr[0], 
                              int(self.gctr[0]+(dest[0]-self.gctr[0])*0.666)), 
                      randint(tBuff, min(self.s_h)-tBuff))
                h2 = (randint(int(self.gctr[0]+(dest[0]-self.gctr[0])*0.333), 
                              dest[0]), 
                      randint(tBuff, 
                              min(self.s_h)-tBuff))
            else:
                h1 = (randint(int(dest[0]+(self.gctr[0]-dest[0])*0.333), 
                              self.gctr[0]), 
                      randint(tBuff, 
                              min(self.s_h)-tBuff))
                h2 = (randint(dest[0], 
                              int(dest[0]+(self.gctr[0]-dest[0])*0.666)), 
                      randint(tBuff, 
                              min(self.s_h)-tBuff))
            ### travel distance
            t_dist = np.sqrt((self.gctr[0]-h1[0])**2 + (self.gctr[1]-h1[1])**2)
            t_dist += np.sqrt((h1[0]-h2[0])**2 + (h1[1]-h2[1])**2)
            t_dist += np.sqrt((h2[0]-dest[0])**2 + (h2[1]-dest[1])**2)
            number_of_track_pts = randint(int(t_dist/self.fo_max_spd),
                                          int(t_dist/self.fo_min_spd)) # this
                                            # determines speed of FO movements
            number_of_track_pts = max(self.refresh_rate, 
                                      number_of_track_pts) # set the minimum 
                                                           # track points

        for i in range(len(self.fo)):
            if len(self.fo[i]['track']) > 1:
                self.fo[i]['track'].pop(0) # pop out the used coordinate 
                  # from the track
            else: # ran out of track data. get a new bezier curve points
                ### make bezier curve track points with individual randomness 
                orig_ = (self.fo[i]['track'][0][0], self.fo[i]['track'][0][1])
                dest_ = (randint(dest[0]-tBuff, dest[0]+tBuff), 
                         randint(dest[1]-tBuff, dest[1]+tBuff))
                h1_ = (randint(h1[0]-tBuff*4, h1[0]+tBuff*4),
                       randint(h1[1]-tBuff*4, h1[1]+tBuff*4))
                h2_ = (randint(h2[0]-tBuff*4, h2[0]+tBuff*4),
                       randint(h2[1]-tBuff*4, h2[1]+tBuff*4))
                self.fo[i]['track'] = make_b_curve_coord(
                                    orig_, h1_, h2_, dest_, number_of_track_pts
                                    )

            if self.flag_rad_change == True:
                ### random radius change of each fo
                if self.fo[i]['rad_change'] == 0:
                    if uniform(0,1) < self.chance_to_change_rad:
                        if uniform(0,1) > 0.5: self.fo[i]['rad_change'] = 1
                        else: self.fo[i]['rad_change'] = -1
                else:
                    self.fo[i]['rad'] += self.fo[i]['rad_change']
                    if self.fo[i]['rad'] < self.fo_min_rad:
                        self.fo[i]['rad'] = int(self.fo_min_rad)
                        self.fo[i]['rad_change'] = 0
                    elif self.fo[i]['rad'] > self.fo_max_rad:
                        self.fo[i]['rad'] = int(self.fo_max_rad)
                        self.fo[i]['rad_change'] = 0

    # --------------------------------------------------            

    def onPaint(self, event):
        dc = wx.PaintDC(event.GetEventObject())
        #dc = wx.BufferedPaintDC(self.panel, self.buffer_)
        dc.Clear()
        if self.flag_trial == False: return
        if not hasattr(self.parent.mods["session_mngr"], "session_type"): return

        s_type = self.parent.mods["session_mngr"].session_type
        if s_type == 'static':
            dc.SetPen(wx.Pen(wx.BLACK, 1))
            dc.SetBrush(wx.Brush('#333333'))
            rad = int(self.s_h/3)
            x = int(self.wSize[0]/2-rad)
            y = int(self.wSize[1]/2-rad)
            w = rad*2
            h = rad*2
            dc.DrawRectangle(x,y,w,h)
            self.gr = (x,y,w,h)
        elif s_type == 'movements' or s_type == 'immersion':
            for i in range(len(self.fo)):
                fo = self.fo[i]
                r=randint(0,255); g=randint(0,255); b=randint(0,255)
                dc.SetPen(wx.Pen(wx.Colour(r,g,b), 2))
                dc.SetBrush(wx.Brush(fo['col']))
                dc.DrawCircle(fo['track'][0][0], fo['track'][0][1], fo['rad'])
        
    # --------------------------------------------------
    
    def onMouseDown(self, event):
        mp = event.GetPosition()
        if (self.gr[0] <= mp[0] <= self.gr[0]+self.gr[2]) and \
           (self.gr[1] <= mp[1] <= self.gr[1]+self.gr[3]):
        # group is touched
            ### set a new destination for scattering motion 
            steps = self.refresh_rate/4
            call_session_mngr_time = 1000/4-10
            # make small pieces to scatter
            number_of_fo_ = int(len(self.fo))
            for i in range(len(self.fo)):
                for j in range(10):
                    x=self.fo[i]['track'][0][0]; y=self.fo[i]['track'][0][1]
                    self.fo.append( dict(track=[(randint(x-10,x+10),randint(y-10,y+10))], # list of coordinates to move along
                                    rad=randint(1, self.fo_min_rad/2), # radius 
                                    rad_change=0, # change of radius on each drawing (-1,0 or 1)
                                    col='#CCCCCC') ) # fill color
            for i in range(number_of_fo_): self.fo.pop(0)
            self.calc_group_rect()
            self.flag_rad_change = False
            # set track points
            for i in range(len(self.fo)):
                orig_ = ( self.fo[i]['track'][0][0], self.fo[i]['track'][0][1] )
                dest_ = [-1, -1]
                if orig_[0] < self.gctr[0]: dest_[0] = randint(orig_[0]-500, orig_[0]-1)
                elif orig_[0] > self.gctr[0]: dest_[0] = randint(orig_[0]+1, orig_[0]+500)
                else: dest_[0] = orig_[0]
                if orig_[1] < self.gctr[1]: dest_[1] = randint(orig_[1]-500, orig_[1]-1)
                elif orig_[1] > self.gctr[1]: dest_[1] = randint(orig_[1]+1, orig_[1]+500)
                else: dest_[1] = orig_[1]
                tl = []; xstep = abs(dest_[0]-orig_[0])/steps; ystep = abs(dest_[1]-orig_[1])/steps
                for j in range(steps):
                    if orig_[0] < dest_[0]: x = orig_[0]+xstep*j
                    else: x = orig_[0]-xstep*j
                    if orig_[1] < dest_[1]: y = orig_[1]+ystep*j
                    else: y = orig_[1]-ystep*j
                    tl.append((x,y))
                self.fo[i]['track'] = tl
            writeFile(self.parent.log_file_path, '%s, [videoOut], The target is touched.\n'%(get_time_stamp())) 
            wx.CallLater(call_session_mngr_time, 
                         self.parent.mods["session_mngr"].msg_q.put, 
                         'videoOut/stim_touched', 
                         True, 
                         None)

    # --------------------------------------------------
        
    def onClose(self, event):
        if self.timer != None: self.timer.Stop()
        writeFile(self.parent.log_file_path, '%s, [videoOut], videoOut mod finished.\n'%(get_time_stamp()))
        self.Destroy()

# ======================================================

if __name__ == '__main__': pass

