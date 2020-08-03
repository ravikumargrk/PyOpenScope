# -*- coding: utf-8 -*-
import requests
import re
import json
import numpy
import pprint

# url = 'http://localhost:42135'
url = 'http://10.0.0.15'

pp = pprint.PrettyPrinter(indent=4)

# Check
payload = {"device":[{"command":"resetInstruments"}]}
r = requests.post(url, json=payload)
pp.pprint(r.json())
