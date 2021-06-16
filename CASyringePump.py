
import MKUsbLocator
import serial
import time

import logging
import queue

logging.basicConfig(
    filename = 'LogMotionGenerator.log',
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S'
)

logging.info('Process started')

'''
Mechanics of controlling and executing commands on the syringe pump.
''' 

def bound(lower, val, upper):
    if val == None:
        return None
    return min(max(val, lower), upper)

class Syringe:
    def __init__(self, name, volume, volume_per_distance, max_plunger_length, min_plunger_length):
        self.name = name # str
        self.volume = volume # int, mL
        self.volume_per_distance = volume_per_distance # mL/mm
        self.max_plunger_length = max_plunger_length # mm
        self.min_plunger_length = min_plunger_length # mm

syringes = [
    Syringe(name='5mL',
        volume=5, # mL
        volume_per_distance=1.0/8, # mL per mm
        max_plunger_length=66.7, # mm
        min_plunger_length=16.3, # mm
    ),
    Syringe(name='10mL',
        volume=12, # mL
        volume_per_distance=1.0/5, # mL per mm
        max_plunger_length=83.1, # mm
        min_plunger_length=18.2, # mm
    ),
    Syringe(name='20mL',
        volume=20, # mL
        volume_per_distance=15.0/47, # mL per mm
        max_plunger_length=100, # mm
        min_plunger_length=18.5, # mm
    ),
    Syringe(name='50mL',
        volume=60, # mL
        volume_per_distance=10.0/15, # mL per mm
        max_plunger_length=119, # mm
        min_plunger_length=22.5, # mm
    ),
]

def get_syringe(name):
    return [s for s in syringes if s.name == name][0]



class SyringeStage:

    '''
    syringe = Syringe class instance
    axis = axis syrinige is positioned in as string. Options include "X" and "Y"
    '''
    def __init__(self, syringe, axis='X'):
        
        if type(syringe) == str:
            syringe = get_syringe(syringe)

        self.syringe = syringe
        self.axis = axis

    # stage properties
    MAX_LENGTH = 114.1 # mm, max coordinate the plunger can be moved to
    position = 0

    def stage_coordinates(self, p):
        return self.MAX_LENGTH - p

    def syringe_depressed_position(self):
        return self.stage_coordinates(self.syringe.min_plunger_length)
    
    def syringe_extended_position(self):
        return self.stage_coordinates(self.MAX_LENGTH - self.syringe.max_plunger_length)
    
    # def syringe_percent_position(self, p):
    #     # 0% -> syringe min length position, 100% to syringe max length position
    #     percentage = min(max(p, 0), 1)
    #     active_dist = self.syringe_depressed_position() - self.syringe_extended_position()
    #     return self.syringe_extended_position() + active_dist * percentage

    # position where syringe has volume v left in syringe  
    def syringe_volume_position(self, v):
        if v == None:
            return None
        return self.stage_coordinates(self.syringe.min_plunger_length + v/self.syringe.volume_per_distance)


    # for motion, we need: new position + speed

    # returns (step-distance, speed)
    def step_distance(self, volume, period):
        
        step_distance = volume / self.syringe.volume_per_distance # mm
        speed = step_distance / period * 60 # mm/min
      
        return step_distance, speed

    def available_distance(self):
        return self.syringe_depressed_position() - self.position

    def available_steps(self, volume):
        if volume == 0:
            return 1000000 # infinately many steps available
        step_distance = volume / self.syringe.volume_per_distance # mm
        steps = self.available_distance() / step_distance
        return steps

import threading

'''
GCode for both stages must be generated at teh same time as GCode commands are blocking 
-> both x and y motions has to be encoded in a single go. 
'''
class SyringePump:

    def __init__(self, port, syringe_x, syringe_y):
        self.x_stage = SyringeStage(syringe_x, 'X')
        self.y_stage = SyringeStage(syringe_y, 'Y')
        
        # set instance variables relating to status
        self.status_time = 0
        self.status_message = ''

        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()

        self.looping = True
        self.thread = threading.Thread(target=self._setup, args=(port,))
        self.thread.start()
        
        self._idle = False
        self.speed_mode = False

    def __del__(self):
        self.looping = False
        self.thread.join()


    def execute_commands(self, commands, block=False):
        if type(commands) == str: # plural s by mistake
            self.execute_command(commands, block)
        for command in commands:
            self.execute_command(command, block=block)

    def execute_command(self, command, block=False): #, block=False, timeout=0.5, reply=True):
        
        logging.debug(command)
        self.input_queue.put(command)
        
        # if self._write(command):
        #     if reply:
        #         self._read()

        #     if block:
        #         # wait until pump status is Idle
        #         ts = time.time()
        #         while not self.idle() and (time.time() > ts + timeout):
        #             time.sleep(0.02)



    def home(self):
        self.execute_command('$H') # do not wait for reply, to have homing go in parallel

    def zero(self):
        self.move(x=0, y=0)

    def move_command(self, x=None, y=None, feed=None):

        if x == None and y == None:
            return
        
        # ensure command does not send stage past limits
        x = bound(0, x, self.x_stage.syringe_depressed_position())
        y = bound(0, y, self.y_stage.syringe_depressed_position())

        commands = ['G1'] if feed else ['G0']
        if x:
            commands.append(f'X{x:.4f}')
        if y:
            commands.append(f'Y{y:.4f}')
        if feed:
            commands.append(f'F{feed:.4f}')

        return ' '.join(commands)

    def move(self, xy=None, x=None, y=None, feed=None, block=False):
        if xy:
            x, y = xy, xy

        command = self.move_command(x=x, y=y, feed=feed)
        self.execute_command(command, block=block)


    def ml(self, x=None, y=None, feed=None, block=False):
        pos_x = self.x_stage.syringe_volume_position(x)
        pos_y = self.y_stage.syringe_volume_position(y)
        self.move(x=pos_x, y=pos_y, feed=feed, block=block)

    def get_config(self):
        self._write('$$')
        pos = self._read(35)
        logging.debug(pos)
        print(pos)

    def get(self):
        self._write('?')
        pos = self._read(2)
        logging.debug(pos)
        return pos.split('\n')[0]

    def get_status(self):
        new_time = time.time()
        if new_time - self.status_time > 0.005: # only collect enw data if 5ms since last
            self.status_time = new_time
            self.status_message = self.get()
        return self.status_message

    def set_position(self, message):
        #<Idle|MPos:11.000,0.000,0.000|FS:0,0|WCO:0.000,0.000,0.000>
        try:
            m = message
            m = m.replace('<' ,'')
            m = m.replace('>' ,'')
            m = m.split('|')[1]
            m = m.split(':')[1]
            m = m.split(',')
            x,y = m[0:2]

            self.x_stage.position = float(x)
            self.y_stage.position = float(y)
            # print('updated position base on message', message)
        except:
            logging.info('Error from position')
            # print(f'Error, could not set position. Status: {m}')
            
    def idle(self):
        return self._idle
        # status = self.get_status()
        # # print(status)
        # return 'Idle' in status.split('|')[0]

    def wait_til_ready(self):
        while not self.idle():
            time.sleep(0.01) 

    # removed comment from gcode string
    @staticmethod
    def removeComment(string):
        if (string.find(';')==-1):
            return string
        else:
            return string[:string.index(';')]



    ### Asynchronous communication with pump

    def _setup(self, port, set_config = True):
        self.serial = serial.Serial(port, 115200, timeout=1)
        time.sleep(1) 
        self.serial.flushInput()  # Flush startup text in serial input
        time.sleep(1)

        while self.serial.in_waiting:
            _ = self._read()
            time.sleep(0.1)
        
        if set_config:
            self.set_config()
        self.home()
        self._loop()

    def _loop(self):
        self.t0 = time.time()
        
        message = ''

        while self.looping:
            # write
            if not self.input_queue.empty():
                message = self.input_queue.get()
                self._write(message)
            
            # read
            bytes = self.serial.read_all()
            if bytes:
                message = message + str(bytes, 'utf-8')
                messages = message.split('\n')
                
                message = messages[-1]
                
                for m in messages[:-1]:
                    # self.output_queue.put(m)
                    if '<' in m and '>' in m:
                        self.set_position(m)
                        self._idle = 'idle' in m.lower()
            
            # every second, query current position
            if not self.speed_mode and time.time() > self.t0 + 1:
                self._write('?')
                self.t0 = time.time()

            time.sleep(0.001)
            

    '''
    Writes to connected serial device. 
    Returns true if command seems valid and is sent.
    '''
    def _write(self, string):
        
        string = self.removeComment(string)
        string = string.strip() # Strip all EOL characters for streaming

        if string:
            self.serial.write(bytes(string + '\n', 'utf-8'))
            return True

        return False

    '''
    Reads from connected serial device.
    '''
    def _read(self, lines=1):

        answers = []

        for _ in range(lines):
            a = self.serial.read_until()
            a = str(a, 'utf-8')
            answers.append(a.strip())
        
        return '\n'.join(answers)

    def set_config(self):
        configurations = [
            '$22=1',
            '$23=3',
            '$100=1613',
            '$101=1613',
            '$130=95',
            '$131=95',
            '$24=80',
            '$120=200.000',
            '$121=200.000',
            '$26=500',
            '$110=1000', # max rate for x 
        ]
        for c in configurations:
            self.execute_command(c)



# consumer design pattern

class Device:

    def __init__(self, port):
        self.port = port

        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()

    def get(self):
        return # override

    def set(self):
        return # override


if __name__ == '__main__':

    port = MKUsbLocator.ask_user()
    if port == None:
        exit()

    p = SyringePump(port, '10mL', '10mL')