
from CASyringePump import *


'''
Goal: 
Spesify what movements the syringe pump should take. - Tranlsate high-level programs to actions taken by pumps.
'''




'''
Dual move 1: 
- X and Y on P1 in lock-step with duty-cycle sweep 
- X on P2 alternating to give pulse
'''
def d1(p1, p2):
    pass



    # Alternates liquid from the two syringes.
#    - step volume (uL/step), volume of liquid ejected during a full cycle
#    - duty cycle, DC=1 -> 100% X steps
#    - step frequency (Hz)
#    - x_start_volume (mL), initial volume position for plunger
#    - y_start_volume (mL), initial volume position for plunger    
#    - steps, totoal number of steps to execute (stops before if empty)
def alternate(self, step_volume, duty_cycle, step_frequency, steps = -1):

    logging.info(f'alternate, {steps}, {step_volume}, {duty_cycle}, {step_frequency}, {steps}')

    step_period = 1/step_frequency

    output = []

    ########

    # Step
    x_speed = step_volume / self.x.syringe.volume_per_distance / step_period*60   # mm/min -> [mL]/[mL/mm]/[s]*60
    y_speed = step_volume / self.y.syringe.volume_per_distance / step_period*60   # mm/min -> [mL]/[mL/mm]/[s]*60
    
    x_pos = self.x.position
    y_pos = self.y.position

    x_distance = self.x.syringe_depressed_position() - x_pos
    y_distance = self.y.syringe_depressed_position() - y_pos

    average_duty_cycle = duty_cycle
    x_distance_per_step = average_duty_cycle * step_volume / self.x.syringe.volume_per_distance
    y_distance_per_step = (1-average_duty_cycle) * step_volume / self.y.syringe.volume_per_distance
    
    x_steps = x_distance / x_distance_per_step
    y_steps = y_distance / y_distance_per_step

    limiting_steps = min(x_steps, y_steps)

    if steps != -1:
        limiting_steps = min(limiting_steps, steps)

    duration = limiting_steps * step_period # s
    end_time = time.time() + duration

    #######

    # Step
    x_speed = step_volume / self.x.syringe.volume_per_distance / step_period*60   # mm/min -> [mL]/[mL/mm]/[s]*60
    y_speed = step_volume / self.y.syringe.volume_per_distance / step_period*60   # mm/min -> [mL]/[mL/mm]/[s]*60
    x_step_distance = step_volume / self.x.syringe.volume_per_distance * duty_cycle
    y_step_distance = step_volume / self.y.syringe.volume_per_distance * (1-duty_cycle)

    x_pos = self.x.position
    y_pos = self.y.position

    while x_pos < self.x.syringe_depressed_position() and y_pos < self.y.syringe_depressed_position() and steps != 0:

        output.append(f'G1 X{x_pos} F{x_speed}')
        output.append(f'G1 Y{y_pos} F{y_speed}')

        x_pos += x_step_distance
        y_pos += y_step_distance

        steps -= 1 # decrement steps

    self.x.position = x_pos
    self.y.position = y_pos

    self.execute_commands(output)

    return end_time


# Alternates liquid from the two syringes.
#    - step volume (uL/step), volume of liquid ejected during a full cycle
#    - duty cycle, DC=1 -> 100% X steps
#    - step frequency (Hz)
#    - x_start_volume (mL), initial volume position for plunger
#    - y_start_volume (mL), initial volume position for plunger    
#    - steps, totoal number of steps to execute (stops before if empty)
def vary_dutycycle(self, step_volume, step_frequency, start_duty_cycle=0, end_duty_cycle=1):

    logging.info(f'vary_dutycycle, {step_volume}, {step_frequency}, {start_duty_cycle}, {end_duty_cycle}')

    step_period = 1/step_frequency

    output = []

    # Step
    x_speed = step_volume / self.x.syringe.volume_per_distance / step_period*60   # mm/min -> [mL]/[mL/mm]/[s]*60
    y_speed = step_volume / self.y.syringe.volume_per_distance / step_period*60   # mm/min -> [mL]/[mL/mm]/[s]*60
    
    x_pos = self.x.position
    y_pos = self.y.position

    x_distance = self.x.syringe_depressed_position() - x_pos
    y_distance = self.y.syringe_depressed_position() - y_pos

    average_duty_cycle = (start_duty_cycle + end_duty_cycle)/2
    x_distance_per_step = average_duty_cycle * step_volume / self.x.syringe.volume_per_distance
    y_distance_per_step = (1-average_duty_cycle) * step_volume / self.y.syringe.volume_per_distance
    
    x_steps = x_distance / x_distance_per_step
    y_steps = y_distance / y_distance_per_step

    limiting_steps = min(x_steps, y_steps)

    duty_cycles = np.linspace(start_duty_cycle, end_duty_cycle, num=int(limiting_steps))

    duration = limiting_steps * step_period # s
    end_time = time.time() + duration


    for duty_cycle in duty_cycles:

        if x_pos < self.x.syringe_depressed_position() and y_pos < self.y.syringe_depressed_position():
            pass
        else:
            print('bad, limits reached')
            break
        
        x_step_distance = step_volume / self.x.syringe.volume_per_distance * duty_cycle
        y_step_distance = step_volume / self.y.syringe.volume_per_distance * (1-duty_cycle)

        output.append(f'G1 X{x_pos} F{x_speed}')
        output.append(f'G1 Y{y_pos} F{y_speed}')

        x_pos += x_step_distance
        y_pos += y_step_distance

    self.x.position = x_pos
    self.y.position = y_pos

    self.execute_commands(output)

    return end_time


def pullback(self, step_volume, step_frequency, steps = -1):
    logging.info(f'alternate single backstep, {steps}, {step_volume}, {step_frequency}, {steps}')

    duty_cycle = 0.5
    step_period = 1/step_frequency

    output = []

    # Step
    x_speed = step_volume / self.x.syringe.volume_per_distance / step_period*60   # mm/min -> [mL]/[mL/mm]/[s]*60
    x_step_distance = step_volume / self.x.syringe.volume_per_distance * duty_cycle

    x_pos = self.x.position

    x_speed = x_speed * 3

    while x_pos < self.x.syringe_depressed_position() and steps != 0:

        b_pos = x_pos-x_step_distance
        f_pos = x_pos

        output.append(f'G1 X{b_pos} Y{f_pos} F{x_speed}')
        output.append(f'G1 X{f_pos} Y{b_pos} F{x_speed}')

        x_pos += x_step_distance

        steps -= 1 # decrement steps

    self.x.position = x_pos

    self.execute_commands(output)



    ########

    # Step
    x_speed = step_volume / self.x.syringe.volume_per_distance / step_period*60   # mm/min -> [mL]/[mL/mm]/[s]*60
    y_speed = step_volume / self.y.syringe.volume_per_distance / step_period*60   # mm/min -> [mL]/[mL/mm]/[s]*60
    
    x_pos = self.x.position
    y_pos = self.y.position

    x_distance = self.x.syringe_depressed_position() - x_pos
    y_distance = self.y.syringe_depressed_position() - y_pos

    average_duty_cycle = duty_cycle
    x_distance_per_step = average_duty_cycle * step_volume / self.x.syringe.volume_per_distance
    y_distance_per_step = (1-average_duty_cycle) * step_volume / self.y.syringe.volume_per_distance
    
    x_steps = x_distance / x_distance_per_step
    y_steps = y_distance / y_distance_per_step

    limiting_steps = min(x_steps, y_steps)

    if steps != -1:
        limiting_steps = min(limiting_steps, steps)

    duration = limiting_steps * step_period # s
    end_time = time.time() + duration

    return end_time
    ####### 
