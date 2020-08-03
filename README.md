# About
A smart DAQ. Python (3.8) code that runs on your PC or RPi, interacts with OpenScope MZ (by digilent) over WiFi to automate the process of collecting data from openscope

You could run this file in RPi and the combo RPi+OpenScope becomes your own smart / automated oscilloscope

# Files
## driver.py 
* Sets up parameters like sampling rate, sample size and number of acquisitins to be done and wait interval between the acquisitions
* Script takes maxacqCount number of acuisition in different files and saves it as CSV files.

