#!/usr/bin/env python
import json
import ssl
import schedule
import time
import threading
import logging
from os import sys, environ
import signal
import iotsim.config.iotconfig as cfg
from iotunit import IOTUnit
import json
import typedefines

sys.path.append(cfg.mqtt_modules['modulesFolder'])
logging.basicConfig(filename=cfg.logger['logFilePath'], filemode='w', format='%(asctime)s -%(levelname)s- %(message)s', level=cfg.logger['loggerLevel']) 

class ProgramKilled(Exception):
    pass

class IOTContainer:
    
    def __init__(self, json_config_file_path):
        self.bind_signal_handlers()
        config = self.load_config(json_config_file_path)
        self.setup_daemon_thread()
        self.init_pods(config)
            
    def load_config(self, json_config_file_path):
        try:
            json_config = json.load(open(json_config_file_path))
            logging.debug("JSON config successfully loaded: %s", json_config)
            return json_config
        except IOError:
            logging.error("Cannot load config file: %s", json_config_file_path)
            raise ProgramKilled
        except json.decoder.JSONDecodeError:
            logging.error("JSON malformed, file path: %s", json_config_file_path)
            raise ProgramKilled

    def bind_signal_handlers(self):
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def setup_daemon_thread(self):
        self.shutdown_flag = threading.Event()
        self.scheduler = schedule
        self.scheduler_thread = threading.Thread(name = 'scheduler daemon', target = self.daemon_scheduler)
        self.scheduler_thread.setDaemon(True)

    def signal_handler(self, signum, frame):
        self.shutdown_flag.set()
        logging.info("shutdown signal received")
        raise ProgramKilled

    def init_pods(self, config):
        self.unitMap = { }
        try:
            self.unitList = json.load(open(config['pods']['pods_list_file_path']))
            for unit in self.unitList:
                unit_tmp = IOTUnit(unit, config['client'], self.scheduler)
                self.unitMap[unit['name']] = unit_tmp
        except Exception:
           logging.error("init iot units failed")
           raise ValueError
        logging.info("iot units initialized -> %s", self.unitMap.keys())

    def mqtt_threads_start(self):
        for unit in self.unitMap.values():
            unit.start_mqtt_loop()
        logging.info("clients loop started")
    
    def mqtt_threads_stop(self):
        for unit in self.unitMap.values():
            unit.stop_mqtt_loop()
        logging.info("clients loop stopped")

    def daemon_scheduler(self):
        while not self.shutdown_flag.is_set():
            self.scheduler.run_pending()
            time.sleep(0.5)
        logging.info("scheduler daemon clean shutdown")
        self.scheduler.clear()
        logging.info("scheduler stopped")
      
    def run(self):
        logging.info("starting iot container")
        self.scheduler_thread.start()
        self.mqtt_threads_start()
    
    def shutdown(self):
        logging.info("stopping iot container")
        self.scheduler_thread.join()
        self.mqtt_threads_stop()