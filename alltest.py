#!/usr/bin/env python3

import gpsd
import time
from mpu6050 import mpu6050 #imu library
#import numpy as np
import math
from datetime import datetime
import time
import csv
from traceback_with_variables import activate_by_import

# Connect to the local gpsd
gpsd.connect()

#global variables
mpu = mpu6050(0x68) #0x68 is device address on i2c bus

start_time=time.time() #save date and time of script start (seconds since epoch - UTC)

recording_time=20 #time of recording in seconds
Tp=0.02
date_diff=prev_diff=ax=ay=az=a_length=0
debug=0

start_datetime=datetime.fromtimestamp(start_time)

#this is the main data file
file_name='Saved_data/data'+str(start_datetime.year)+'-'+str(start_datetime.month)+'-'+str(start_datetime.day)+'-'+str(start_datetime.hour)+'-'+str(start_datetime.minute)+'-'+str(start_datetime.second)+'.csv'
csv_file=open(file_name, 'w+', encoding='UTF8', newline='')
writer=csv.writer(csv_file, delimiter=';')
writer.writerow(['t','ax','ay','az','a_length','latitude','longitude','speed'])

if debug:
    #this file is used for debugging purposes
    csv_file_debug=open('Saved_data/data'+str(start_datetime.year)+'-'+str(start_datetime.month)+'-'+str(start_datetime.day)+'-'+str(start_datetime.hour)+'-'+str(start_datetime.minute)+'-'+str(start_datetime.second)+'debug.csv', 'w+', encoding='UTF8', newline='')
    debug_writer=csv.writer(csv_file_debug, delimiter=';')
    debug_writer.writerow(['t','date_diff','new_date_diff','newsleep'])

#first write in order to sync time
accel_data = mpu.get_accel_data() #accelerometer data acquisition
ax=accel_data['x']
ay=accel_data['y']
az=accel_data['z'] #save accelerometer elements to variables

a_length=math.sqrt(ax**2+ay**2+az**2) #calculate [ax, ay, az] length

packet = gpsd.get_current()

while True:
    date_diff=time.time()-start_time
    writer.writerow([date_diff, ax, ay, az, a_length, packet.lat, packet.lon, packet.hspeed])
    if date_diff>=recording_time:
        csv_file.close()
        exit()
        
    #print("Temp : "+str(mpu.get_temp())) #thermometer module (unused)
    
    #accelerometer data acquisition
    accel_data = mpu.get_accel_data() 
    ax=accel_data['x']
    ay=accel_data['y']
    az=accel_data['z'] #save accelerometer elements to variables
    
    a_length=math.sqrt(ax**2+ay**2+az**2) #calculate [ax, ay, az] length
    
    # Get gps position
    packet = gpsd.get_current()

    newsleep=Tp-((time.time()-start_time)-date_diff)
    if debug:
        debug_writer.writerow([time.time(),date_diff,time.time()-start_time,newsleep])
    if newsleep<=0:
        newsleep=0
        print('something happened')
    time.sleep(newsleep) 