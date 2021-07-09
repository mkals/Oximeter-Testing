

from Arduino import Arduino
import time

A0 = 14
A1 = 15
A2 = 16
A3 = 17
A4 = 18

header_string = 'p1,p2'


def connect(port="/dev/tty.usbmodem143201"):
    global board

    # plugged in via USB, serial com at rate 115200
    board = Arduino("115200", port=port)
    board.pinMode(A1, "INPUT")
    board.pinMode(A2, "INPUT")
    board.pinMode(A3, "INPUT")
    board.pinMode(A4, "INPUT")


def readVoltage(pin):
    global board
    return board.analogRead(pin) / 2**10 * 5


def severinghaus(x):
    if x == 0:
        return 0
    return ((((x**3+150*x)**-1 * 23400)+1)**-1) * 100


def read():
    mmhg1 = (readVoltage(A4)/5)*200
    #so1 = severinghaus(mmhg1)
    #temp1 = (readVoltage(A3)/5)*50

    mmhg2 = (readVoltage(A2)/5)*200
    #so2 = severinghaus(mmhg2)
    #temp2 = (readVoltage(A1)/5)*50

    return (mmhg1, mmhg2)
    # return [mmhg1, so1, mmhg2, so2]


if __name__ == '__main__':
    connect()
    a, b = read()
    print(a, b)
