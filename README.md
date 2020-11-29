# About
A smart DAQ. Python (3.8) code that runs on your PC or RPi, interacts with OpenScope MZ (by digilent) over WiFi to automate the process of collecting data from openscope

This code could in RPi and the combo RPi+OpenScope becomes your own smart / automated oscilloscope / Data Acquisition System.

You might want to read this before coding on top this repo : [Digilent Instrumentation Protocol](https://reference.digilentinc.com/reference/software/digilent-instrumentation-protocol/protocol)
# Files
## usb_omz.py 
* Sets up parameters like sampling rate, sample size and number of acquisitions to be done and wait interval between the acquisitions
* Script takes maxacqCount number of acuisition in different files and saves it as CSV files.

