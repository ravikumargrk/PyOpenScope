import numpy
# C:\Users\ravik\OneDrive\Documents\LiDust\ADC\Driver\data_04102020182056
foldername = 'data_04102020182056'
filename = 'AC1SR2000.0.bin'

try:
   fileobj = open(foldername + '/' + filename,'rb')
   data = fileobj.read()
finally:
   fileobj.close()

sampleFreq = float(filename[filename.index('R')+1:filename.index('.bin')])

mvolts=numpy.zeros(len(data)//2)
for i in range(0, len(data)-2, 2):
   mvolts[i//2] = int.from_bytes(data[i:i+2], byteorder='little', signed=True)

volts = mvolts / 1000
t = numpy.arange(len(volts)) / sampleFreq

a = numpy.transpose(numpy.asarray([ t, volts ]))
numpy.savetxt(foldername + '/' + filename[0:filename.index('.bin')] + '.csv', a, delimiter=",")