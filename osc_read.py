# -*- coding: utf-8 -*-
import json
import time
import serial
import re
import pprint

omz_addr = 'COM3'
omz_br   = 1250000
wait_for_response = 0.5
omz_timeout = 2

omz = serial.Serial(omz_addr, omz_br, timeout = omz_timeout)
pp = pprint.PrettyPrinter(indent=4)

# write command
payload = {'osc': {'1': [{'command': 'read', 'acqCount': 1}]}}
if not omz.is_open:
    omz.open()
omz.write(json.dumps(payload).encode())
time.sleep(wait_for_response)
# read reply
replystr = b''
while(omz.in_waiting > 0):
    byte = omz.read()
    replystr += omz.read()
omz.close()

result = re.split(b'\r\n',replystr)

# convert single quotes to double quotes for valid JSON
str_json = result[1].decode('ASCII').replace("'", '"')
my_json = json.loads(str_json)

# data's in the 3rd chunk apparently
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

