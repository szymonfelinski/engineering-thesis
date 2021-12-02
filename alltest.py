#!/usr/bin/env python3

gDebug = 0 #will the csv debug file be written?
gLog = 1 #will the csv data file be written? (if 0, the program has no stop condition!)
gDisplayData = 1 #display data on the display?
gReverseGeocode = 0 #attempt to reverse geocode GPS data?
gVerbose = 1 #verbose output in console? (does nothing atm - 06.09.21)
stop_after_time_passed = 0 #will the program stop after the amount of time set in recording_time?
gRecording_time = 1800 #time of recording in seconds
Tp = 0.1 #discrete step time, framerate
warning_threshold = 12 #acceleration at which a message will appear

csv_file = []
csv_file_debug = []
writer = []
writer_debug = []
packet = []
reverse_geocode_result = []
d = [128, 64]

geocode_process = []
display_process = []
main_process = []

road = "unresolved"
house = "unresolved"

import multiprocessing as mp

import gpsd #gps library
from OSMPythonTools.nominatim import Nominatim #maps library (reverse geocoding)
import time
from mpu6050 import mpu6050 #imu library
import math
import time
import csv
from traceback_with_variables import activate_by_import

if gDisplayData:
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
    
#init display
def displayInit():
    serial = i2c(port=1, address=0x3C) #configure address in i2c bus
    display = sh1106(serial) #binding display to process variable
    #d=[128, 64] #screen size in pixels
    return display
#END OF DISPLAY INIT

start_datetime=time.localtime(start_time)

def loggingFuncInit(debug):
    #this is the main data file
    file_name='Saved_data/data'+str(start_datetime.tm_year)+'-'+str(start_datetime.tm_mon)+'-'+str(start_datetime.tm_mday)+'-'+str(start_datetime.tm_hour)+'-'+str(start_datetime.tm_min)+'-'+str(start_datetime.tm_sec)
    if debug:
        file_name=file_name+'debug'
    file_name=file_name+'.csv'
    csv_file_temp=open(file_name, 'w+', encoding='UTF8', newline='')
    writer_temp=csv.writer(csv_file_temp, delimiter=';')
    if debug:
        writer_temp.writerow(['t','date_diff','new_date_diff','newsleep'])
    else:
        writer_temp.writerow(['t','ax','ay','az','a_length','latitude','longitude','speed', 'Street Name', 'House Number']) #csv headers
    return csv_file, writer_temp

#def debugFuncInit(): #old debug file init - removed 08.08.2021
#    #this file is used for debugging purposes
#    csv_file_debug=open('Saved_data/data'+str(start_datetime.tm_year)+'-'+str(start_datetime.tm_mon)+'-'+str(start_datetime.tm_mday)+'-'+str(start_datetime.tm_hour)+'-'+str(start_datetime.tm_min)+'-'+str(start_datetime.tm_sec)+'debug.csv', 'w+', encoding='UTF8', newline='')
#    writer_debug=csv.writer(csv_file_debug, delimiter=';')
#    writer_debug.writerow(['t','date_diff','new_date_diff','newsleep'])

def init():
    csv_file_init = None
    writer_init = None
    csv_file_debug_init = None
    writer_debug_init = None
    
    
    
    if gLog:
        try:
            csv_file_init, writer_init = loggingFuncInit(0)
        except:
            print("Couldn't init log file")
    
    if gDebug:
        try:
            csv_file_debug_init, writer_debug_init = loggingFuncInit(1)
        except:
            print("Couldn't init debug file")
    
    global csv_file
    csv_file = csv_file_init
    global writer
    writer = writer_init
    global csv_file_debug
    csv_file_debug = csv_file_debug_init
    global writer_debug
    writer_debug = writer_debug_init
    


def gpsResolve():
    return gpsd.get_current()
    
def reverseGeocode(sentGeo):
    #global packet
    while True:
        try:
            #takes a while the first time
            temp = geocode_api.query(packet.lat, packet.lon, reverse=True, zoom=18)
            sentGeo.send(temp)
        except:
            print("GEO: Can't resolve address")


def displayData(pipe):
    if gDisplayData:
        try:
            display = displayInit()
        except:
            print("Couldn't init display")
    
    receivedData, sentData = pipe
    sentData.close() #reading data only
    
    while True:
        try:
            while receivedData.poll(): #this small loop reads only the last item in the pipe (basically skips elements until none are left)
                a_length, packet, road, house = receivedData.recv()
        except:
            print("DISPLAY: No data received")
        
        cur_time=time.time()
        cur_timestamp=time.localtime(cur_time)
        with canvas(display) as draw: #execution time: around 100ms (good!)
            if cur_timestamp.tm_min<10: #clock
                legacy.text(draw, (0, 0), str(cur_timestamp.tm_hour)+":0"+str(cur_timestamp.tm_min), fill="white")
            else:
                legacy.text(draw, (0, 0), str(cur_timestamp.tm_hour)+":"+str(cur_timestamp.tm_min), fill="white")
            
            if gLog:
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
                print("DISPLAY: No address to display")
            #print(reverse_geocode_result.displayName())

def main(receivedGeo, sentData):
    global csv_file
    global csv_file_debug
    global writer
    global writer_debug
    global road
    global house
    init()
    
    while True:
        try:
            cur_time=time.time()
            date_diff=cur_time-start_time #save current loop timestamp in relation to starting time
            
            if date_diff>=gRecording_time and gLog and stop_after_time_passed:
               csv_file.close()
               exit()
            #print("Temp : "+str(mpu.get_temp())) #thermometer module (unused)
            
            #get gps position
            try:
                packet = gpsResolve()
            except:
                print("MAIN: Can't resolve GPS")
            
            #resolve reverse geocoded address
            if gReverseGeocode:
                try:
                    #if receivedGeo.poll(): #if there's data in the geocoding pipe
                        #reverse_geocode_result = receivedGeo.recv()
                    time.sleep(0)
                except:
                    print("MAIN: Can't resolve address")
            
            oldroad=road
            oldhouse=house
            
            #fallback to old address if reverse geocoding failed
            try:
                #legacy.text(draw, (0, d[1]-8), reverse_geocode_result.address()['road']+" "+reverse_geocode_result.address()['house_number'], fill="white", font=legacy.font.TINY_FONT)
                #print(reverse_geocode_result.displayName())
                
                road = reverse_geocode_result.address()['road']
                
                house = reverse_geocode_result.address()['house_number']
                print("MAIN: "+road+" "+house)
            except:
                house = oldhouse
                road = oldroad
                print("MAIN: Old: "+road+" "+house)
            
            #accelerometer data acquisition
            try:
                accel_data = mpu.get_accel_data() 
                ax = accel_data['x']
                ay = accel_data['y']
                az = accel_data['z'] #save accelerometer elements to variables
                
                a_length=math.sqrt(ax**2+ay**2+az**2) #calculate [ax, ay, az] length (slightly faster than numpy)
            except:
                print("MAIN: Can't resolve accelerometer data") #literally never happened
            
            if gLog:
                try:
                    writer.writerow([date_diff, ax, ay, az, a_length, packet.lat, packet.lon, packet.hspeed, road, house])
                except:
                    print("MAIN: Couldn't write to log file")
            
            newsleep=Tp-((time.time()-start_time)-date_diff)
            
            if gDebug:
                try:
                    writer_debug.writerow([time.time(),date_diff,time.time()-start_time,newsleep])
                except:
                    print("MAIN: Couldn't write to debug file")
            
            try:
                sentData.send([a_length, packet, road, house])
            except:
                print("MAIN: Couldn't send data")
            
            if newsleep>0:
                time.sleep(newsleep)
                print('MAIN: something happened')
        
        except KeyboardInterrupt: #this is important. without it, the processes might run indefinitely.
            geocode_process.terminate()
            display_process.terminate()
            main_process.terminate()
            raise SystemExit


if __name__ == "__main__":
    mp.set_start_method('fork')
    receivedData, sentData = mp.Pipe()
    receivedGeo, sentGeo = mp.Pipe()
    main_process = mp.Process(target = main, args=((receivedGeo, sentData),))
    display_process = mp.Process(target = displayData, args=((receivedData, sentData),))
    geocode_process = mp.Process(target = reverseGeocode, args=((sentGeo),))
    
    print("Starting main process.")
    main_process.start()
    
    if gDisplayData:
        print("Starting display process.")
        display_process.start() #works with data exchange - 06.09.21
    
    if gReverseGeocode: #TODO
        print("Starting reverse geocode process.")
        geocode_process.start()