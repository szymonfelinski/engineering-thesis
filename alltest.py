#!/usr/bin/env python3

gLogGeocode = 1 #will the csv debug file be written?
gLog = 1 #will the csv data file be written? (if 0, the program has no stop condition!)
gDisplayData = 1 #display data on the display?
gReverseGeocode = 1 #attempt to reverse geocode GPS data?
gVerbose = 1 #verbose output in console? (does nothing atm - 06.09.21)
stop_after_time_passed = 0 #will the program stop after the amount of time set in recording_time?
gRecording_time = 1800 #time of recording in seconds
Tp = 0.1 #discrete step time, framerate
warning_threshold = 12 #acceleration at which a message will appear

screenNumber = 0 #tells which screen is currently showed. 0 is starting screen, 1 is working program, 2 is ending screen
totalScreenNumber = 2 #total number of screens
wagonType = 0 #choose wagon type
buttonPinLeft = 22
buttonPinMiddle = 27
buttonPinRight = 17
wagonName = {
            0:"Gamma", 
            1:"Beta", 
            2:"Omega"
            }

geocode_process = []
display_process = []
main_process = []
d = [128, 64]

import multiprocessing as mp

import gpsd #gps library
import time
from mpu6050 import mpu6050 #imu library
import math
import time
import csv
from traceback_with_variables import activate_by_import
import RPi.GPIO as gpio #library that control pins

if gDisplayData:
    #display libraries
    from luma.core.render import canvas
    from luma.core import legacy
    from luma.oled.device import sh1106
    from luma.core.interface.serial import i2c

if gReverseGeocode:
    from OSMPythonTools.nominatim import Nominatim #maps library (reverse geocoding)
    import logging
    logging.getLogger('OSMPythonTools').setLevel(logging.ERROR) #https://github.com/mocnik-science/osm-python-tools#logging #suppressing the output of Nominatim.
    geocode_api = Nominatim() #binding reverse geocoding to a process variable
    #reverse_geocode_result = geocode_api.query(40.714224, -73.961452, reverse = True)
    #print(reverse_geocode_result.displayName())
    
#global variables
start_time = time.time() #save date and time of script start (seconds since epoch - UTC)

# Connect to the local gpsd
gpsd.connect() #this takes a while (MUST BE SET UP USING sudo gpsd /dev/serial0 -F /var/run/gpsd.sock !!! #EDIT 06.08.21 - added automatic execution at system startup.)

#DISPLAY
MY_CUSTOM_BITMAP_FONT = [ # Note that "\0" is the zero-th character in the font
    [
        0x00, 0x3e, 0x08, 0x3e, 0x00, 0x3e, 0x2a, 0x22, 
        0x00, 0x3e, 0x20, 0x20, 0x00, 0x3e, 0x0a, 0x0e
    ], #HELP
    [
        0x00	, 0x32	, 0x2a	, 0x26	, 0x00	, 0x3e	, 0x22	, 0x3e	, 0x00	, 0x26	, 0x2a	, 0x32	, 0x00	, 0x3e	, 0x00	, 0x3c	, 0x12	, 0x3c

    ], #ZOSIA
    [
        0xff	, 0x81	, 0x81	, 0xff
    ], #O
    [
        0x00	, 0x46	, 0x89	, 0x89	, 0x89	, 0x72	, 0x00	, 0xff	, 0x11	, 0x11	, 0x11	, 0x01	, 0x60	, 0x96	, 0xa9	, 0xa6	, 0x40	, 0xa0	, 0x00	, 0xff	, 0x06	, 0x08	, 0x06	, 0xff	, 0x00	, 0xff	, 0x81	, 0x81	, 0x81	, 0x7e
    ]#SF&MD
    ]
    
#init display
def displayInit():
    serial = i2c(port = 1, address = 0x3C) #configure address in i2c bus
    display = sh1106(serial) #binding display to process variable
    #d = [128, 64] #screen size in pixels
    return display
#END OF DISPLAY INIT

start_datetime = time.localtime(start_time)

def loggingFuncInit(geocoding):
    #this is the main data file
    file_name = '/home/dobrej/Saved_data/data' + str(start_datetime.tm_year) + '-' + str(start_datetime.tm_mon) + '-' + str(start_datetime.tm_mday) + '-' + str(start_datetime.tm_hour) + '-' + str(start_datetime.tm_min) + '-' + str(start_datetime.tm_sec)
    if geocoding:
        file_name = file_name + '_geocode'
    file_name = file_name + '.csv'
    csv_init = open(file_name, 'w+', encoding = 'UTF8', newline = '')
    writer_init = csv.writer(csv_init, delimiter = ';')
    if geocoding:
        writer_init.writerow(['unix time', 'road', 'house', 'latitude', 'longitude', 'hspeed']) #changed to geocoding file 04.11.21 - added packet data 08.11.21
    else:
        writer_init.writerow(['unix time', 'dt', 'ax', 'ay', 'az', 'a_length', 'latitude', 'longitude', 'speed']) #csv headers - removed road and street - 06.09.21 - added unix time - 04.11.21
    return csv_init, writer_init

#def debugFuncInit(): #old debug file init - removed 08.08.2021
#    #this file is used for debugging purposes
#    csv_file_geo = open('Saved_data/data' + str(start_datetime.tm_year) + '-' + str(start_datetime.tm_mon) + '-' + str(start_datetime.tm_mday) + '-' + str(start_datetime.tm_hour) + '-' + str(start_datetime.tm_min) + '-' + str(start_datetime.tm_sec) + 'debug.csv', 'w + ', encoding = 'UTF8', newline = '')
#    writer_geo = csv.writer(csv_file_geo, delimiter = ';')
#    writer_geo.writerow(['t', 'date_diff', 'new_date_diff', 'newsleep'])

#def init():
#    csv_file_init = None
#    writer_init = None
#    csv_file_geo_init = None
#    writer_geo_init = None
#    
#    if gLog:
#        try:
#            csv_file_init, writer_init = loggingFuncInit(0)
#        except:
#            print("Couldn't init log file")
#    
#    if gLogGeocode:
#        try:
#            csv_file_geo_init, writer_geo_init = loggingFuncInit(1)
#        except:
#            print("Couldn't init debug file")
#    
#    global csv_file
#    csv_file = csv_file_init
#    global writer
#    writer = writer_init
#    #04.11 - changed from 'debug' to 'geo'
#    global csv_file_geo
#    csv_file_geo = csv_file_geo_init
#    global writer_geo
#    writer_geo = writer_geo_init
##05.11 - removed this function.

def gpsResolve():
    return gpsd.get_current()
    
def reverseGeocode(sentGeo):
    while True:
        try:
            packet = gpsResolve() #this works better than sending a packet from display.
            geocodingResult = geocode_api.query(packet.lat, packet.lon, reverse = True, zoom = 18) #takes a while the first time
            if geocodingResult.isReverse(): #if the response is actual reverse geocode data
                sentGeo.send(geocodingResult) #send data to pipe
                print("GEOCODE: Address found.")
                #print(geocodingResult.address())
            time.sleep(5) #limit the number of calls to API - possible cause of CPU hangs if not limited.
        except KeyboardInterrupt: #this is important. without it, the display process would run indefinitely.
            raise SystemExit
        except:
            print("GEOCODE: Can't resolve address")
            
def button_0_pressed(self):         #change screen if button is pressed
    global screenNumber
    print("screen number before change: ", screenNumber)
    changeScreenNumber()
    print("screen number after change: ", screenNumber)
    
def button_1_pressed(self):         #change screen if button is pressed
    global wagonType
    if wagonType < len(wagonName) - 1:
        wagonType += 1
    else:
        wagonType = 0
    print("middle button pressed: ")
    s = returnTypeOfWagon(0)
    print("s: ", s)

    
def button_2_pressed(self):         #change screen if button is pressed
    global wagonType
    if wagonType > 0:
        wagonType -= 1
    else: 
        wagonType = len(wagonName) - 1
    print("left button pressed: ")
    
def changeScreenNumber():
    global screenNumber
    if screenNumber < totalScreenNumber:
        screenNumber += 1
    else:
        screenNumber = 0

def returnTypeOfWagon(wagonNumber):     #added 14.09.2021
    return wagonName.get(wagonNumber, "Invalid type")

def displayData(receivedData):
    #global road
    #global house
    
    if gReverseGeocode: 
        receivedGeo, sentGeo = mp.Pipe()
        geocode_process = mp.Process(target = reverseGeocode, args = ((sentGeo), )) #added 08.09.21
        print("DISPLAY: Starting reverse geocode process.")
        geocode_process.start()
        
    global screenNumber
    global wagonType
    gpio.setmode(gpio.BCM)
    gpio.setup(17, gpio.IN, pull_up_down = gpio.PUD_DOWN)
    gpio.setup(27, gpio.IN, pull_up_down = gpio.PUD_DOWN)
    gpio.setup(22, gpio.IN, pull_up_down = gpio.PUD_DOWN)
    gpio.add_event_detect(17, gpio.RISING, callback = button_0_pressed, bouncetime = 300)
    gpio.add_event_detect(27, gpio.RISING, callback = button_1_pressed, bouncetime = 300)
    gpio.add_event_detect(22, gpio.RISING, callback = button_2_pressed, bouncetime = 300)
    
    road = "unresolved"
    house = "unresolved"
    
    if gDisplayData:
        try:
            display = displayInit()
        except:
            print("DISPLAY: Couldn't init display")    
    
    if gLogGeocode: #this replaces init() as of 05.11.21
        try:
            csv_file_geo, writer_geo = loggingFuncInit(1)
        except:
            print("Couldn't init debug file")
    
    while True: 
        #print("screen number in loop: ", screenNumber)
        cur_time = time.time()
        cur_timestamp = time.localtime(cur_time)
        
        #resolve reverse geocoded address
        if gReverseGeocode:
            try:
                while receivedGeo.poll(): #only pull the latest result
                    reverse_geocode_result = receivedGeo.recv()
                    
                #print(reverse_geocode_result.address())
            except:
                print("DISPLAY: Can't resolve address")
    
        oldroad = road
        oldhouse = house
        
        packet = gpsResolve()
        
        try:
            road = reverse_geocode_result.address()['road']
        except: #fallback to old address if reverse geocoding failed (and quarter handling - 10.09.21)
            try:
                road = reverse_geocode_result.address()['quarter'] #this is needed in case it's "osiedle" and not "ulica".
            except: 
                road = oldroad
            #print("DISPLAY: Old: " + road + " " + house)
            
        try:                
            house = reverse_geocode_result.address()['house_number']
        except: #fallback to old address if reverse geocoding failed
            house = oldhouse
        
        #print("DISPLAY: " + road + " " + house)
        
        if gLogGeocode: #changed function from cycle time debugging to reverse geocode logging - 04.11.21
            try:
                writer_geo.writerow([cur_time, road, house, packet.lat, packet.lon, packet.hspeed])
                csv_file_geo.flush()
            except:
                print("DISPLAY: Couldn't write to debug file")
        
        if screenNumber == 0:
            with canvas(display) as draw: #execution time: around 100ms
                if cur_timestamp.tm_sec%2:
                    if cur_timestamp.tm_min<10: #clock
                        legacy.text(draw, (0, 0), str(cur_timestamp.tm_hour) + ":0" + str(cur_timestamp.tm_min), fill = "white")
                    else:
                        legacy.text(draw, (0, 0), str(cur_timestamp.tm_hour) + ":" + str(cur_timestamp.tm_min), fill = "white")
                else:
                    if cur_timestamp.tm_min<10: #clock
                        legacy.text(draw, (0, 0), str(cur_timestamp.tm_hour) + " 0" + str(cur_timestamp.tm_min), fill = "white")
                    else:
                        legacy.text(draw, (0, 0), str(cur_timestamp.tm_hour) + " " + str(cur_timestamp.tm_min), fill = "white")
                try:
                    s = "SF&MD"
                    legacy.text(draw, (d[0]-len(s)*8, 0), "\3", fill = "white", font = MY_CUSTOM_BITMAP_FONT) #watermark
                except:
                    time.sleep(0)
                try:
                    z = returnTypeOfWagon(wagonType)
                    #print("s: ", z)
                    legacy.text(draw, (0, 15), "Rodzaj: " + z, fill = "white", font = legacy.font.SINCLAIR_FONT) #Wagon type
                except:
                    time.sleep(0)
        elif screenNumber == 1:
            try:
                while receivedData.poll(): #this small loop reads only the last item in the pipe (basically skips elements until none are left)
                    #a_length, packet, cycle = receivedData.recv()
                    a_length, cycle = receivedData.recv()
            except KeyboardInterrupt: #this is important. without it, the display process would run indefinitely.
                if gReverseGeocode:
                    geocode_process.terminate()
                raise SystemExit
            except:
                print("DISPLAY: No data received")
            
            with canvas(display) as draw: #execution time: around 100ms (good!) #do tego momentu nic nie ruszaj ok?
                if cur_timestamp.tm_sec%2:
                    if cur_timestamp.tm_min < 10: #clock
                        legacy.text(draw, (0, 0), str(cur_timestamp.tm_hour) + ":0" + str(cur_timestamp.tm_min), fill = "white")
                    else:
                        legacy.text(draw, (0, 0), str(cur_timestamp.tm_hour) + ":" + str(cur_timestamp.tm_min), fill = "white")
                else:
                    if cur_timestamp.tm_min < 10: #clock
                        legacy.text(draw, (0, 0), str(cur_timestamp.tm_hour) + " 0" + str(cur_timestamp.tm_min), fill = "white")
                    else:
                        legacy.text(draw, (0, 0), str(cur_timestamp.tm_hour) + " " + str(cur_timestamp.tm_min), fill = "white")
                
                if gLog:
                    try:
                        s = "logging"
                        legacy.text(draw, (d[0]/2-len(s)*5/2, 0), s, fill = "white", font = legacy.font.TINY_FONT)
                    except:
                        legacy.text(draw, (d[0]/2, 0), " ", fill = "white", font = legacy.font.TINY_FONT)
                
                try:
                    s = "SF&MD"
                    legacy.text(draw, (d[0]-len(s)*8, 0), "\3", fill = "white", font = MY_CUSTOM_BITMAP_FONT) #watermark
                except:
                    time.sleep(0)
                
                try:
                    legacy.text(draw, (0, 8), "telepanie: " + str(round(a_length, 2)), fill = "white", font = legacy.font.SINCLAIR_FONT)
                except:
                    time.sleep(0)
                
                try:
                    legacy.text(draw, (0, 15), "Lat: " + str(packet.lat), fill = "white", font = legacy.font.TINY_FONT)
                    legacy.text(draw, (0, 21), "Lon: " + str(packet.lon), fill = "white", font = legacy.font.TINY_FONT)
                    legacy.text(draw, (0, 27), "Cycle: " + str(cycle), fill = "white", font = legacy.font.TINY_FONT)
                except:
                    time.sleep(0)
                
                try:
                    if a_length > warning_threshold:
                        s = "ZWOLNIJ"
                        legacy.text(draw, (d[0]/2-len(s)*8/2, d[1]/2), s, fill = "white")
                except:
                    legacy.text(draw, (d[0]/2, d[1]/2), " ", fill = "white")
                
                try: #gps satellite count
                    legacy.text(draw, (0, d[1]-22), "Sats: " + str(packet.sats), fill = "white", font = legacy.font.SINCLAIR_FONT)
                except:
                    legacy.text(draw, (0, d[1]-22), " ", fill = "white", font = legacy.font.SINCLAIR_FONT)
                
                try: #speed as reported by gps
                    legacy.text(draw, (0, d[1]-14), "Speed: " + str(packet.hspeed) + " m/s", fill = "white", font = legacy.font.SINCLAIR_FONT)
                except:
                    legacy.text(draw, (0, d[1]-14), "Speed: unknown", fill = "white", font = legacy.font.SINCLAIR_FONT)
                #print(reverse_geocode_result.displayName())
                if gReverseGeocode:
                    try: #address display
                        legacy.text(draw, (0, d[1]-6), road + " " + house, fill = "white", font = legacy.font.TINY_FONT) #renders address on the bottom of display (TINY_FONT is 5x3 pixels).
                    except:
                        legacy.text(draw, (0, d[1]-6), "unknown address", fill = "white", font = legacy.font.TINY_FONT)
                        print("DISPLAY: No address to display") 
        elif screenNumber == 2:
            with canvas(display) as draw: #execution time: around 100ms
                if cur_timestamp.tm_sec%2:
                    if cur_timestamp.tm_min<10: #clock
                        legacy.text(draw, (0, 0), str(cur_timestamp.tm_hour) + ":0" + str(cur_timestamp.tm_min), fill = "white")
                    else:
                        legacy.text(draw, (0, 0), str(cur_timestamp.tm_hour) + ":" + str(cur_timestamp.tm_min), fill = "white")
                else:
                    if cur_timestamp.tm_min < 10: #clock
                        legacy.text(draw, (0, 0), str(cur_timestamp.tm_hour) + " 0" + str(cur_timestamp.tm_min), fill = "white")
                    else:
                        legacy.text(draw, (0, 0), str(cur_timestamp.tm_hour) + " " + str(cur_timestamp.tm_min), fill = "white")
                try:
                    s = "SF&MD"
                    legacy.text(draw, (d[0] - len(s) * 8, 0), "\3", fill = "white", font = MY_CUSTOM_BITMAP_FONT) #watermark
                except:
                    time.sleep(0)
                try:
                    legacy.text(draw, (0, 15), "Koniec programu ", fill = "white", font = legacy.font.SINCLAIR_FONT) #Wagon type
                except:
                    time.sleep(0)
        time.sleep(0.1)

def processingData(sentData):
    
    mpu = mpu6050(0x68) #0x68 is device address on i2c bus
    
    #global reverse_geocode_result
    #init() - moved to beginning of program as of 04.11.21
    if gLog: #this replaces init() as of 05.11.21
        try:
            csv_file, writer = loggingFuncInit(0)
        except:
            print("Couldn't init log file")
    
    slowDown = False
    prevDateDiff = 0
    while True:
        cur_time = time.time()
        date_diff = cur_time - start_time #save current loop timestamp in relation to starting time
        
        if date_diff >= gRecording_time and gLog and stop_after_time_passed:
           csv_file.close()
           exit()
        #print("Temp : " + str(mpu.get_temp())) #thermometer module (unused)
        
        #get gps position #commented out 08.11.21
        #try:
        #    packet = gpsResolve()
        #except:
        #    print("MAIN: Can't resolve GPS")
        
        #moved road and house to displaydata - 06.09.21
        
        #accelerometer data acquisition
        try:
            accel_data = mpu.get_accel_data() 
            ax = accel_data['x']
            ay = accel_data['y']
            az = accel_data['z'] #save accelerometer elements to variables
            
            a_length = math.sqrt(ax**2 + ay**2 + az**2) #calculate [ax, ay, az] length (slightly faster than numpy)
            #if a_length>13:
            #    slowDown = True
            #    timeSlowDown = cur_time
            #elif a_length and (cur_time-timeSlowDown > 1.0):
            #    slowDown = False
        except:
            print("MAIN: Can't resolve accelerometer data") #literally never happened
        
        if gLog:
            try:
                #writer.writerow([cur_time, date_diff - prevDateDiff, ax, ay, az, a_length, packet.lat, packet.lon, packet.hspeed])
                writer.writerow([cur_time, date_diff - prevDateDiff, ax, ay, az, a_length, 'removed', 'removed', 'removed'])
                csv_file.flush()
                prevDateDiff = date_diff
            except:
                print("MAIN: Couldn't write to log file")
        
        cycle = (time.time() - start_time) - date_diff #this calculates current cycle length
        
        #if gLogGeocode: #changed function from cycle time debugging to reverse geocode logging - 04.11.21
        #    try:
        #        writer_geo.writerow([time.time(), date_diff, time.time()-start_time, newsleep])
        #    except:
        #        print("MAIN: Couldn't write to debug file")
        
        try:
            #sentData.send([a_length, packet, cycle])
            sentData.send([a_length, cycle])
        except KeyboardInterrupt: #this is important. without it, the processes would run indefinitely.
            raise SystemExit
        except:
            print("MAIN: Couldn't send data to display")
        
        if cycle < Tp:
            time.sleep(Tp - cycle) #approximately allow for regular cycle times (alike RTC system)
        else:
            print('MAIN: Cycle time too long.')
            


if __name__ == "__main__":
    #init()
    mp.set_start_method('fork')
    receivedData, sentData = mp.Pipe()
    main_process = mp.Process(target = processingData, args = ((sentData), ))
    display_process = mp.Process(target = displayData, args = ((receivedData), ))
    #geocode_process = mp.Process(target = reverseGeocode) #instead calling the function in displayData. - 06.09.21
    #it needs to be in its own process - sometimes hangs the display.
    print("Starting main process.")
    main_process.start()
    
    if gDisplayData:
        print("Starting display process.")
        display_process.start()
     
#    while True:
#        try:
#            time.sleep(0)
#        except KeyboardInterrupt: #this is important. without it, the display process would run indefinitely.
#            display_process.terminate()
#            main_process.terminate()
#            raise SystemExit
