# -*- coding: utf-8 -*-
import requests
import re
import json
import numpy
import pprint
import time

# url = 'http://localhost:42135'
url = 'http://10.0.0.15'

pp = pprint.PrettyPrinter(indent=4)

# Load Calibration
payload = {"device":[{"command":"calibrationLoad","type":"sd0"}]}
r = requests.post(url, json=payload)
pp.pprint(r.json())

# Configure components
payload = {"awg":{"1":[{"command":"setRegularWaveform","signalType":"sine","signalFreq":1000000,"vpp":3000,"vOffset":0}]},"osc":{"1":[{"command":"setParameters","vOffset":0,"gain":1,"sampleFreq":10000000,"bufferSize":30000,"triggerDelay":0}]},"trigger":{"1":[{"command":"setParameters","source":{"instrument":"osc","channel":1,"type":"risingEdge","lowerThreshold":0,"upperThreshold":100},"targets":{"osc":[1]}},{"command":"single"}]}}
r = requests.post(url, json=payload)
pp.pprint(r.json())

# Run AWG : Comment out when not testing
payload = {"awg":{"1":[{"command":"run"}]}}
r = requests.post(url, json=payload)
pp.pprint(r.json())
time.sleep(5)

# Get all device states
payload = {"awg":{"1":[{"command":"getCurrentState"}]},"osc":{"1":[{"command":"getCurrentState"}]},"trigger": {"1": [{"command":"getCurrentState"}]}}
r = requests.post(url, json=payload)
pp.pprint(r.json())

# Finally Read
payload = {'osc': {'1': [{'command': 'read', 'acqCount': 0}]}}
r = requests.post(url, json=payload)
result = re.split(b'\r\n',r.content)
# Decode bytes, and convert single quotes to double quotes for valid JSON
str_json = result[1].decode('ASCII').replace("'", '"')
# Load the JSON to a Python list & pretty print formatted JSON
my_json = json.loads(str_json)
pp.pprint(my_json)

data = result[4]

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
	numpy.savetxt("data.csv", a, delimiter=",")

# Stop AWG
payload = {"trigger":{"1":[{"command":"stop"}]},"awg":{"1":[{"command":"stop"}]}}
r = requests.post(url, json=payload)
pp.pprint(r.json())
