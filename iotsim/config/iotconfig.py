#!/usr/bin/env python
import os
import logging

logger ={'logFilePath': os.environ['HOME'] + '/iot_simulator.log',
         'loggerLevel': logging.INFO}
paths = {'simulator_root': os.environ['HOME'] + '/Workspace/iot-device-simulator',
         'certificates_root_path': os.environ['HOME'] + '/certificates'}
mqtt_client = { 'host':'localhost',
                'port': 1883,
                'use_certificates': False,
                'rootCA': paths['certificates_root_path'] + '/ca_certificates/ca.crt',
                'clientCertificate' : paths['certificates_root_path']  + '/client_certificates/client.crt',
                'clientKey': paths['certificates_root_path']  + '/client_certificates/client.key'}
mqtt_modules = { 'iotUnitList': paths['simulator_root'] + '/examples/iotunits.json',
                 'modulesFolder': paths['simulator_root'] + '/examples/'}
