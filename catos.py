# coding: UTF-8

'''
CATOS
(Computer Aided Training/Observing System for animal behavior experiments) 

jinook.oh@univie.ac.at
tecumseh.fitch@univie.ac.at
Cognitive Biology Dept., University of Vienna
- 2015.07

----------------------------------------------------------------------
Copyright (C) 2015 Jinook Oh, W. Tecumseh Fitch 
- Contact: jinook.oh@univie.ac.at, tecumseh.fitch@univie.ac.at

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import plistlib
from threading import Thread
from os import getcwd, path, mkdir
from copy import copy
from time import time, sleep
from datetime import datetime, timedelta
from glob import glob
from random import shuffle
from sys import argv
from queue import Queue

import wx, serial
from modules.misc_funcs import GNU_notice, get_time_stamp, writeFile
from modules.misc_funcs import get_log_file_path, show_msg, chk_msg_q

### load exisitng module files in module folder
###   (only files for running intended experiment is meant to be
###    located in module folder)
MODS = ["arduino", "session_mngr", "feeder_mngr",
        "videoIn", "videoOut", "audioIn", "audioOut", ]
flagMods = {}
for mod in MODS:
    if path.isfile("modules/%s.py"%(mod)):
        if mod == "arduino":
            from modules.arduino import Arduino
        elif mod == "session_mngr":
            from modules.session_mngr import ESessionManager
        elif mod == "feeder_mngr":
            from modules.feeder_mngr import FeederManager
        elif mod == "videoIn":
            from modules.videoIn import VideoIn
        elif mod == "videoOut":
            from modules.videoOut import VideoOut
        elif mod == "audioIn":
            from modules.audioIn import AudioIn
        elif mod == "audioOut":
            from modules.audioOut import AudioOut
        flagMods[mod] = True
    else:
        flagMods[mod] = False 

__version__ = "1.1.0"
DEBUG = False 

# ======================================================

class CATOSFrame(wx.Frame):
    """ Frame of CATOS to control experiment

    Attributes:
        Each attribute is commented in 'setting up attributes' section.
    """
    def __init__(self):
        if DEBUG: print('CATOSFrame.__init__()')

        ##### [begin] setting up attributes -----
        ### output folder check
        output_folder = path.join(CWD, 'output')
        if path.isdir(output_folder) == False: mkdir(output_folder)
        self.output_folder = output_folder # output folder
        # determine log file path
        self.log_file_path = get_log_file_path(output_folder)
        # audio file to load
        self.audio_files = ['input/snd_fly.wav', 'input/pos_fb.wav']
        self.w_size = (400, 300) # window size
        self.font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL)
        # init dict to contain necessary modules
        self.mods = dict(arduino=None, 
                         videoIn=[], 
                         feeder_videoIn=[], # when feeder uses a cam
                         videoOut=None, 
                         audioOut=None, 
                         session_mngr=None)
        self.program_start_time = time()
        self.session_start_time = -1
        self.last_play_time = -1 # last stimulus play time
        self.cam_idx = [0] #[0,1,2] # webcam indices # [[TEMP]] using one 
          # webcam for testing 
        self.cam_idx_feeder = [] # webcam index for the feeder
        self.cam_view_pos = [50+self.w_size[0], 
                             wx.GetDisplaySize()[1]-350] # position of
          # webcam view checking windows
        self.msg_q = Queue()
        ##### [end] setting up attributes ----- 
        
        # init frame
        wx.Frame.__init__(self, None, -1, 'CATOS', size=self.w_size) 
        self.SetPosition((50, wx.GetDisplaySize()[1]-self.w_size[1]))
        self.Show(True)
        self.panel = wx.Panel(self, pos=(0,0), size=self.w_size)
        self.panel.SetBackgroundColour('#000000')

        ##### [begin] user interface setup -----
        posX = 5
        posY = 10
        btn_width = 150
        b_space = 30
        self.btn_cam = wx.Button(self.panel, 
                                 -1, 
                                 label='Check webcam views', 
                                 pos=(posX,posY), 
                                 size=(btn_width, -1))
        self.btn_cam.Bind(wx.EVT_LEFT_UP, self.onChkWebcamView)
        posY += b_space
        self.btn_session = wx.Button(self.panel, 
                                     -1, 
                                     label='Start session', 
                                     pos=(posX,posY), 
                                     size=(btn_width, -1))
        self.btn_session.Bind(wx.EVT_LEFT_UP, self.onStartStopSession)
        posY += b_space
        self.btn_trial = wx.Button(self.panel, 
                                   -1, 
                                   label='Start trial', 
                                   pos=(posX,posY), 
                                   size=(btn_width, -1))
        self.btn_trial.Bind(wx.EVT_LEFT_UP, self.onStartTrial)
        posY += b_space + 10
        _stxt = wx.StaticText(self.panel, 
                              -1, 
                              label="Leave a note in LOG file", 
                              pos=(posX+5,posY))
        _stxt.SetForegroundColour('#CCCCCC')
        posY += 20
        self.txt_notes = wx.TextCtrl(self.panel, 
                                     -1, 
                                     name='txt_notes', 
                                     pos=(posX+5,posY), 
                                     size=(btn_width,-1), 
                                     style=wx.TE_PROCESS_ENTER)
        self.txt_notes.Bind(wx.EVT_TEXT_ENTER, self.onEnterInTextCtrl)
        posY += b_space + 10
        _stxt = wx.StaticText(self.panel, 
                              -1, 
                              label="Send a direct command to Arduino",
                              pos=(posX+5,posY))
        _stxt.SetForegroundColour('#CCCCCC')
        posY += 20
        self.txt_arduino = wx.TextCtrl(self.panel, 
                                       -1, 
                                       name='txt_arduino', 
                                       pos=(posX+5,posY), 
                                       size=(btn_width,-1), 
                                       style=wx.TE_PROCESS_ENTER)
        self.txt_arduino.Bind(wx.EVT_TEXT_ENTER, self.onEnterInTextCtrl)
        posY += b_space + 10
        self.btn_quit = wx.Button(self.panel, 
                                  -1, 
                                  label='QUIT', 
                                  pos=(posX,posY), 
                                  size=(btn_width, -1))
        self.btn_quit.Bind(wx.EVT_LEFT_UP, self.onClose)
        
        posX = 170
        posY = 15
        # time since program-start
        self.sTxt_pr_time = wx.StaticText(self.panel, 
                                          -1, 
                                          label='0:00:00', 
                                          pos=(posX, posY)) 
        _x = self.sTxt_pr_time.GetPosition()[0] + \
               self.sTxt_pr_time.GetSize()[0] + 15
        _stxt = wx.StaticText(self.panel, 
                              -1, 
                              label='since program started', 
                              pos=(_x, posY))
        _stxt.SetForegroundColour('#CCCCCC')
        self.sTxt_pr_time.SetFont(self.font)
        self.sTxt_pr_time.SetBackgroundColour('#000000')
        self.sTxt_pr_time.SetForegroundColour('#00FF00')
        posY += b_space
        # time since session-start
        self.sTxt_s_time = wx.StaticText(self.panel, 
                                         -1, 
                                         label='0:00:00', 
                                         pos=(posX, posY)) 
        _x = self.sTxt_s_time.GetPosition()[0] + \
               self.sTxt_s_time.GetSize()[0] + 15
        _stxt = wx.StaticText(self.panel, 
                              -1, 
                              label='since session started', 
                              pos=(_x, posY))
        _stxt.SetForegroundColour('#CCCCCC')
        self.sTxt_s_time.SetFont(self.font)
        self.sTxt_s_time.SetBackgroundColour('#000000')
        self.sTxt_s_time.SetForegroundColour('#CCCCFF')
        posY += b_space
        self.sTxt_time = wx.StaticText(self.panel, 
                                       -1, 
                                       label='0:00:00', 
                                       pos=(posX, posY))
        _x = self.sTxt_time.GetPosition()[0] + \
               self.sTxt_time.GetSize()[0] + 15
        _stxt = wx.StaticText(self.panel, 
                              -1, 
                              label='since last stimulus', 
                              pos=(_x, posY))
        _stxt.SetForegroundColour('#CCCCCC')
        self.sTxt_time.SetFont(self.font)
        self.sTxt_time.SetBackgroundColour('#000000')
        self.sTxt_time.SetForegroundColour('#FFFF00')
        
        statbar = wx.StatusBar(self, -1)
        self.SetStatusBar(statbar)
        ##### [end] user interface setup -----

        ### keyboard binding
        quit_btnId = wx.NewIdRef(count=1)
        session_btnId = wx.NewIdRef(count=1)
        note_btnId = wx.NewIdRef(count=1)
        self.Bind(wx.EVT_MENU, self.onClose, id=quit_btnId)
        self.Bind(wx.EVT_MENU, self.onStartStopSession, id=session_btnId)
        self.Bind(wx.EVT_MENU, self.onEnterNote, id=note_btnId)
        accel_tbl = wx.AcceleratorTable([ 
                                (wx.ACCEL_CTRL, ord('S'), session_btnId), 
                                (wx.ACCEL_CTRL, ord('N'), note_btnId),
                                (wx.ACCEL_CTRL, ord('Q'), quit_btnId)
                                ])
        self.SetAcceleratorTable(accel_tbl)

        ### set timer for processing message and 
        ###   updating the current running time
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onTimer, self.timer)
        self.timer.Start(100)

        if flagMods["arduino"]: self.start_arduino()
        self.txt_notes.SetFocus()

        self.Bind( wx.EVT_CLOSE, self.onClose )
        
        writeFile(self.log_file_path, 
                  "%s, [CATOS], Begining of the program\n"%(get_time_stamp()))

    # --------------------------------------------------        

    def start_arduino(self):
        if DEBUG: print('CATOSFrame.start_arduino()')
        
        self.mods["arduino"] = Arduino(self, self.output_folder)
        if self.mods["arduino"].aConn == None:
            return # !!! remove for actual setup. This is for testing purpose.
            msg = "Arduino chip is not found.\nPlease connect it and retry."
            show_msg(msg, self.panel)
            self.onClose(None)
        writeFile(self.log_file_path, 
                  "%s, [CATOS], arduino mod init.\n"%(get_time_stamp()))
    
    # --------------------------------------------------        
   
    def stop_arduino(self):
        if DEBUG: print('CATOSFrame.stop_arduino()')
        
        self.mods["arduino"] = None
        writeFile(self.log_file_path, 
                  "%s, [CATOS], arduino mod finished.\n"%(get_time_stamp()))
   
    # --------------------------------------------------        

    def start_mods(self, mod='all', option_str=''):
        if DEBUG: print('CATOSFrame.start_mods()')
        
        if mod == 'videoIn' or mod == 'feeder_videoIn':
            if option_str == 'chk_cam_view':
                chk_cam_view = True
                mod_name = 'videoIn'
                cam_idx = self.cam_idx + self.cam_idx_feeder
                flag_feeder = False
            else:
                chk_cam_view = False
                if mod == 'videoIn':
                    mod_name = 'videoIn'
                    cam_idx = self.cam_idx
                    flag_feeder = False
                elif mod == 'feeder_videoIn': 
                    mod_name = 'feeder_videoIn'
                    cam_idx = self.cam_idx_feederf
                    flag_feeder = True
            pos = list(self.cam_view_pos)
            for i in range(len(cam_idx)):
                self.mods[mod_name].append(VideoIn(self, 
                                                   cam_idx[i], 
                                                   tuple(pos)))
                self.mods[mod_name][-1].thrd = Thread(
                                target=self.mods[mod_name][-1].run,
                                args=(chk_cam_view, flag_feeder,)
                                )
                self.mods[mod_name][-1].thrd.start()
                pos[0] += 400
                
        if mod == 'videoOut' or (mod == 'all' and flagMods["videoOut"]):
            self.mods["videoOut"] = VideoOut(self)
            self.mods["videoOut"].Show(True)

        if mod == 'audioIn' or (mod == 'all' and flagMods["audioIn"]):
            self.mods["audioIn"] = AudioIn(self)
            self.mods["audioIn"].thrd = Thread(
                                target=self.mods["audioIn"].run
                                )
            self.mods["audioIn"].thrd.start()

        if mod == 'audioOut' or (mod == 'all' and flagMods["audioOut"]):
            self.mods["audioOut"] = AudioOut(self, self.audio_files)
        
        if mod == 'session_mngr' or (mod == 'all' and flagMods["session_mngr"]):
            self.mods["session_mngr"] = ESessionManager(self)
            writeFile(self.log_file_path, 
              '%s, [CATOS], session manager mod init.\n'%(get_time_stamp()))
        
        if mod == 'feeder_mngr' or (mod == 'all' and flagMods["feeder_mngr"]):
            self.mods["feeder_mngr"] = FeederManager(self)
            writeFile(self.log_file_path, 
              '%s, [CATOS], feeder manager mod init.\n'%(get_time_stamp()))

    # --------------------------------------------------        
        
    def stop_mods(self, mod='all', option_str=''):
        if DEBUG: print('CATOSFrame.stop_mods()')
        
        if mod == 'videoIn' or (mod =='all' and flagMods["videoIn"]):
            for i in range(len(self.mods['videoIn'])):
                self.mods['videoIn'][i].msg_q.put('main/quit/True', True, None)
                #wx.CallLater(1000, self.mods['videoIn'][i].thrd.join)
            self.mods['videoIn'] = []
            
        if mod == 'feeder_videoIn' or \
          (mod == 'all' and flagMods["feeder_mngr"]):
            for i in range(len(self.mods['feeder_videoIn'])):
                self.mods['feeder_videoIn'][i].msg_q.put(
                                                'main/quit/True', True, None
                                                )
                #wx.CallLater(1000, self.mods['feeder_videoIn'][i].thrd.join)
            self.mods['feeder_videoIn'] = []
            
        if mod == 'videoOut' or (mod == 'all' and flagMods["videoOut"]):
            if self.mods["videoOut"] != None:
                self.mods["videoOut"].onClose(None)
                self.mods["videoOut"] = None
        
        if mod == 'audioIn' or (mod == 'all' and flagMods["audioIn"]):
            if self.mods["audioIn"] != None:
                self.mods["audioIn"].msg_q.put('main/quit/True', True, None)
                self.mods["audioIn"] = None
    
        if mod == 'audioOut' or (mod == 'all' and flagMods["audioOut"]):
            if self.mods["audioOut"] != None:
                self.mods["audioOut"].stop()
                self.mods["audioOut"] = None

        if mod == 'session_mngr' or (mod == 'all' and flagMods["session_mngr"]):
            if self.mods["session_mngr"] != None:
                self.mods["session_mngr"].quit()
                self.mods["session_mngr"] = None
                log = "%s, [CATOS],"%(get_time_stamp())
                log += " session manager mod finished.\n"
                writeFile(self.log_file_path, log) 
            
        if mod == 'feeder_mngr' or (mod == 'all' and flagMods["feeder_mngr"]):
            if self.mods["feeder_mngr"] != None:
                self.mods["feeder_mngr"].quit()
                self.mods["feeder_mngr"] = None
                log = "%s, [CATOS],"%(get_time_stamp())
                log += " feeder manager mod finished.\n"
                writeFile(self.log_file_path, log)

    # --------------------------------------------------

    def onChkWebcamView(self, event):
        ''' Turn On/Off webcam to check its views
        '''
        if DEBUG: print('CATOSFrame.onChkWebcamView()')
        
        if flagMods["videoIn"] == False: return
        if self.btn_cam.IsEnabled() == False: return
        if self.mods["videoIn"] == []:
            self.start_mods(mod='videoIn', option_str='chk_cam_view')
        else: self.stop_mods(mod='videoIn')

    # --------------------------------------------------

    def onStartStopSession(self, event):
        '''Start/Stop a training or experimental session
        '''
        if DEBUG: print('CATOSFrame.onStartStopSession()')
        
        if self.session_start_time == -1: # not in session. start a session
            if flagMods["videoIn"] and self.mods["videoIn"] != []:
                self.stop_mods(mod="videoIn")
            if flagMods["videoIn"]:
                self.start_mods(mod='videoIn') # start webcam 
                  # (watching over 3 screens surrounded area)
            self.start_mods( mod='all' )
            self.session_start_time = time()
            e_time = time() - self.session_start_time
            log = "%s, [CATOS],"%(get_time_stamp())
            log += " %.3f, Beginning of session.\n"%(e_time)
            writeFile(self.log_file_path, log)
            self.btn_cam.Disable()
            self.btn_session.SetLabel('End session')
        else: # in session. stop it.
            if flagMods["videoIn"]:
                self.stop_mods(mod='videoIn') # stop webcam
            self.stop_mods( mod='all' )
            e_time = time() - self.session_start_time
            log = "%s, [CATOS],"%(get_time_stamp())
            log += " %.3f, End of session.\n"%(e_time)
            writeFile(self.log_file_path, log)
            self.session_start_time = -1
            self.last_play_time = -1 # time when the last stimulus was play
            self.sTxt_time.SetLabel('0:00:00')
            self.sTxt_s_time.SetLabel('0:00:00')
            self.btn_cam.Enable()
            self.btn_session.SetLabel('Start session')

    # --------------------------------------------------
    
    def onStartTrial(self, event):
        '''Start trial
        '''
        if DEBUG: print('CATOSFrame.onStartTrial()')
        
        if self.session_start_time == -1: return # not in session. quit
        self.mods["session_mngr"].init_trial()
    
    # --------------------------------------------------

    def onTimer(self, event):
        ''' Main timer 
        for processing messages from modules
        and updating running time on the main window
        '''
        if DEBUG: print('CATOSFrame.onTimer()')
        
        ### processing message
        msg_src, msg_body, msg_details = chk_msg_q(self.msg_q)

        ### update log file path, if necessary
        lfd = path.basename(self.log_file_path)[-6:-4] # date of the current
          # log file name
        _d = '%.2i'%(datetime.now().day) # current date
        if lfd != _d:
            # reset the log file path
            self.log_file_path = get_log_file_path(self.output_folder) 

        ### update several running time
        e_time = time() - self.program_start_time
        self.sTxt_pr_time.SetLabel(
                str(timedelta(seconds=e_time)).split('.')[0]
                )
        if self.session_start_time != -1:
            e_time = time() - self.session_start_time
            self.sTxt_s_time.SetLabel(
                    str(timedelta(seconds=e_time)).split('.')[0]
                    )
        if self.last_play_time != -1:
            e_time = time() - self.last_play_time
            self.sTxt_time.SetLabel(
                    str(timedelta(seconds=e_time)).split('.')[0]
                    )

    # --------------------------------------------------

    def onEnterInTextCtrl(self, event):
        if DEBUG: print('CATOSFrame.onEnterInTextCtrl()')
        
        if event.GetEventObject().GetName().strip() == 'txt_notes':
            value = self.txt_notes.GetValue()
            log = "%s, [CATOS], %s\n"%(get_time_stamp(), value)
            writeFile(self.log_file_path, log)
            self.show_msg_in_statbar("'%s' is written in the log."%value)
            self.txt_notes.SetValue('')
        else: # entered in txt_arduino
            cmd = self.txt_arduino.GetValue()
            self.mods["arduino"].send(cmd.encode()) # send a message to Arduino
            self.txt_arduino.SetValue("")

    # --------------------------------------------------
    
    def onEnterNote(self, event):
        if DEBUG: print('CATOSFrame.onEnterInTextCtrl()')
        
        self.txt_notes.SetFocus()
    
    # --------------------------------------------------

    def show_msg_in_statbar(self, msg, time=5000):
        if DEBUG: print('CATOSFrame.show_msg_in_statbar()')
        
        self.SetStatusText(msg)
        wx.CallLater(time, self.SetStatusText, "") # delete it after a while

    # --------------------------------------------------

    def onClose(self, event):
        if DEBUG: print('CATOSFrame.onClose()')
        
        self.timer.Stop()
        #for k in self.timers.keys(): self.timers[k].Stop()
        if self.session_start_time != -1:
            self.onStartStopSession(None) # stop session if it's running
        if self.mods["videoIn"] != []:
            self.stop_mods(mod='videoIn')
        if flagMods["arduino"]: self.stop_arduino()
        writeFile(self.log_file_path, 
                  '%s, [CATOS], End of the program\n'%(get_time_stamp()))
        wx.CallLater(1000, self.Destroy)

# ======================================================

class CATOSApp(wx.App):
    def OnInit(self):
        if DEBUG: print('CATOSApp.OnInit()')
        
        self.frame = CATOSFrame()
        self.frame.Show()
        self.SetTopWindow(self.frame)
        return True

# ======================================================

if __name__ == '__main__':
    if len(argv) > 1:
        if argv[1] == '-w': GNU_notice(1)
        elif argv[1] == '-c': GNU_notice(2)
    else:
        GNU_notice(0)
        CWD = getcwd()
        app = CATOSApp(redirect = False)
        app.MainLoop()




