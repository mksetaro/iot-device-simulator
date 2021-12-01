#!/usr/bin/env python

import os
import logging

logger ={'logFilePath': '/home/mike/iot_simulator.log',
         'loggerLevel': logging.DEBUG}
mqtt_client = { 'host':'localhost',
                'port':'8883',
                'rootCA': os.environ['CERTIFICATESPATH'] + '/ca_certificates/ca.crt',
                'clientCertificate' : os.environ['CERTIFICATESPATH'] + '/client_certificates/client.crt',
                'clientKey': os.environ['CERTIFICATESPATH'] + '/client_certificates/client.key'}
mqtt_modules = { 'iotUnitList': '/home/mike/iot_simulator/iot_units/iotunits.json',
                 'modulesFolder': '/home/mike/iot_simulator/iot_units/'}
