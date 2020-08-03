# -*- coding: utf-8 -*-
import requests
import re
import json
import numpy
import pprint

# url = 'http://localhost:42135'
url = 'http://10.0.0.15'

pp = pprint.PrettyPrinter(indent=4)

# Finally Read
payload = {'osc':{'1':[{'command':'read','acqCount': 0}]}}
r = requests.post(url, json=payload)
result = re.split(b'\r\n',r.content)
# Decode bytes, and convert single quotes to double quotes for valid JSON
str_json = result[1].decode('ASCII').replace("'", '"')
# Load the JSON to a Python list & pretty print formatted JSON
my_json = json.loads(str_json)
pp.pprint(my_json)

data = result[3]

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

