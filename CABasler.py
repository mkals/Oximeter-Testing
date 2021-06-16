from pypylon import pylon
from PIL import Image, ImageOps
import matplotlib.pyplot as plt
import cv2
import pytesseract
import time

import MKSerialWriter 

#   install pypylon https://github.com/basler/pypylon/blob/master/README.md
#   pip3 install pypylon

#install tesseract (on Mac)
#   ''' brew install tesseract'''

image_number = 0

def camera_open():
    global camera
    camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
    camera.Open()
    camera.PixelFormat = "Mono8"
    # demonstrate some feature access

    camera.ExposureTime.SetValue(120000)


def new_directory():
    global directory, image_number
    directory = MKSerialWriter.generate_image_directory()
    image_number = 0

def camera_close():
    global camera
    camera.Close()

def camera_grab():
    global camera, directory, image_number
    numberOfImagesToGrab = 1
    camera.StartGrabbingMax(numberOfImagesToGrab)

    while camera.IsGrabbing():
        grabResult = camera.RetrieveResult(500, pylon.TimeoutHandling_ThrowException)
        if grabResult.GrabSucceeded():
            # Access the image data.
            img = grabResult.Array
            
            #print("Gray value of first pixel: ", img[0, 0])
            
            im=Image.fromarray(img)
            #plt.gray
            #plt.imshow(im)

            filename = MKSerialWriter.generate_image_file(directory, image_number)
            im.save(filename)
            image_number += 1
        
        grabResult.Release()
    #return img


def change_contrast(img, level):
    factor = (259 * (level + 255)) / (255 * (259 - level))
    print(factor)
    def contrast(c):
        return factor * (c)
    return img.point(contrast)



if __name__ == '__main__':

    camera_open()
    t0 = time.time()
    image_count = 10
    for i in range(image_count):
        camera_grab()
    print(f'Framerate {image_count/(time.time()-t0)} FPS')
    camera_close()
