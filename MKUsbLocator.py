import os
from sys import platform


# locate USB devies according to platform

if 'linux' in platform:
    PORT_DIRECTORY = '/dev'
    USB_PATTERN = '.usb'

elif 'darwin' in platform:
    PORT_DIRECTORY = '/dev'
    USB_PATTERN = 'tty.usb'

elif 'win' in platform:
    PORT_DIRECTORY = '/dev'  # TODO
    USB_PATTERN = '.usb'    # TODO


# lists all USB devices as strings
def find_usb_devices():
    return [f for f in os.listdir(PORT_DIRECTORY) if USB_PATTERN in f]


# presents user with found USB portrs and asks to select if multiple candidates
def ask_user(in_use=[]):

    ports = find_usb_devices()
    ports = [p for p in ports if f'{PORT_DIRECTORY}/{p}' not in in_use]

    if len(ports) == 0:
        print('No devices found.')
        return None

    elif len(ports) == 1:
        port = ports[0]

    else:

        # multiple devies to choose from, present user with options
        print('Type index of device you want to use (default 0).')
        for i, d in enumerate(ports):
            print(f'  {i}: {d}')

        while True:
            try:
                s = input('  ')
                selection = '0' if s == '' else s
                port = ports[int(selection)]
                break  # break only when device assignment is successfull
            except KeyboardInterrupt:
                break
            except:
                pass

    return f'{PORT_DIRECTORY}/{port}'


if __name__ == '__main__':
    for d in find_usb_devices():
        print(d)
