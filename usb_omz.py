#!/bin/bash/python3
# -*- coding: utf-8 -*-
from os import mkdir
from datetime import datetime

import json
import time
import serial
import re

###########################################################
# SETUP
omz_addr = 'COM3'
omz_br   = 1250000
wait_for_response = 1
omz_timeout = 2

# boolean
force = True
indicate_status = False
testing = True
awgfreq = 1000 # Hz

vpp = 510
vdc = 500
trg_l = 400
trg_h = 600
signalstr = "sine"

oscfreq = 1000 # S/sec
sample_size = 10000 # limit
waitInterval = 10 # sec
maxacqCount = 1 # no. of files

omz = serial.Serial(omz_addr, omz_br, timeout = omz_timeout)
omz.set_buffer_size(rx_size = 60500, tx_size = 12800)
now = datetime.now()
dt_string = now.strftime("%d%m%Y%H%M%S")
foldername = "data_" + dt_string
mkdir(foldername)

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
    [BinaryLength,ActualBinaryLength] = [0,0]
    # write command
    payload = {'osc': {'1': [{'command': 'read', 'acqCount': acqCount}]}}
    print(json.dumps(payload).encode())
    if not omz.is_open:
        omz.open()
    omz.write(json.dumps(payload).encode())
    time.sleep(wait_for_response)

    # Read header
    # format : <number>\r\n
    header = b''
    while( omz.in_waiting > 0 ):
        if( (len(header) > 2) & (header[-2:] == b'\r\n') ):
            break
        byte = omz.read()
        header += byte
    # print(header)

    # read reply json
    replystr = b''
    leftBraceCount = 0
    rightBraceCount = 0
    # while( omz.in_waiting > 0 ):
    while( ( leftBraceCount != rightBraceCount ) | (leftBraceCount == 0) ):
        byte = omz.read()
        if(byte == b'{'):
            leftBraceCount += 1
        if(byte == b'}'):
            rightBraceCount += 1
        replystr += byte
    # print(replystr)
    # Extract parameters
    reply_json = json.loads(replystr)
    BinaryLength = reply_json['osc']['1'][0]['binaryLength']
    acqCount = reply_json['osc']['1'][0]['acqCount']
    sampleFreq = reply_json['osc']['1'][0]['actualSampleFreq']/1000

    # Read secondary header
    # format : \r\n<number>\r\n
    header2 = b''
    return_count = 0
    # while( omz.in_waiting > 0 ):
    while (return_count != 2):
        byte = omz.read()
        if byte==b'\n':
            return_count += 1
        header2 += byte
    # print(header2)

    # read data
    # <BinaryLength size blob>
    datastr = b''
    # while( omz.in_waiting > 0 ):
    while(len(datastr) < BinaryLength):
        datastr += omz.read()
    # print(datastr)

    # read footer
    # format : \r\n<number>\r\n\r\n
    footer = b''
    return_count = 0
    # while( omz.in_waiting > 0 ):
    while (return_count != 3):
        byte = omz.read()
        if byte==b'\n':
            return_count += 1
        footer += byte
    # print(footer)

    # Close communications with COM port
    omz.close()

    filename = "AC" + str(acqCount) + "SR" + str(sampleFreq)

    # # write binary file and convert later
    with open(foldername + "/" + filename + ".bin", "wb") as file:
        for byte in datastr:
            file.write(byte.to_bytes(1, byteorder='big'))
    
    return len(header)+len(header2)+len(datastr)+len(footer)

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
            printstatus('Data for Acqition count '+ str(acqCount_trg) + '...reading')
            totb = oscread(acqCount_trg)
            print('Total bytes received : ' + str(totb))
            break
        if(osc_state=='acquiring'):
            continue
        else:
            # iterate
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
    # Wait between two readings
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
