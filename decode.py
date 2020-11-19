import csv
import json

foldernames = ['data_22102020160959','data_22102020161252','data_22102020161353','data_22102020161444','data_22102020161618']
filename = 'AC1SR20000.0.bin'

def bin2dat(foldername,filename):
   try:
      fileobj = open(foldername + '/' + filename,'rb')
      bin_data = fileobj.read()
   finally:
      fileobj.close()

   sampleFreq = float(filename[filename.index('R') + 1 : filename.index('.bin')])

   # mvolts = numpy.zeros(len(bin_data)//2)
   # time = numpy.arange(len(mvolts)) / sampleFreq

   mvolts = [0 for i in range(0,len(bin_data)//2)]
   time = [i/sampleFreq for i in range(0,len(mvolts))]

   for i in range(0, len(bin_data)-2, 2):
      mvolts[i//2] = int.from_bytes(bin_data[i:i+2], byteorder='little', signed=True)

   data = [ time, mvolts ]
   data = list(map(list,zip(*data)))

   with open(foldername + '/' + filename[0:filename.index('.bin')] + '.csv', 'w') as f:
      writer = csv.writer(f)
      writer.writerows(data)

##################################
####   JSON File Saving ####
##################################
   # dataset = {
   #    'name':filename,
   #    'data':data
   # }

   # chart = {
   #    'status': True,
   #    'data': {
   #       'chart_title': foldername[ foldername.index('_') + 1 : ],
   #       'colors': [
   #          '#e71d36'
   #       ],
   #       'xaxis_title': 'sec',
   #       'yaxis_title': 'mV',
   #       'datasets': [dataset]
   #    }
   # }

   # with open(foldername + '/' + filename + '.json', 'w') as jsonfile:
   #    json.dump(chart, jsonfile, indent=4, sort_keys=True)

   # jsonfile.close()

for foldername in foldernames:
   bin2dat(foldername,filename)