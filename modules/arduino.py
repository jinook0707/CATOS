# coding: UTF-8

"""
This module is for sending and receiving messages
 to Arduino-chip to control sensors and actuators.
"""

import serial
from os import path
from glob import glob
from time import time, sleep
from sys import platform

from modules.misc_funcs import writeFile, get_time_stamp, update_log_file_path, show_msg

# ======================================================

class Arduino:
    def __init__(self, parent, output_folder):
        self.parent = parent
        self.output_folder = output_folder
        self.log_file_path = ''
        if platform == 'darwin': ARDUINO_USB_GLOB = "/dev/cu.usbmodem*"
        elif 'linux' in platform: ARDUINO_USB_GLOB = "/dev/ttyACM*"
        ARDUINO_PORT = ''
        self.aConn = None
        for aConn in self.serial_scan(ARDUINO_USB_GLOB):
            ARDUINO_PORT = aConn.name # Note: it uses the last one (when there're multiple ARDUINO chips connected)
        if str(ARDUINO_PORT) != '':
            msg = str(ARDUINO_PORT) + " connected."
            print(msg)
            self.aConn = aConn

    # --------------------------------------------
    
    def try_open(self, port):
        try:
            port = serial.Serial(port, 9600, timeout = 0)
        except serial.SerialException as e:
            return None
        else:
            return port

    # --------------------------------------------

    def serial_scan(self, ARDUINO_USB_GLOB):
        for fn in glob(ARDUINO_USB_GLOB):
            port = self.try_open(fn)
            if port is not None:
                yield port
    
    # --------------------------------------------    

    def send(self, msg='', flag_log=True):
        self.aConn.write(msg) # send a message to Arduino
        #sleep(0.1)
        self.aConn.flush() # flush the serial connection
        if flag_log == True:
            if path.isfile(self.log_file_path) == False:
                self.log_file_path = update_log_file_path(self.output_folder)
            writeFile(self.log_file_path, "%s, [arduino], '%s' was sent to Arduino\n"%(get_time_stamp(), msg))

    # --------------------------------------------

    def receive(self, header, timeout):
        ''' receive an intended(header-matching) message from the Arduino-chip 
        for timeout-time(in seconds)
        '''
        startTime = time()
        while True:
            ### try to get the intended message only for timeout-time
            if timeout != None:
                currTime = time()
                if currTime - startTime > timeout:
                    msg = None
                    break
            msg = self.receive_a_msg(timeout)
            if msg == None: break
            else:
                msg = msg.strip("\r\n")
                msg = [ m.strip() for m in msg.split(",") ]
                if header in msg: # if there's a header in the list of messages
                    msg = msg[msg.index(header):] # store the head to end
                    break # quit loop (otherwise keep receiving message)
        if msg != None:
            self.aConn.flushInput()
            if msg[len(msg)-1] == 'EOM': msg.pop(len(msg)-1) # delete 'EOM'
        return msg

    # --------------------------------------------

    def receive_a_msg(self, timeout):
        ''' receive a message from the Arduino-chip for timeout-time
        '''
        startTime = time()
        msg = self.aConn.read()
        while msg[-3:] != "EOM": # End Of Message
            if timeout != None:
                currTime = time()
                if currTime - startTime > timeout:
                    msg = None
                    break
            msg += self.aConn.read()
        return msg

# ======================================================

