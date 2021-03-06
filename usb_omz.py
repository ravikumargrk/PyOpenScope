#########################################################
#  Author : Ravi Kumar https://github.com/ravikumargrk  #
#  Code to automate data acquisition from openscope     #
#########################################################

#!/bin/bash/python3
# -*- coding: utf-8 -*-
from os import mkdir
from datetime import datetime

import json
import time
import serial
import re
import os
import sys
import pprint
pp = pprint.PrettyPrinter(indent=4)
###########################################################
# SETUP
omz_addr = '/dev/ttyUSB0'
omz_br   = 115200
wait_for_response = 1
omz_timeout = 2
buffersize = 4096

# boolean
force = False
indicate_status = False
testing = True
awgfreq = 100 # Hz

vpp = 510
vdc = 500
trg_l = 0
trg_h = 600
signalstr = "sine"

oscfreq = 1000 # S/sec
sample_size = 30000 # limit
waitInterval = 5 # sec
maxacqCount = 2 # no. of files
maxreadcount = 5
omz = serial.Serial(omz_addr, omz_br, timeout = omz_timeout)

now = datetime.now()
dt_string = now.strftime("%d%m%Y%H%M%S")
foldername = "data_" + dt_string
mkdir(foldername)

#################################################
# definitions
def runjson(payload):
    readcount = 0
    while (readcount < maxreadcount):
        try:
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
        except:
            continue
    return None
    
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
    payload = {'osc': {'1': [{'command': 'read', 'acqCount': acqCount}]}}
    # open port
    if not omz.is_open:
        omz.open()
    omz.flush()
    # write
    omz.write(json.dumps(payload).encode())
    # wait for response
    time.sleep(wait_for_response)

    # read
    replystr = b''
    while (omz.in_waiting > 0):
        buffer = omz.read(buffersize)
        replystr += buffer
    omz.close()
    # Split
    result = re.split(b'\r\n',replystr)

    # Check if you got data
    if (len(result) < 3):
        return [0, 0, len(result)]
    
    # json at index 1
    reply_json_str = result[1]
    # chop off right
    reply_json_str = reply_json_str[reply_json_str.find(b'{'):reply_json_str.rfind(b'}')+1]
    # Decode bytes, and convert single quotes to double quotes for valid JSON
    reply_json_str = reply_json_str.decode('ASCII').replace("'", '"')

    # slice of incase of extra bytes attached
    reply_json = json.loads(reply_json_str)

    # pp.pprint(reply_json)
    # Get parameters
    BinaryOffset = reply_json['osc']['1'][0]['binaryOffset']
    BinaryLength = reply_json['osc']['1'][0]['binaryLength']
    acqCount = reply_json['osc']['1'][0]['acqCount']
    sampleFreq = reply_json['osc']['1'][0]['actualSampleFreq']/1000
    filename = "AC" + str(acqCount) + "SR" + str(oscfreq)

    # data's in the 3rd chunk apparently
    datastr = result[3]
    # # write binary file and convert later
    
    with open(foldername + "/" + filename + ".bin", "wb") as file:
        for byte in datastr:
            file.write(byte.to_bytes(1, byteorder='big'))
    
    #return stats
    return [BinaryLength, len(datastr), len(result)]

# check states and acquisition counts   
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

if (len(reply['file'][0]['files']) >= 5):
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
                        "lowerThreshold": trg_l,
                        "upperThreshold": trg_h
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
                        "signalType": signalstr,
                        "signalFreq": awgfreq*1000,
                        "vpp": vpp,
                        "vOffset": vdc
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
    print('Acquisition #: ' + str(acqCount+1) + ' state: arming', end='')
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
            print('\rAcquisition #: ' + str(acqCount) + ' state: armed     ', end='')
            break  
        else:
            # iterate
            time.sleep(0.5)
            continue
    
    while (True):
        # Check osc state 
        [awg_state,osc_state,trg_state,acqCount_osc,acqCount_trg] = check()
        # Wait till osc is triggered.
        if(osc_state=='armed'):
            # force trigger
            if force:
                reply = runjson(
                    {
                        "trigger":{
                            "1":[
                                {
                                    "command":"forceTrigger"
                                }
                            ]
                        }
                    }
                )
            time.sleep(0.5)
            continue

        if(osc_state=='acquiring'):
            # Wait for osc to finish acquiring
            print('\rAcquisition #: ' + str(acqCount) + ' state: acquiring ', end='')
            time.sleep(sample_size/oscfreq)
            continue
        
        if(osc_state=='triggered'):
            print('\rAcquisition #: ' + str(acqCount) + ' state: triggered ', end='')
            break

    # read loop
    readcount = 0
    errormsg = ''
    while (readcount < maxreadcount):
        try:
            t = time.time()
            stats = oscread(acqCount_trg)
            elapsed = time.time() - t
            readcount+=1
            if(stats[2] > 3):
                print('\rAcquisition #: ' + str(acqCount) + ' state: saved ' + str(stats[1]*100//stats[0]) + '% data | time : ' + str(round(elapsed,2)) + ' sec')
                readcount = -1
                break
        except:
            readcount = maxacqCount
            filepath = foldername + '/' + 'AC' + str(acqCount) + 'SR' + str(oscfreq) + '.bin'
            if os.path.exists(filepath):
                os.remove(filepath)
            errormsg = str(sys.exc_info())
            print('\rAcquisition #: ' + str(acqCount) + ' state: save failed. Exception: ' + errormsg)
            break

    # proces result
    if(readcount != -1):
        print('\rAcquisition #: ' + str(acqCount) + ' state: save failed. Read Count: ' + str(readcount) )
        
    # Wait between two readings
    if(acqCount < maxacqCount):
        time.sleep(waitInterval) 

################################################
# Reset device and end transmission

runjson(
    {
        "device":[
            {
                "command":"resetInstruments"
            }
        ]
    }
)
