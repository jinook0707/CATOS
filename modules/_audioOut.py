import wave
from time import time, sleep

import openal.al as al
from openal.audio import SoundSink, SoundSource, SoundListener
from openal.loaders import load_wav_file

from modules.misc_funcs import writeFile, get_time_stamp, chk_fps, make_b_curve_coord

# ===========================================================

class AudioOut:
    def __init__(self, parent, wav_file_paths):
        self.parent = parent
        self.wav_file_paths = wav_file_paths
        self.snd_src = None
        self.sink = SoundSink()
        self.sink.activate()
        self.listener = SoundListener()
        self.sink.listener = self.listener
        self.snd_data = []
        for fp in wav_file_paths: self.snd_data.append( load_wav_file(fp) )
        self.wav_file_paths = wav_file_paths
        writeFile(self.parent.log_file_path, '%s, [audioOut], audioOut mod init.\n'%(get_time_stamp()))
        
    # --------------------------------------------------
    
    def play(self, snd_idx, loop=True):
        self.snd_src = SoundSource(gain=0.25, position=[0,0,0])
        self.snd_src.looping = loop
        self.snd_src.queue( self.snd_data[snd_idx] )
        self.sink.play(self.snd_src)
        self.sink.update()
        writeFile(self.parent.log_file_path, '%s, [audioOut], sound (%s) play starts.\n'%(get_time_stamp(), self.wav_file_paths[snd_idx]))
    
    # --------------------------------------------------
    
    def move(self, pos):
        self.snd_src.position = [ pos[0], pos[1], pos[2] ]
        if pos[0] == 0: self.snd_src.gain = 0.25
        else: self.snd_src.gain = 0.5
        self.sink.update()
       
    # --------------------------------------------------
    
    def stop(self):
        if self.snd_src != None:
            self.sink.stop(self.snd_src)
            self.sink.update()
            self.snd_src = None
        writeFile(self.parent.log_file_path, '%s, [audioOut], sound stopped.\n'%(get_time_stamp()))

    # --------------------------------------------------    

# ===========================================================


