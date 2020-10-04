#!/bin/bash/python3
# -*- coding: utf-8 -*-
from os import mkdir
from datetime import datetime
now = datetime.now()
dt_string = now.strftime("%d%m%Y%H%M%S")
foldername = "data_" + dt_string
mkdir(foldername)
import numpy
import json
import pprint
import time
import serial
import re

###########################################################
# SETUP

omz_addr = 'COM3'
omz_br   = 115200
wait_for_response = 0.5
omz_timeout = 2
# boolean
indicate_status = False
testing = True
awgfreq = 100 # Hz
oscfreq = 2000 # S/sec
sample_size = 30000 # limit
waitInterval = 10 # sec
maxacqCount = 3 # no. of files

pp = pprint.PrettyPrinter(indent=4)
omz = serial.Serial(omz_addr, omz_br, timeout = omz_timeout)


#################################################
# definitions
def runjson(payload):
    if not omz.is_open:
        omz.open()
    # flush ?
    omz.write(json.dumps(payload).encode())
    time.sleep(wait_for_response)
    replystr = b''
    while(omz.in_waiting > 0):
        replystr += omz.read()
    omz.close()
    replystr = replystr[replystr.find(b'{'):replystr.rfind(b'}')+1]
    # print(replystr)
    return json.loads(replystr.decode())
    
runjson(
    {
        "mode":"JSON"
    }
)

runjson(
    {
        "device":[
            {
                "command":"resetInstruments"
            }
        ]
    }
)

def printstatus(status_str):
    #if indicate_status:
        # write status_str to status_broadcast_addr
    print(status_str)

def interrupt():
    exit()

def oscread(acqCount):
    # write command
    payload = {'osc': {'1': [{'command': 'read', 'acqCount': acqCount}]}}
    if not omz.is_open:
        omz.open()
    omz.write(json.dumps(payload).encode())
    time.sleep(wait_for_response)
    # read reply
    replystr = b''
    while(omz.in_waiting > 0):
        replystr += omz.read()
    omz.close()
    result = re.split(b'\r\n',replystr)

    # convert single quotes to double quotes for valid JSON
    str_json = result[1].decode('ASCII').replace("'", '"')
    my_json = json.loads(str_json)

    # data's in the 3rd chunk apparently
    data = result[3]

    # write binary file and convert later
    acqCount = my_json['osc']['1'][0]['acqCount']
    sampleFreq = my_json['osc']['1'][0]['actualSampleFreq']/1000
    filename = "AC" + str(acqCount) + "SR" + str(sampleFreq)
    with open(foldername + "/" + filename + ".bin", "wb") as file:
        for byte in data:
            file.write(byte.to_bytes(1, byteorder='big'))
    mvolts=numpy.zeros(len(data)//2)
    for i in range(0, len(data)-2, 2):
        mvolts[i//2] = int.from_bytes(data[i:i+2], byteorder='little', signed=True)

    volts = mvolts / 1000
    t = numpy.arange(len(volts)) / sampleFreq

    if(len(t)==0):
        print("empty")
    else:
        a = numpy.asarray([ t, volts ])
        numpy.savetxt(foldername + "/" + filename +'.csv', a, delimiter=",")

def check():
    reply = runjson(
        {
            "awg": {
                "1": [
                    {
                        "command": "getCurrentState"
                    }
                ]
            },
            "osc": {
                "1": [
                    {
                        "command": "getCurrentState"
                    }
                ]
            },
            "trigger": {
                "1": [
                    {
                        "command": "getCurrentState"
                    }
                ]
            }
        }
    )
    return [reply['awg']['1'][0]['state'], reply['osc']['1'][0]['state'], reply['trigger']['1'][0]['state'], reply['osc']['1'][0]['acqCount'], reply['trigger']['1'][0]['acqCount']]


###########################################################
# Check SD card

reply = runjson(
    {
        "device":[
            {
                "command":"calibrationGetStorageTypes"
            }
        ]
    }
)

if (len(reply['device'][0]['storageTypes'])==2):
    # SD card mounted
    printstatus('SD Card mounted.')
else:
    printstatus('SD Card not mounted.')
    interrupt()

###########################################################
# Check files on SD card

reply = runjson(
    {
        "file": [{
            "command": "listdir",
            "type": "sd0",
            "path": "/"
        }]
    }
)

if (len(reply['file'][0]['files']) >= 6):
    # SD card mounted
    printstatus('All config files intact')
else:
    printstatus('Files missing.')
    interrupt()

###########################################################
# load calibration from sd card

reply = runjson(
    {
        "device":[
            {
                "command":"calibrationLoad",
                "type":"sd0"
            }
        ]
    }
)
if (reply['device'][0]['statusCode']==0):
    printstatus('Calibration loaded')
else:
    printstatus('error loading calibration')
time.sleep(2*reply['device'][0]['wait']/1000)

###########################################################
# Set parameters

reply = runjson(
        {
        "osc": {
            "1": [
                {
                    "command": "setParameters",
                    "vOffset": 0,
                    "gain": 1,
                    "sampleFreq": oscfreq*1000, # 1000000 mHz = 1kS/sec
                    "bufferSize": sample_size, # Sample size
                    "triggerDelay": 0
                }
            ]
        },
        "trigger": {
            "1": [
                {
                    "command": "setParameters",
                    "source": {
                        "instrument": "osc",
                        "channel": 1,
                        "type": "risingEdge",
                        "lowerThreshold": 0,
                        "upperThreshold": 500
                    },
                    "targets": {
                        "osc": [
                            1
                        ]
                    }
                }
            ]
        }
    }
)
if (reply['osc']['1'][0]['statusCode'] ==0 & reply['trigger']['1'][0]['statusCode'] == 0):
    printstatus('OSC and Trigger configured.')
else:
    printstatus('Error configuring osc and trigger.')

###########################################################
# Testing

if testing:
    reply = runjson(
        {
            "awg": {
                "1": [
                    {
                        "command": "setRegularWaveform",
                        "signalType": "sine",
                        "signalFreq": awgfreq*1000,
                        "vpp": 3000,
                        "vOffset": 0
                    }
                ]
            }
        }
    )
    if (reply['awg']['1'][0]['statusCode']!=0):
        print('Error with awg setup')
        interrupt()
    reply = runjson(
        {
            "awg": {
                "1": [
                    {
                        "command": "run"
                    }
                ]
            }
        }
    )
    if (reply['awg']['1'][0]['statusCode']!=0):
        print('Error with awg run')
        interrupt()
    else:
        print('Testing case : AWG setup done')

###########################################################
# Main loop

acqCount= 0
while(acqCount < maxacqCount):
    while (True):
        reply = runjson(
            {
                "trigger":{
                    "1":[
                        {
                            "command":"single"
                        }
                    ]
                }
            }
        )
        if(reply['trigger']['1'][0]['statusCode']==0):
            acqCount = reply['trigger']['1'][0]['acqCount']
            printstatus('Trigger armed for acqCount = ' + str(acqCount))
            break  
        else:
            # iterate
            time.sleep(0.5)
            continue
    # Wait for osc to finish acq
    time.sleep(sample_size/oscfreq)
    # Check osc state 
    while (True):
        # Wait till osc is triggered.
        [awg_state,osc_state,trg_state,acqCount_osc,acqCount_trg] = check()
        if(osc_state=='triggered'):
            printstatus('Data for Acqition count '+ str(acqCount_trg) + ' ..wiritng to disk')
            oscread(acqCount_trg)
            break
        else:
            # iterate
            time.sleep(0.5)
    # Wait between two readings
    time.sleep(waitInterval) 

################################################
# Reset device and end

runjson(
    {
        "device":[
            {
                "command":"resetInstruments"
            }
        ]
    }
)
