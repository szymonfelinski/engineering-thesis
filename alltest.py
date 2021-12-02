#!/usr/bin/env python3

import gpsd #gps library
import time
from mpu6050 import mpu6050 #imu library
#import numpy as np
import math
from datetime import datetime
import time
import csv
from traceback_with_variables import activate_by_import

#display libraries
import time
from pathlib import Path
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.virtual import terminal
from PIL import ImageFont

# Connect to the local gpsd
gpsd.connect() #this takes a while

#DISPLAY
#init display
serial = i2c(port=1, address=0x3C) #configure address in i2c bus
device = sh1106(serial)

def make_font(name, size): #this function resolves the font file
    font_path = str(Path(__file__).resolve().parent.joinpath('fonts', name))
    return ImageFont.truetype(font_path, size)
    
font = make_font("FreePixel.ttf", 12)
term = terminal(device, font)
term.animate = False #typing-like animation

MY_CUSTOM_BITMAP_FONT = [
        [
            0x00, 0x3e, 0x08, 0x3e, 0x00, 0x3e, 0x2a, 0x22,
            0x00, 0x3e, 0x20, 0x20, 0x00, 0x3e, 0x0a, 0x0e
        ],
        [
            0x00	,0x32	,0x2a	,0x26	,0x00	,0x3e	,0x22	,0x3e	,0x00	,0x26	,0x2a	,0x32	,0x00	,0x3e	,0x00	,0x3c	,0x12	,0x3c

        ]
    ]
#END OF DISPLAY

#global variables
mpu = mpu6050(0x68) #0x68 is device address on i2c bus

start_time=time.time() #save date and time of script start (seconds since epoch - UTC)

recording_time=5 #time of recording in seconds
Tp=0.2
date_diff=prev_diff=ax=ay=az=a_length=0 #init variables
debug=0

start_datetime=datetime.fromtimestamp(start_time) #generate readable datetime

#this is the main data file
file_name='Saved_data/data'+str(start_datetime.year)+'-'+str(start_datetime.month)+'-'+str(start_datetime.day)+'-'+str(start_datetime.hour)+'-'+str(start_datetime.minute)+'-'+str(start_datetime.second)+'.csv'
csv_file=open(file_name, 'w+', encoding='UTF8', newline='')
writer=csv.writer(csv_file, delimiter=';')
writer.writerow(['t','ax','ay','az','a_length','latitude','longitude','speed']) #csv headers

if debug:
    #this file is used for debugging purposes
    csv_file_debug=open('Saved_data/data'+str(start_datetime.year)+'-'+str(start_datetime.month)+'-'+str(start_datetime.day)+'-'+str(start_datetime.hour)+'-'+str(start_datetime.minute)+'-'+str(start_datetime.second)+'debug.csv', 'w+', encoding='UTF8', newline='')
    debug_writer=csv.writer(csv_file_debug, delimiter=';')
    debug_writer.writerow(['t','date_diff','new_date_diff','newsleep'])

while True:
    date_diff=time.time()-start_time #save current loop timestamp in relation to starting time
    
    if date_diff>=recording_time:
        csv_file.close()
        exit()
    #print("Temp : "+str(mpu.get_temp())) #thermometer module (unused)
    
    #accelerometer data acquisition
    accel_data = mpu.get_accel_data() 
    ax=accel_data['x']
    ay=accel_data['y']
    az=accel_data['z'] #save accelerometer elements to variables
    
    a_length=math.sqrt(ax**2+ay**2+az**2) #calculate [ax, ay, az] length (slightly faster than numpy)
    
    # Get gps position
    packet = gpsd.get_current()
    
    #term.carriage_return()
    #term.puts("Przyspieszenie:"+str(round(a_length,2)))
    
    writer.writerow([date_diff, ax, ay, az, a_length, packet.lat, packet.lon, packet.hspeed])
    
    newsleep=Tp-((time.time()-start_time)-date_diff)
    if debug:
        debug_writer.writerow([time.time(),date_diff,time.time()-start_time,newsleep])
    
    if newsleep<=0:
        newsleep=0
        print('something happened')
    time.sleep(newsleep) 