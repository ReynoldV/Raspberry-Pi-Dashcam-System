# -----------------------------------------------------------------------------------------
#This section includes libraries pertaining to the program

import struct
import smbus
import sys
import RPi.GPIO as GPIO
from picamera import PiCamera, Color
import datetime as dt
import os
import shutil
from time import sleep

# -----------------------------------------------------------------------------------------
# This section includes functions pertaining to the battery module

def readCapacity(bus):
    #This function returns as a float the remaining capacity of the battery
    address = 0x36
    read = bus.read_word_data(address, 0x04)
    swapped = struct.unpack("<H", struct.pack(">H", read))[0]
    capacity = swapped / 256
    return capacity


def QuickStart(bus):
    address = 0x36
    bus.write_word_data(address, 0x06, 0x4000)


def PowerOnReset(bus):
    address = 0x36
    bus.write_word_data(address, 0xFE, 0x0054)


# -----------------------------------------------------------------------------------------
# This section includes functions pertaining to file management

def StorageSpace(File_Path):
    #This function determines the amount of free storage space on the flash drive
    total, used, free = shutil.disk_usage(File_Path)
    print("Free: %d GiB" % (free // (2 ** 30)))
    return (free // (2 ** 30))


def DeleteOldest(File_Path):
    #This function deletes the oldest file from flash drive if there is low amount of free storage space
    os.chdir(File_Path)
    files = sorted(os.listdir(os.getcwd()), key=os.path.getmtime)
    oldest = files[0]
    os.remove(oldest)
    #The below line will re-examine the amount of free space available
    free_space = StorageSpace(File_Path)
    #If there is still not enough free space, another file will be deleted
    if free_space <= 2:
        DeleteOldest(File_Path)


# -----------------------------------------------------------------------------------------
# This section includes functions pertaining to the camera module

def VideoRecord(File_Path):
    #This function records 1 minute video with a timestamp overlay
    File_Name = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    camera.start_preview()
    camera.annotate_text_size = 50
    camera.annotate_foreground = Color("yellow")
    camera.annotate_background = Color("black")
    camera.annotate_text = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    camera.start_recording(File_Path + File_Name + ".h264")
    start = dt.datetime.now()
    while (dt.datetime.now() - start).seconds < 60:
        camera.annotate_text = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        camera.wait_recording(0.2)
    camera.stop_recording()
    camera.stop_preview()

# -----------------------------------------------------------------------------------------
#This section includes functions pertaining to the motion sensor module

def Motion():
    #This function detects motion
    while True:
        i = GPIO.input(17)
        if i == GPIO.LOW: #When output from motion sensor is LOW
            return False
        elif i == GPIO.HIGH: #When output from motion sensor is HIGH
            return True


# -----------------------------------------------------------------------------------------
# This section setups up the raspberry pi gpio pin interface

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(4, GPIO.IN)
GPIO.setup(17, GPIO.IN, GPIO.PUD_DOWN)
GPIO.setup(16, GPIO.IN, GPIO.PUD_DOWN)

# -----------------------------------------------------------------------------------------
#This section sets up constants

#The 2 constants below define the hours where  the dashcam should 100% be turned off
After_Hours_Before_Midnight = 230000
After_Hours_After_Midnight = 40000
#This constant defines the file path to where the videos will be saved to
File_Path = "/mnt/DASHCAM/February 2022 Tests/"

# -----------------------------------------------------------------------------------------
#This section is the main structure of the program. All decision making is done here
bus = smbus.SMBus(1)  # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)

PowerOnReset(bus)
QuickStart(bus)

camera = PiCamera()
camera.resolution = (1920, 1080)
camera.framerate = 30

while True:
    #When the dashcam is hooked up to car power, it will record video
    if GPIO.input(16) == GPIO.HIGH:
            free_space = StorageSpace(File_Path)
            if free_space < 2:
                DeleteOldest(File_Path)
            VideoRecord(File_Path)
    #When the dashcam is no longer hooked up to car power, it will only record video if there is motion
    if GPIO.input(16) == GPIO.LOW:
            #If the battery capacity is below 5%, the dashcam will shutdown
            if readCapacity(bus) < 5:
                os.system("sudo shutdown -h now")
            if Motion() == True:
                free_space = StorageSpace(File_Path)
                if free_space < 2:
                    DeleteOldest(File_Path)
                VideoRecord(File_Path)
            print(readCapacity(bus))
            #The dashcam will always be turned off during the hours of 11pm and 4am
            if int(dt.datetime.now().strftime("%H%M%S")) >= After_Hours_Before_Midnight:
                os.system("sudo shutdown -h now")
            if int(dt.datetime.now().strftime("%H%M%S")) <= After_Hours_After_Midnight:
                os.system("sudo shutdown -h now")