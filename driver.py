#!/bin/bash/python3
# -*- coding: utf-8 -*-
import json
import pprint
import requests
import time

import re
import numpy

###########################################################
# SETUP

omz_addr = 'http://10.0.0.15' # Change to openscope's hostname
# boolean
indicate_status = False
testing = True
awgfreq = 100 # Hz
oscfreq = 2000 # S/sec
sample_size = 30000 # limit
waitInterval = 20 # sec
maxacqCount = 10 # no. of files
#status_broadcast_addr = 'http://10.0.0.16' # status indicator
pp = pprint.PrettyPrinter(indent=4)

#################################################
# definitions

def printstatus(status_str):
    #if indicate_status:
        # write status_str to status_broadcast_addr
    print(status_str)

def interrupt():
    exit()

def oscread(acqCount):
    payload = {'osc': {'1': [{'command': 'read', 'acqCount': acqCount}]}}
    r = requests.post(omz_addr, json=payload)
    result = re.split(b'\r\n',r.content)
    # Decode bytes, and convert single quotes to double quotes for valid JSON
    str_json = result[1].decode('ASCII').replace("'", '"')
    # Load the JSON to a Python list & pretty print formatted JSON
    my_json = json.loads(str_json)
    # pp.pprint(my_json)
    # data's in the 3rd chunk apparently
    data = result[3]
    # in case you want to write binary file and convert later
    if (False):
        with open("filename.bin", "wb") as file:
            for byte in data:
                file.write(byte.to_bytes(1, byteorder='big'))

    SampleFreq = my_json['osc']['1'][0]['actualSampleFreq']/1000

    mvolts=numpy.zeros(len(data)//2)
    for i in range(0, len(data)-2, 2):
        mvolts[i//2] = int.from_bytes(data[i:i+2], byteorder='little', signed=True)

    volts = mvolts / 1000
    t = numpy.arange(len(volts)) / SampleFreq

    if(len(t)==0):
        print("empty")
    else:
        a = numpy.asarray([ t, volts ])
        numpy.savetxt('DataForAcqCount='+ str(acqCount) +'.csv', a, delimiter=",")
        print('DataForAcqCount='+ str(acqCount) +'.csv'+' ... saved')


def check():
    reply = requests.post(omz_addr, json =
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
    ).json()
    return [reply['awg']['1'][0]['state'], reply['osc']['1'][0]['state'], reply['trigger']['1'][0]['state'], reply['osc']['1'][0]['acqCount'], reply['trigger']['1'][0]['acqCount']]


###########################################################
# Check SD card

reply = requests.post(omz_addr, json =
    {
        "device":[
            {
                "command":"calibrationGetStorageTypes"
            }
        ]
    }
).json()

if (len(reply['device'][0]['storageTypes'])==2):
    # SD card mounted
    printstatus('SD Card mounted.')
else:
    printstatus('SD Card not mounted.')
    interrupt()

###########################################################
# Check files on SD card

reply = requests.post(omz_addr, json =
    {
        "file": [{
            "command": "listdir",
            "type": "sd0",
            "path": "/"
        }]
    }
).json()

if (len(reply['file'][0]['files']) >= 6):
    # SD card mounted
    printstatus('All config files intact')
else:
    printstatus('Files missing.')
    interrupt()

###########################################################
# load calibration from sd card

reply = requests.post(omz_addr, json =
    {
        "device":[
            {
                "command":"calibrationLoad",
                "type":"sd0"
            }
        ]
    }
).json()
if (reply['device'][0]['statusCode']==0):
    printstatus('Calibration loaded')
else:
    printstatus('error loading calibration')
time.sleep(2*reply['device'][0]['wait']/1000)

###########################################################
# Set parameters

reply = requests.post(omz_addr, json =
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
                },
                {
                    "command": "single"
                }
            ]
        }
    }
).json()
if (reply['osc']['1'][0]['statusCode'] ==0 & reply['trigger']['1'][0]['statusCode'] == 0):
    printstatus('OSC and Trigger configured.')
else:
    printstatus('Error configuring osc and trigger.')

###########################################################
# Testing

if testing:
    reply = requests.post(omz_addr, json =
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
    ).json()
    if (reply['awg']['1'][0]['statusCode']!=0):
        print('Error with awg setup')
        interrupt()
    reply = requests.post(omz_addr, json =
        {
            "awg": {
                "1": [
                    {
                        "command": "run"
                    }
                ]
            }
        }
    ).json()
    if (reply['awg']['1'][0]['statusCode']!=0):
        print('Error with awg run')
        interrupt()
    else:
        print('Testing case : AWG setup done')
        time.sleep(20)

# [awg_state,osc_state,trg_state,acqCount_osc,acqCount_trg] = check()

# printstatus('AWG state : ' + awg_state )
# printstatus('OSC state : ' + osc_state )
# printstatus('TRG state : ' + trg_state )
# printstatus('acqCount_osc : ' + str(acqCount_osc) )
# printstatus('acqCount_trg : ' + str(acqCount_trg) )

# if ((osc_state=='idle') or (trg_state=='idle')):
#     printstatus('Problem with OSC state')
#     interrupt()

###########################################################
# Main loop
acqCount = 1
while(acqCount <= maxacqCount):
    # Check osc state 
    while (True):
        # Wait till osc is triggered.
        [awg_state,osc_state,trg_state,acqCount_osc,acqCount_trg] = check()
        if(osc_state=='triggered'):
            printstatus('Data for Acqition count '+ str(acqCount_osc) + ' ..Acquring')
            oscread(acqCount_osc)
            break
        else:
            # iterate
            time.sleep(0.5)
    # Re Arm trigger. by passing single
    while (True):
        reply = requests.post(omz_addr, json=
            {
                "trigger":{
                    "1":[
                        {
                            "command":"single"
                        }
                    ]
                }
            }
        ).json()
        if(reply['trigger']['1'][0]['statusCode']==0):
            acqCount = reply['trigger']['1'][0]['acqCount']
            printstatus('OSC triggered for AcqCount = ' + str(acqCount))
            break
        else:
            # iterate
            time.sleep(0.5)
            continue
    time.sleep(waitInterval) # wait for 5 minutes

# Reset device and end
r = requests.post(omz_addr, json=
    {
        "device":[
            {
                "command":"resetInstruments"
            }
        ]
    }
)