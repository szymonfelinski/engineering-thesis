#!/usr/bin/env python3

gLogGeocode = 1 #will the csv debug file be written?
gLog = 1 #will the csv data file be written? (if 0, the program has no stop condition!)
gDisplayData = 1 #display data on the display?
gReverseGeocode = 1 #attempt to reverse geocode GPS data?
Tp = 0.1 #discrete step time, framerate
displayTp = 0.3 #framerate for the display

gGradingTime = 180 #length of grading window in seconds


screenNumber = 0 #tells which screen is currently shown. 0 is starting screen, 1 is working program, 2 is ending screen
totalScreenNumber = 2 #total number of screens
newDataFlag = 0
wagonType = 0 #choose wagon type
buttonPinLeft = 22
buttonPinMiddle = 27
buttonPinRight = 17
wagonName = {
            0:"Moderus Gamma", 
            1:"Moderus Alfa", 
            2:"Moderus Beta",
            3:"Siemens Combino",
            4:"Konstal 105Na",
            5:"Tatra RT6",
            6:"Solaris Tramino"
            }

display_process = []
main_process = []
d = [128, 64]

import multiprocessing as mp
import signal
import gpsd #GPS library
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
    
#global variables
start_time = time.time() #save date and time of script start (seconds since epoch - UTC)

mpu = mpu6050(0x68) #0x68 is device address on i2c bus

mpu.bus.write_byte_data(0x68, 0x1A, 4) #this enables digital low-pass filter on accelerometer and gyro - added 11.11.21

# Connect to the local gpsd
gpsd.connect() #this takes a while (MUST BE SET UP USING sudo gpsd /dev/serial0 -F /var/run/gpsd.sock !!! #EDIT 06.08.21 - added automatic execution at system startup.)

#DISPLAY
MY_CUSTOM_BITMAP_FONT = [ # Note that "\0" is the zero-th character in the font
    [
        0x00, 0x3e, 0x08, 0x3e, 0x00, 0x3e, 0x2a, 0x22, 
        0x00, 0x3e, 0x20, 0x20, 0x00, 0x3e, 0x0a, 0x0e
    ], #HELP
    [
        0xff	, 0x81	, 0x81	, 0xff
    ], #O
    [
        0x00	, 0x46	, 0x89	, 0x89	, 0x89	, 0x72	, 0x00	, 0xff	, 0x11	, 0x11	, 0x11	, 0x01	, 0x60	, 0x96	, 0xa9	, 0xa6	, 0x40	, 0xa0	, 0x00	, 0xff	, 0x06	, 0x08	, 0x06	, 0xff	, 0x00	, 0xff	, 0x81	, 0x81	, 0x81	, 0x7e
    ]  #SF&MD
    ]
    
class ProcessKill: #this class handles soft termination of processes (i. e. ctrl-c) - added this 22.11.21 and implemented in program. All processes properly terminate now.
    terminate = False
    def __init__(self):
        signal.signal(signal.SIGINT, self.term_process)
        signal.signal(signal.SIGTERM, self.term_process)
    
    def term_process(self,signum, frame):
        self.terminate = True

#init display
def displayInit():
    serial = i2c(port = 1, address = 0x3C) #configure address in i2c bus
    display = sh1106(serial) #binding display to process variable
    return display
#END OF DISPLAY INIT

start_datetime = time.localtime(start_time)

def loggingFuncInit(geocoding):
    #this is the main data file
    start_datetime = time.localtime(time.time())
    file_name = '/home/dobrej/Saved_data/data' + str(start_datetime.tm_year) + '-' + str(start_datetime.tm_mon) + '-' + str(start_datetime.tm_mday) + '-' + str(start_datetime.tm_hour) + '-' + str(start_datetime.tm_min) + '-' + str(start_datetime.tm_sec)
    if geocoding:
        file_name = file_name + '_geocode'
    file_name = file_name + '.csv'
    csv_init = open(file_name, 'w+', encoding = 'UTF8', newline = '')
    writer_init = csv.writer(csv_init, delimiter = ';')
    if geocoding:
        writer_init.writerow(['unix time', 'road', 'house', 'latitude', 'longitude', 'hspeed']) #changed to geocoding file 04.11.21 - added packet data 08.11.21
    else:
        writer_init.writerow(['set time', 'actual time', 'ax', 'ay', 'az', 'day', 'daz', 'dyAvg', 'dzAvg', 'grade', 'gy', 'gz', 'latitude', 'longitude', 'hspeed']) #csv headers - removed road and street - 06.09.21 - added unix time - 04.11.21
    return file_name, csv_init, writer_init

def GPSResolve():
    return gpsd.get_current()
    
def GPSFunc(sentGPS):
    killer = ProcessKill()
    
    while not killer.terminate: 
        try:
            packet = GPSResolve()
            sentGPS.send(packet)
            time.sleep(0.5) #give GPS 500ms of delay after successful data read
        except KeyboardInterrupt:
            pass
        except:
            print("GPS: Can't resolve GPS data")
    
def reverseGeocode(sentGeo):
    killer = ProcessKill()
    while not killer.terminate:
        try:
            packet = GPSResolve() #this works better than sending a packet from display.
            geocodingResult = geocode_api.query(packet.lat, packet.lon, reverse = True, zoom = 18) #takes a while the first time
            if geocodingResult.isReverse(): #if the response is actual reverse geocode data
                sentGeo.send(geocodingResult) #send data to pipe
                #print("GEOCODE: Address found.")
                #print(geocodingResult.address())
            time.sleep(5) #limit the number of calls to API to 0.2 per second - possible cause of CPU hangs if not limited.
        except KeyboardInterrupt: #this is important. without it, the display process would run indefinitely.
            pass
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
    s = returnTypeOfWagon(wagonType)
    print("s: ", s)

    
def button_2_pressed(self):         #change screen if button is pressed
    global newDataFlag
    newDataFlag = 1
    print("right button pressed: new travel")
    
def changeScreenNumber():
    global screenNumber
    if screenNumber < totalScreenNumber:
        screenNumber += 1
    else:
        screenNumber = 0

def returnTypeOfWagon(wagonNumber):     #added 14.09.2021
    return wagonName.get(wagonNumber, "Invalid type")

def displayData(receivedData):
    if gReverseGeocode: 
        receivedGeo, sentGeo = mp.Pipe()
        geocode_process = mp.Process(target = reverseGeocode, args = ((sentGeo), ), name = "Geocode process") #added 08.09.21
        print("DISPLAY: Starting reverse geocode process.")
        geocode_process.start()
        
    global screenNumber
    global wagonType
    global newDataFlag
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
            file_name_geo_, csvFileGeo, writerGeo = loggingFuncInit(1)
        except:
            print("Couldn't init debug file")
    
    killer = ProcessKill()
    
    displayNextTime = start_time + displayTp
    
    while not killer.terminate: 
        try:
            if time.time() >= displayNextTime:
                
                cur_time = time.time()
                cur_timestamp = time.localtime(cur_time)
                
                try:
                    while receivedData.poll(): #this small loop reads only the last item in the pipe (basically skips elements until none are left)
                        [accData, derivAccData, grade, GPSDistance, packet] = receivedData.recv()
                except KeyboardInterrupt: #this is important. without it, the display process would run indefinitely.
                    pass
                except:
                    print("DISPLAY: No data received")
                
                #resolve reverse geocoded address
                try:
                    while receivedGeo.poll(): #only pull the latest result
                        reverse_geocode_result = receivedGeo.recv()
                except:
                    print("DISPLAY: Can't resolve geocode address")
                
                oldroad = road
                oldhouse = house
                
                try:
                    road = reverse_geocode_result.address()['road']

                except: #fallback to old address if reverse geocoding failed (and quarter handling - 10.09.21)
                    try:
                        road = reverse_geocode_result.address()['quarter'] #this is needed in case it's "osiedle" and not "ulica".
                    except: 
                        road = oldroad
                    
                try:                
                    house = reverse_geocode_result.address()['house_number']
                except: #fallback to old address if reverse geocoding failed
                    house = oldhouse
                
                if newDataFlag and gLogGeocode: #added 11.11.21
                    try:
                        csvFileGeo.close()
                        file_name_geo_, csvFileGeo, writerGeo = loggingFuncInit(1)
                        csvFileGeo.flush()
                        newDataFlag = 0
                    except:
                        print("DISPLAY: Couldn't write to debug file")
                
                currentWagon = returnTypeOfWagon(wagonType)
                
                if gLogGeocode: #changed function from cycle time debugging to reverse geocode logging - 04.11.21
                    try:
                        writerGeo.writerow([cur_time, road, house, packet.lat, packet.lon, packet.hspeed, currentWagon])
                        csvFileGeo.flush()
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
                            legacy.text(draw, (d[0]-len(s)*8, 0), "\2", fill = "white", font = MY_CUSTOM_BITMAP_FONT) #watermark
                        except:
                            pass
                        
                        try:
                            legacy.text(draw, (0, 15), "Rodzaj: ", fill = "white", font = legacy.font.SINCLAIR_FONT) #Wagon type
                            legacy.text(draw, (0, 24), currentWagon, fill = "white", font = legacy.font.SINCLAIR_FONT) #Wagon type
                            legacy.text(draw, (0, 64-12), "Distance: " + str(GPSDistance), fill = "white", font = legacy.font.TINY_FONT)
                            legacy.text(draw, (0, 64-6), "Grade: " + str(grade), fill = "white", font = legacy.font.TINY_FONT)
                        except:
                            pass
                elif screenNumber == 1:
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
                            legacy.text(draw, (d[0]-len(s)*8, 0), "\2", fill = "white", font = MY_CUSTOM_BITMAP_FONT) #watermark
                        except:
                            pass
                        
                        try:
                            legacy.text(draw, (0, 8), "x: " + str(round(accData['x'], 2)), fill = "white", font = legacy.font.TINY_FONT)
                            legacy.text(draw, (40, 8), "y: " + str(round(accData['y'], 2)), fill = "white", font = legacy.font.TINY_FONT)
                            legacy.text(draw, (80, 8), "z: " + str(round(accData['z'], 2)), fill = "white", font = legacy.font.TINY_FONT)
                            legacy.text(draw, (0, 14), "x: " + str(round(derivAccData[0], 2)), fill = "white", font = legacy.font.TINY_FONT)
                            legacy.text(draw, (40, 14), "y: " + str(round(derivAccData[1], 2)), fill = "white", font = legacy.font.TINY_FONT)
                            legacy.text(draw, (80, 14), "z: " + str(round(derivAccData[2], 2)), fill = "white", font = legacy.font.TINY_FONT)
                            legacy.text(draw, (0, 20), "Lat: " + str(packet.lat), fill = "white", font = legacy.font.TINY_FONT)
                            legacy.text(draw, (0, 26), "Lon: " + str(packet.lon), fill = "white", font = legacy.font.TINY_FONT)
                            legacy.text(draw, (0, 32), "Distance: " + str(GPSDistance), fill = "white", font = legacy.font.TINY_FONT)
                            legacy.text(draw, (0, 38), "Grade: " + str(grade), fill = "white", font = legacy.font.TINY_FONT)
                        except:
                            pass
                        
                        try: #speed as reported by GPS
                            legacy.text(draw, (0, d[1]-14), "Speed: " + str(round(packet.hspeed*3.6,1)) + " km/h", fill = "white", font = legacy.font.SINCLAIR_FONT)
                        except:
                            legacy.text(draw, (0, d[1]-14), "Speed: unknown", fill = "white", font = legacy.font.SINCLAIR_FONT)
                        
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
                            legacy.text(draw, (d[0] - len(s) * 8, 0), "\2", fill = "white", font = MY_CUSTOM_BITMAP_FONT) #watermark
                        except:
                            pass
                        try:
                            legacy.text(draw, (0, 15), "Koniec programu ", fill = "white", font = legacy.font.SINCLAIR_FONT) #Wagon type
                        except:
                            pass
                
                displayNextTime += displayTp
            else:
                time.sleep(0.005)
        except KeyboardInterrupt:
            pass
    if killer.terminate:
        geocode_process.terminate()
        exit()

def move_data_by_one(data):
    
    for i in range(10):
        if i > 0:
            data[i-1] = data[i]
    return data
    
def average_data(data):
    avg = 0.0
    for i in range(10):
        avg += data[i]
    return avg / 10

def calcDeriv(data1, data2):
    derivative = [data1['x'] - data2['x'], data1['y'] - data2['y'], data1['z'] - data2['z']]
    return derivative

def processingData(sentData):
    
    global newDataFlag
    
    gpio.setmode(gpio.BCM)
    gpio.setup(22, gpio.IN, pull_up_down = gpio.PUD_DOWN)
    gpio.add_event_detect(22, gpio.RISING, callback = button_2_pressed, bouncetime = 300)
    
    newDataFlag = True
    
    #GPS process
    receivedGPS, sentGPS = mp.Pipe()
    GPSProcess = mp.Process(target = GPSFunc, args = ((sentGPS), ), name = "Main GPS process")
    GPSProcess.start()
    
    data_table = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    nextTime = start_time + Tp
    
    accelData = mpu.get_accel_data() 
    gyroData = mpu.get_gyro_data()
    
    killer = ProcessKill()
    
    csv_file = 0
    
    while not killer.terminate:
        #curTime = time.time()
        try:
            if newDataFlag and gLog: #added 11.11.21, changed 29.11.21
                try:
                    #grading algorithm variables
                    derivAccelData = calcDeriv(accelData, accelData)
                    numberOfPoints = 0
                    numberOfPointsdz = 0
                    numberOfPointsdy = 0
                    grade = 0
                    gradeSum = 0
                    dySum = 0
                    dzSum = 0
                    dyAvg = 0
                    dzAvg = 0
                    GPSDistance = 0
                    
                    data_counter = 0
                    if csv_file:
                        csv_file.close()
                    
                    file_name, csv_file, writer = loggingFuncInit(0) #changed to new file every new data - 29.11.21
                    newDataFlag = False
                except:
                    print("MAIN: Couldn't create new log file")
            
            if time.time() >= nextTime:
                date_diff = nextTime - start_time #save current loop timestamp in relation to starting time
                
                if data_counter >= 120: #this ensures that data are written to file every 120th cycle - 09.11.21
                    csv_file.close()
                    csv_file = open(file_name, 'a', encoding = 'UTF8', newline = '')
                    writer = csv.writer(csv_file, delimiter = ';')
                    data_counter = 0
                
                #print("Temp : " + str(mpu.get_temp())) #thermometer module (unused)
                
                try: #added 25.11.2021
                    while receivedGPS.poll(): #this small loop reads only the last item in the GPS pipe (basically skips elements until none are left)
                        packet = receivedGPS.recv()
                except:
                    print("MAIN: Can't resolve GPS data from pipe.")
                
                #accelerometer data acquisition
                try:
                    accelDataOld = accelData
                    gyroDataOld = gyroData
                    
                    accelData = mpu.get_accel_data() #save IMU data to variables
                    gyroData = mpu.get_gyro_data()
                    
                    derivAccelData = calcDeriv(accelData, accelDataOld)
                    
                except:
                    print("MAIN: Can't resolve accelerometer data") #literally never happened
                
                try:
                    GPSDistance += packet.hspeed #crude speed integration
                    
                    if packet.hspeed > 2.5 and math.fabs(derivAccelData[2]) > 0.01:
                        numberOfPoints += 1
                        numberOfPointsdz += 1
                        gradeSum += math.fabs(derivAccelData[2])
                        dzSum += math.fabs(derivAccelData[2])
                        dzAvg = dzSum / numberOfPointsdz
                    
                    if packet.hspeed > 0.1 and math.fabs(derivAccelData[1]) > 0.01:
                        numberOfPoints += 1
                        numberOfPointsdy += 1
                        gradeSum += math.fabs(derivAccelData[1])
                        dySum += math.fabs(derivAccelData[1])
                        dyAvg = dySum / numberOfPointsdy
                    
                    if numberOfPoints > 0:
                        grade = gradeSum / numberOfPoints
                    
                except:
                    print("MAIN: Algorithm problem")
                
                if gLog:
                    try:
                        writer.writerow([nextTime, time.time(), accelData['x'], accelData['y'], accelData['z'], derivAccelData[1], derivAccelData[2], dyAvg, dzAvg, grade, GPSDistance, gyroData['z'], packet.lat, packet.lon, packet.hspeed])
                    except:
                        print("MAIN: Couldn't write to log file")
                
                try:
                    sentData.send([accelData, derivAccelData, grade, GPSDistance, packet])
                except KeyboardInterrupt: #this is important. without it, the processes would run indefinitely.
                    raise SystemExit
                except:
                    print("MAIN: Couldn't send data to display")
                
                data_counter += 1
                
                nextTime += Tp
            else:
                time.sleep(0.005)
        except KeyboardInterrupt:
            pass
    
    GPSProcess.terminate()

if __name__ == "__main__":
    #init()
    mp.set_start_method('fork')
    receivedData, sentData = mp.Pipe()
    main_process = mp.Process(target = processingData, args = ((sentData), ), name = "Main process")
    display_process = mp.Process(target = displayData, args = ((receivedData), ), name = "Display process")
    #it needs to be in its own process - sometimes hangs the display.
    print("Starting main process.")
    main_process.start()
    
    if gDisplayData:
        print("Starting display process.")
        display_process.start()
        
    #exit()
     
    killer = ProcessKill()
    
    while not killer.terminate: 
        try:
            time.sleep(1)
        except KeyboardInterrupt: #this is important. without it, the display process would run indefinitely.
            display_process.terminate()
            main_process.terminate()
            raise SystemExit
