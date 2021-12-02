#!/usr/bin/env python3

gDebug=0 #will the csv debug file be written?
gLog=1 #will the csv data file be written? (if 0, the program has no stop condition!)
gDisplayData=1 #display data on the display?
stop_after_time_passed=0 #will the program stop after the amount of time set in recording_time?
gRecording_time=1800 #time of recording in seconds
Tp=0.2 #discrete step time, framerate
warning_threshold=12 #acceleration at which a message will appear

road="unresolved"
house="unresolved"

import asyncio

import gpsd #gps library
from OSMPythonTools.nominatim import Nominatim #maps library (reverse geocoding)
import time
from mpu6050 import mpu6050 #imu library
import math
import time
import csv
from traceback_with_variables import activate_by_import

if display:
    #display libraries
    from luma.core.render import canvas
    from luma.core import legacy
    from luma.oled.device import sh1106
    from luma.core.interface.serial import i2c

#global variables
start_time=time.time() #save date and time of script start (seconds since epoch - UTC)

mpu = mpu6050(0x68) #0x68 is device address on i2c bus

# Connect to the local gpsd
gpsd.connect() #this takes a while (MUST BE SET UP USING sudo gpsd /dev/serial0 -F /var/run/gpsd.sock !!! #EDIT 6/8/21 - added automatic execution at system startup.)

geocode_api=Nominatim() #binding reverse geocoding to a process variable
#reverse_geocode_result = geocode_api.query(40.714224, -73.961452, reverse=True)
#print(reverse_geocode_result.displayName())

#DISPLAY
#init display
def displayInit():
    serial = i2c(port=1, address=0x3C) #configure address in i2c bus
    display = sh1106(serial) #binding display to process variable
    d=[128, 64] #screen size in pixels
    
    MY_CUSTOM_BITMAP_FONT = [ # Note that "\0" is the zero-th character in the font
        [
            0x00, 0x3e, 0x08, 0x3e, 0x00, 0x3e, 0x2a, 0x22,
            0x00, 0x3e, 0x20, 0x20, 0x00, 0x3e, 0x0a, 0x0e
        ], #HELP
        [
            0x00	,0x32	,0x2a	,0x26	,0x00	,0x3e	,0x22	,0x3e	,0x00	,0x26	,0x2a	,0x32	,0x00	,0x3e	,0x00	,0x3c	,0x12	,0x3c

        ],#ZOSIA
        [
            0xff	,0x81	,0x81	,0xff
        ],#O
        [
			0x00	,0x46	,0x89	,0x89	,0x89	,0x72	,0x00	,0xff	,0x11	,0x11	,0x11	,0x01	,0x60	,0x96	,0xa9	,0xa6	,0x40	,0xa0	,0x00	,0xff	,0x06	,0x08	,0x06	,0xff	,0x00	,0xff	,0x81	,0x81	,0x81	,0x7e
        ]#SF&MD
        ]
#END OF DISPLAY

start_datetime=time.localtime(start_time)

def loggingFuncInit():
    #this is the main data file
    file_name='Saved_data/data'+str(start_datetime.tm_year)+'-'+str(start_datetime.tm_mon)+'-'+str(start_datetime.tm_mday)+'-'+str(start_datetime.tm_hour)+'-'+str(start_datetime.tm_min)+'-'+str(start_datetime.tm_sec)+'.csv'
    csv_file=open(file_name, 'w+', encoding='UTF8', newline='')
    writer=csv.writer(csv_file, delimiter=';')
    writer.writerow(['t','ax','ay','az','a_length','latitude','longitude','speed', 'Street Name', 'House Number']) #csv headers

def debugFuncInit():
    #this file is used for debugging purposes
    csv_file_debug=open('Saved_data/data'+str(start_datetime.tm_year)+'-'+str(start_datetime.tm_mon)+'-'+str(start_datetime.tm_mday)+'-'+str(start_datetime.tm_hour)+'-'+str(start_datetime.tm_min)+'-'+str(start_datetime.tm_sec)+'debug.csv', 'w+', encoding='UTF8', newline='')
    debug_writer=csv.writer(csv_file_debug, delimiter=';')
    debug_writer.writerow(['t','date_diff','new_date_diff','newsleep'])

while True:
    cur_time=time.time()
    date_diff=cur_time-start_time #save current loop timestamp in relation to starting time
    
    
    if date_diff>=recording_time and log and stop_after_time_passed:
       csv_file.close()
       exit()
    #print("Temp : "+str(mpu.get_temp())) #thermometer module (unused)
    
    # Get gps position
    try:
        packet = gpsd.get_current()
    except:
        print("Can't resolve GPS")
    
    #resolve reverse geocoded address
    try:
        reverse_geocode_result = geocode_api.query(packet.lat, packet.lon, reverse=True, zoom=18) #takes a while at boot
    except:
        print("Can't resolve address")
        
    oldroad=road
    oldhouse=house
    
    #fallback to old address if reverse geocoding failed
    try:
        #legacy.text(draw, (0, d[1]-8), reverse_geocode_result.address()['road']+" "+reverse_geocode_result.address()['house_number'], fill="white", font=legacy.font.TINY_FONT)
        #print(reverse_geocode_result.displayName())
        road=reverse_geocode_result.address()['road']
        house=reverse_geocode_result.address()['house_number']
        print(road+" "+house)
    except:
        house=oldhouse
        road=oldroad
        print("Old: "+road+" "+house)
    
    #accelerometer data acquisition
    try:
        accel_data = mpu.get_accel_data() 
        ax=accel_data['x']
        ay=accel_data['y']
        az=accel_data['z'] #save accelerometer elements to variables
        
        a_length=math.sqrt(ax**2+ay**2+az**2) #calculate [ax, ay, az] length (slightly faster than numpy)
    except:
        print("Can't resolve accelerometer data") #literally never happened
    
    if gDisplayData:
        try:
            cur_timestamp=time.localtime(cur_time)
            with canvas(display) as draw: #execution time: around 100ms (good!)
                if cur_timestamp.tm_min<10:
                    legacy.text(draw, (0, 0), str(cur_timestamp.tm_hour)+":0"+str(cur_timestamp.tm_min), fill="white")
                else:
                    legacy.text(draw, (0, 0), str(cur_timestamp.tm_hour)+":"+str(cur_timestamp.tm_min), fill="white")
                
                if log:
                    try:
                        s="logging"
                        legacy.text(draw, (d[0]/2-len(s)*5/2,0), s, fill="white", font=legacy.font.TINY_FONT)
                    except:
                        legacy.text(draw, (d[0]/2,0), " ", fill="white", font=legacy.font.TINY_FONT)
                
                try:
                    s="SF&MD"
                    legacy.text(draw, (d[0]-len(s)*8, 0), s, fill="white") #watermark
                except:
                    time.sleep(0)
                
                try:
                    legacy.text(draw, (0, 8), "telepanie: "+str(round(a_length,2)), fill="white", font=legacy.font.SINCLAIR_FONT)
                except:
                    time.sleep(0)
                
                try:
                    legacy.text(draw, (0, 13), str(packet.lat), fill="white", font=legacy.font.TINY_FONT)
                    legacy.text(draw, (0, 18), str(packet.lon), fill="white", font=legacy.font.TINY_FONT)
                except:
                    time.sleep(0)
                
                try:
                    if a_length>warning_threshold:
                        s="ZWOLNIJ"
                        legacy.text(draw, (d[0]/2-len(s)*8/2, d[1]/2), s, fill="white")
                except:
                    legacy.text(draw, (d[0]/2, d[1]/2), " ", fill="white")
                
                try: #gps satellite count
                    legacy.text(draw, (0, d[1]-22), "Sats: "+str(packet.sats), fill="white", font=legacy.font.SINCLAIR_FONT)
                except:
                    legacy.text(draw, (0, d[1]-22), " ", fill="white", font=legacy.font.SINCLAIR_FONT)
                
                try: #speed as reported by gps
                    legacy.text(draw, (0, d[1]-14), "Speed: "+str(packet.hspeed), fill="white", font=legacy.font.SINCLAIR_FONT)
                except:
                    legacy.text(draw, (0, d[1]-14), "Speed: unknown", fill="white", font=legacy.font.SINCLAIR_FONT)
                
                try: #address display
                    legacy.text(draw, (0, d[1]-6), road+" "+house, fill="white", font=legacy.font.TINY_FONT) #renders address on the bottom of display (TINY_FONT is 5x3 pixels).
                except:
                    legacy.text(draw, (0, d[1]-6), "unknown address", fill="white", font=legacy.font.TINY_FONT)
                    print(reverse_geocode_result)
                    print("No address to display")
                #print(reverse_geocode_result.displayName())
        except:
            print("Can't display data")
    
    if log:
        try:
            writer.writerow([date_diff, ax, ay, az, a_length, packet.lat, packet.lon, packet.hspeed, reverse_geocode_result.address()['road'], reverse_geocode_result.address()['house_number']])
        except:
            writer.writerow([date_diff, ax, ay, az, a_length, packet.lat, packet.lon, packet.hspeed, "unknown", "unknown"])
    
    newsleep=Tp-((time.time()-start_time)-date_diff)
    
    if debug:
        debug_writer.writerow([time.time(),date_diff,time.time()-start_time,newsleep])
    
    if newsleep<=0:
        newsleep=0
        #print('something happened')
    time.sleep(newsleep) 


if __name__ == "__main__":
    