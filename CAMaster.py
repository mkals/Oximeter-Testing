

import threading
import os, sys
import platform
from pathlib import Path
from typing import MutableSequence
import numpy as np

import pandas as pd
import time

import CASyringePump as Sp
import CAOxymeter as Oxy
from CAPulseOximeter import CAPulseOximeter
import CABasler as Cam
import MKUsbLocator

from CASyringePump import SyringePump, logging

pressure_1, pressure_2 = 0,0

sense = True
collect_metadata = False

def update_p():
    global pressure_1, pressure_2
    pressure_2, pressure_1 = Oxy.read()

def clean_df():
    global df
    header_string = f'{bath.header_string},{Oxy.header_string},pump_mixing_ratio,pump_bpm'
    headers = header_string.split(',')
    df = pd.DataFrame(columns=headers)

clean_df()

last_time = time.time()
index = 0

stop = False
oxy_threads = []

pump_mixing_ratio = 0 # duty cycle, set by motion functions
pump_bpm = 0 # beats per minute

def collect_data():
    global last_time, index, df, pump_mixing_ratio, pump_bpm
    
    ps = bath.read()
    ps = ps.strip().split(',')
    ps = [float(p) for p in ps]
    
    if time.time() - last_time >= 1: # update pulse less frequently
        last_time = time.time()
        update_p()

    d = ps + [pressure_1, pressure_2, pump_mixing_ratio, pump_bpm]
    
    df.loc[index] = d
    index += 1

def loop_collect():
    global stop
    while not stop:
        try:
            collect_data()
        except ValueError:
            print('ValueError in loop_collect')
            pass

def loop_camera():
    global stop
    t0 = time.time()
    while not stop:
        Cam.camera_grab()
        delay = 1 - (time.time() - t0)
        delay = max(0, delay)
        time.sleep(delay)
        t0 = time.time()


def generate_file():
	
	# Generate logfile name
	timestring = time.strftime("%Y%m%d_%H%M")
	filename = f"PO_{timestring}.csv"

	directory = 'Oximeter_data/Logs'
	
	file = os.path.join(directory, filename)

	return file


def write_metadata(name, sim_string):
    questions = [
        'Errors',
        'Phantom type', 
        'Melanin concentration',
        'Syringe contents',
        'Pulse oximeter positioin',
        'Oximeter positioin',
        'Notes'
    ]

    def write_line(f, l):
        f.write(f'{l}\n')

    meta = name + '.txt'
    answers = [input(f'{q}? ') for q in questions]

    with open(meta, 'w') as f:
        write_line(f, sim_string)
        for q,a in zip(questions, answers):
            write_line(f, f'{q}: {a}')


def write_to_file(sim_string):
    name = generate_file()
    df.to_csv(name)
    
    print(Cam.directory)
    if collect_metadata:
        write_metadata(name, sim_string)


def start_round(message):
    global oxy_threads

    p1.wait_til_ready()
    p1.speed_mode = True

    if sense:    
        clean_df()
        Cam.new_directory()

        oxy_threads.append(threading.Thread(target=loop_collect, args=()))
        # oxy_threads.append(threading.Thread(target=loop_camera, args=()))
        for t in oxy_threads:
            t.start()

    logging.info(message)


def end_round(message):
    
    global stop, oxy_threads, df

    p1.speed_mode = False

    if sense:
        stop = True
        for t in oxy_threads:
            t.join()
        oxy_threads = []
        stop = False

        write_to_file(message)

        df['timestamp'] = pd.to_datetime(df['time'], unit='s')
        df['so2_1'] = df['p1'].apply(Oxy.severinghoouse)
        df['so2_2'] = df['p2'].apply(Oxy.severinghoouse)


t0 = time.time()
def print_frequency():
    global t0, pump_bpm, pump_mixing_ratio
    t = time.time()
    frequency = 1/(t-t0)
    t0 = t
    pump_bpm = frequency * 60
    print(f'Mixing {pump_mixing_ratio:3.2f}, {pump_bpm:4.1f} bpm, {frequency:4.2f} Hz')


## Motion programs

def alternate(p, step_volume, duty_cycle, step_frequency, steps = -1):
    message = f'alternate, {step_volume}, {duty_cycle}, {step_frequency}, {steps}'

    global pump_mixing_ratio
    pump_mixing_ratio = 1 # no change in overall mixing, assuming PBS in one of the two syringes
    start_round(message)
    
    step_period = 1/step_frequency - 0.11*step_frequency # subtract to compensate for system delays
    output = []

    # Step
    x_speed = step_volume / p.x.syringe.volume_per_distance / step_period*60   # mm/min -> [mL]/[mL/mm]/[s]*60
    y_speed = step_volume / p.y.syringe.volume_per_distance / step_period*60   # mm/min -> [mL]/[mL/mm]/[s]*60
    x_step_distance = step_volume / p.x.syringe.volume_per_distance * duty_cycle
    y_step_distance = step_volume / p.y.syringe.volume_per_distance * (1-duty_cycle)

    x_pos = p.x.position
    y_pos = p.y.position

    while x_pos < p.x.syringe_depressed_position() and y_pos < p.y.syringe_depressed_position() and steps != 0:

        output.append(f'G1 X{x_pos} F{x_speed}')
        output.append(f'G1 Y{y_pos} F{y_speed}')

        x_pos += x_step_distance
        y_pos += y_step_distance

        steps -= 1 # decrement steps

        print_frequency()

    p.x.position = x_pos
    p.y.position = y_pos

    try:
        p.execute_commands(output, block=True) # returns only when done

    except: # to catch cancelations
        pass

    end_round(message)
    

'''
The two pumps pulse
One pump sweeps concentration
p2 uses x axis
'''
def pulse_sweep(p1, p2, step_volume, step_frequency, pulse_dc, start_dc=0, end_dc=1):
    message = f'pulse_sweep, {step_volume}, {step_frequency}, {pulse_dc}, {start_dc}, {end_dc}'
    
    global pump_mixing_ratio
    start_round(message)

    step_period = 1/step_frequency - 0.11*step_frequency # subtract to compensate for system delays

    p1_output = []
    p2_output = []

    mean_dc = (start_dc + end_dc)/2

    x_pos = p1.x_stage_stage.position
    y_pos = p1.y_stage_stage.position
    p2_pos = p2.x_stage.position

    x_steps = p1.x_stage_stage.available_steps(step_volume * pulse_dc * (mean_dc))
    y_steps = p1.y_stage_stage.available_steps(step_volume * pulse_dc * (1-mean_dc))
    p2_steps = p2.x_stage.available_steps(step_volume * (1-pulse_dc))
    limiting_steps = min([x_steps, y_steps, p2_steps])

    duty_cycles = np.linspace(0, np.pi/2, num=int(limiting_steps))
    x_dcs = np.sin(duty_cycles)
    y_dcs = np.cos(duty_cycles)

    for x_dc, y_dc in zip(x_dcs, y_dcs):
        
        pump_mixing_ratio = x_dc # for data-collectioin

        x_step_distance, x_speed = p1.x_stage_stage.step_distance(step_volume * pulse_dc * x_dc, step_period * pulse_dc)
        y_step_distance, y_speed = p1.y_stage_stage.step_distance(step_volume * pulse_dc * y_dc, step_period * pulse_dc)
        p2_step_distance, p2_speed = p2.x_stage.step_distance(step_volume * (1-pulse_dc), step_period * (1-pulse_dc))

        p1_speed = (x_speed**2 + y_speed**2)**0.5

        x_pos += x_step_distance
        y_pos += y_step_distance
        p2_pos += p2_step_distance

        p1_output.append(f'G1 X{x_pos} Y{y_pos} F{p1_speed}')
        p2_output.append(f'G1 X{p2_pos} F{p2_speed}')

    try:
        
        for a, b in zip(p1_output, p2_output):
            p1.execute_command(a, True)
            p2.execute_command(b, True)
            print_frequency()
    except: # to catch cancelations
        pass
    
    end_round(message)



'''
The two pumps pulse
One pump sweeps concentration
p2 uses x axis
'''
def pulse_stay(p1, p2, step_volume, step_frequency, pulse_dc, mix_dc, steps = -1):
    message = f'pulse_stay, {step_volume}, {step_frequency}, {pulse_dc}, {mix_dc}'
    
    global pump_mixing_ratio
    start_round(message)

    step_period = 1/step_frequency - 0.11*step_frequency # subtract to compensate for system delays

    p1_output = []
    p2_output = []

    x_pos = p1.x_stage.position
    y_pos = p1.y_stage.position
    p2_pos = p2.x_stage.position

    x_steps = p1.x_stage.available_steps(step_volume * pulse_dc * (mix_dc))
    y_steps = p1.y_stage.available_steps(step_volume * pulse_dc * (1-mix_dc))
    p2_steps = p2.x_stage.available_steps(step_volume * (1-pulse_dc))
    limiting_steps = min([x_steps, y_steps, p2_steps])

    if steps > 0 :
        limiting_steps = min([limiting_steps, steps])

    for _ in range(limiting_steps):
        
        pump_mixing_ratio = mix_dc # for data-collectioin

        x_step_distance, x_speed = p1.x_stage.step_distance(step_volume * pulse_dc * mix_dc, step_period * pulse_dc)
        y_step_distance, y_speed = p1.y_stage.step_distance(step_volume * pulse_dc * (1-mix_dc), step_period * pulse_dc)
        p2_step_distance, p2_speed = p2.x_stage.step_distance(step_volume * (1-pulse_dc), step_period * (1-pulse_dc))

        p1_speed = (x_speed**2 + y_speed**2)**0.5

        x_pos += x_step_distance
        y_pos += y_step_distance
        p2_pos += p2_step_distance

        p1_output.append(f'G1 X{x_pos} Y{y_pos} F{p1_speed}')
        p2_output.append(f'G1 X{p2_pos} F{p2_speed}')

    try:
        
        for a, b in zip(p1_output, p2_output):
            p1.execute_command(a, True)
            p2.execute_command(b, True)
            print_frequency()
    except: # to catch cancelations
        pass
    
    end_round(message)

def rotate(l, n):
    return l[n:] + l[:n]

t_s = [0, 3, 5,   7,  10]
a_s = [0, 1, 0.5, 0.6, 0]
#a_s = [1, 0, 0.8, 0.7, 1]

def step_in_place(p1, step_volume, t_fractions, a_fractions, step_frequency=1, step_count=60, dc_offset_ml=0):
    
    message = f'step_in_place, {step_volume}, {step_frequency}, {step_count}'
    
    start_round(message)

    step_period = 1/step_frequency/2 # subtract to compensate for system delays

    t_fractions = np.array(t_fractions) / max(t_fractions) # normalize to sum to 1
    a_fractions = np.array(a_fractions) / max(a_fractions) # normalize to 1

    print(t_fractions)
    print(a_fractions)

    x_pos = p1.x_stage.position

    step_distance, _ = p1.x_stage.step_distance(step_volume, step_period)

    positions = [x_pos + a * step_distance for a in a_fractions] # mm
    #periods = [step_period * t for t in t_fractions] # s
    periods = [(b-a) * step_period for a,b in zip(t_fractions, t_fractions[1:])] # s
    d_positions = [b-a for a,b in zip(positions, rotate(positions, -1))] # mm
    speeds = [abs(d/t) * 60 for d, t in zip(d_positions, periods)] # mm/min

    print(positions)
    print(periods)
    print(d_positions)
    print(speeds)

    
    if dc_offset_ml == 0:
        p1_output = [p1.move_command(x=p, y=None, feed=s) for p,s in zip(positions, speeds)]
        p1_output *= step_count
    
    else:

        p1_output = [p1.move_command(x=p, y=None, feed=s) for p,s in zip(positions, speeds)]
        p1_output *= step_count
        

    try:
        ta = time.time()
        for i, a in enumerate(p1_output):
            
            p1.execute_command(a)
            print(a)
            
            # manually sync time once for every step
            if i % len(speeds) == 0:
                delta = (ta + 1/step_frequency) - time.time()
                time.sleep(max(0, delta))
                print(f'{delta}', end='\t')
                print_frequency()
                ta = time.time()
                
    
    except: # to catch cancelations
        pass
    
    end_round(message)



# def setp_in_place_0(p1, step_volume, step_frequency=1, step_count=60):
        
#     message = f'setp_in_place, {step_volume}, {step_frequency}, {step_count}'
    
#     start_round(message)

#     step_period = 1/step_frequency - 0.1*step_frequency # subtract to compensate for system delays

#     x_pos = p1.x_stage.position

#     p1_output = []

#     for _ in range(step_count):

#         x_step_distance, x_speed = p1.x_stage.step_distance(step_volume, step_period/2)

#         p1_output.append(p1.move_command(x=x_pos, y=None, feed=x_speed))
#         p1_output.append(p1.move_command(x=x_pos+x_step_distance, y=None, feed=x_speed))

#     try:
        
#         even = False
#         for a in p1_output:
            
#             ta = time.time()
#             p1.execute_command(a)
            
#             delta = (ta + 1/step_frequency * 0.5) - time.time()
#             time.sleep(max(0, delta))

#             even = not even
#             if even:
#                 print_frequency()
    
#     except: # to catch cancelations
#         pass
    
#     end_round(message)


'''
The two pumps pulse
One pump steps concentration
p2 uses x axis
'''
def pulse_step(p1, p2, step_volume, step_frequency, start_dc=0, end_dc=1, dc_count=6, step_count=360, backstep=0.5):
    
    pulse_dc = 0.5
    
    message = f'pulse_step, {step_volume}, {step_frequency}, {pulse_dc}, {start_dc}, {end_dc}, {dc_count}'
    
    global pump_mixing_ratio
    start_round(message)

    step_period = 1/step_frequency - 0.5*step_frequency # subtract to compensate for system delays

    mean_dc = (start_dc + end_dc)/2

    x_pos = p1.x_stage.position
    y_pos = p1.y_stage.position
    p2_pos = p2.x_stage.position

    x_steps = p1.x_stage.available_steps(step_volume * pulse_dc * (mean_dc))
    y_steps = p1.y_stage.available_steps(step_volume * pulse_dc * (1-mean_dc))
    p2_steps = p2.x_stage.available_steps(step_volume * (1-pulse_dc))
    limiting_steps = min([x_steps, y_steps, p2_steps, step_count])

    steps_per_dc = int(limiting_steps/dc_count)

    duty_cycles = np.linspace(start_dc, end_dc, num=dc_count)
    duty_cycles = np.repeat(duty_cycles, steps_per_dc)

    x_dcs = duty_cycles

    p1_output = []
    p2_output = []
    pump_mixing_ratios = []

    p1_output.append(p1.move_command(x=x_pos, y=y_pos)) # to make x and y out of step

    for x_dc in x_dcs:

        x_step_distance, x_speed = p1.x_stage.step_distance(step_volume * pulse_dc * x_dc, step_period * pulse_dc)
        y_step_distance, y_speed = p1.y_stage.step_distance(step_volume * pulse_dc * (1-x_dc), step_period * pulse_dc)
        p2_step_distance, p2_speed = p2.x_stage.step_distance(step_volume * (1-pulse_dc), step_period * (1-pulse_dc))

        p1_speed = (x_speed**2 + y_speed**2)**0.5
        p2_speed = p2_speed

        x_pos += x_step_distance
        y_pos += y_step_distance
        p2_pos += p2_step_distance
        
        # backstep stuff
        x_backstep_pos = x_pos - x_step_distance * backstep
        y_backstep_pos = y_pos - y_step_distance * backstep
        p2_backstep_pos = p2_pos - p2_step_distance * backstep
        
        p1_backstep_speed = p1_speed * backstep
        p2_backstep_speed = p2_speed * backstep
        p1_speed = p1_speed * (1+backstep)
        p2_speed = p2_speed * (1+backstep)

        p1_output.append(p1.move_command(x=x_pos, y=y_pos, feed=p1_speed))
        p1_output.append(p1.move_command(x=x_backstep_pos, y=y_backstep_pos, feed=p1_backstep_speed))
        
        p2_output.append(p2.move_command(x=p2_pos, y=None, feed=p2_speed))
        p2_output.append(p2.move_command(x=p2_backstep_pos, y=None, feed=p2_backstep_speed))
        
        pump_mixing_ratios.append(x_dc) # pump_mixing_ratio = x_dc
        pump_mixing_ratios.append(x_dc) # pump_mixing_ratio = x_dc

    try:
        
        even = False
        for a, b, mixing_ratio in zip(p1_output, p2_output, pump_mixing_ratios):
            pump_mixing_ratio = mixing_ratio
            
            ta = time.time()
            p1.execute_command(a)
            p2.execute_command(b)
            
            delta = (ta + 1/step_frequency * pulse_dc) - time.time()
            time.sleep(max(0, delta))

            even = not even
            if even:
                print_frequency()
    
    except: # to catch cancelations
        pass
    
    end_round(message)


import matplotlib.pyplot as plt

def plot_s(d):
    plt.figure()
    plt.title('Pulse oximeter reflectance')
    plt.plot(d['timestamp'], d['i'])
    plt.plot(d['timestamp'], d['r'])
    plt.legend(['IR', 'red'])
    plt.xlabel('Time (s)')
    plt.gcf().autofmt_xdate()
    plt.show()

def plot_o(d):
    plt.figure()
    plt.title('Oxygenation')
    plt.plot(d['timestamp'], d['SPO2Avg'], '.')
    plt.plot(d['timestamp'], d['so2_1'], '.')
    plt.plot(d['timestamp'], d['so2_2'], '.')
    plt.legend(['Bath', 'Probe 1', 'Probe 2'])
    plt.xlabel('Time (s)')
    plt.ylabel('Oxygenation (%)')
    plt.gcf().autofmt_xdate()
    # plt.ylim([10,110])
    plt.show()

def home():
    p1.home()
    p2.home()

def zero():
    p1.zero()
    p2.zero()

def ml(x1, y1, x2, y2):
    p1.ml(x=x1, y=y1, block=True)
    p2.ml(x=x2, y=y2, block=True)


if __name__ == '__main__':

    port_p1 = MKUsbLocator.ask_user()
    p1 = Sp.SyringePump(port_p1, '20mL', '20mL')

    bath = CAPulseOximeter()

    # p1.wait_til_ready()
    # time.sleep(10)
    # p1.ml(20, 20, block=True)

    # print(MKUsbLocator.find_usb_devices())

    # ports = [
    #     'tty.usbmodem144301',
    #     'tty.usbserial-1430',
    #     'tty.usbmodem144101',
    #     'tty.usbmodem144201',
    # ]

    # # ports = ['/dev/tty.usbmodem143201', '/dev/tty.usbserial-1440', '/dev/tty.usbmodem144101', '/dev/tty.usbmodem144201']

    # # oxi
    # # pul
    # # p1
    # # p2

    # ports = [f'/dev/{p}' for p in ports]
    # print(f'Ports: {ports}')
    
    # print('initialize Pump 1')
    # p1 = Sp.SyringePump(ports[2], '20mL', '20mL')

    # print('initialize Pump 2')
    # p2 = Sp.SyringePump(ports[3], '20mL', '20mL')

    # if sense:
    #     # print('initializing Oxymeter')
    #     # Oxy.connect(ports[0])
    #     # print('initializing Pulse Oximeter')
        # Pul.connect()
    #     print('initializing Camera')
    #     Cam.camera_open()

    print('initialization compelte')
    
    # def cleanup(*args):
    #     for a in args:
    #         del a

    # import atexit
    # atexit.register(cleanup, p1, p2)

    #alternate(p1, 0.1, 0.5, 1, 10)
    #pulse_sweep(p1, p2, step_volume=0.1, step_frequency=1, pulse_dc=0.5, start_dc=0, end_dc=1)
    #pulse_step(p1, p2, step_volume=0.1, step_frequency=1, pulse_dc=0.5, start_dc=0, end_dc=1, dc_count=6)
    #pulse_step_backstep(p1, p2, step_volume=0.1, step_frequency=1, dc_count=6, backstep=0.5)
    #step_in_place(p1, step_volume=0.5, t_fractions=t_s, a_fractions=a_s, step_frequency=1, step_count=60)
'''
Frequency:
1 -> 0.9
2/0.9 -> 1.8
'''