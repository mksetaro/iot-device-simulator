#!/usr/bin/env python
import json
import ssl
import schedule
import time
import threading
import logging
from os import sys, environ
import signal
from iotunit import IOTUnit
import json
import generated_parameters as params

#

class ProgramKilled(Exception):
    pass

class IOTContainer:
    
    def __init__(self, json_config_file_path):
        logger_cfg, client_cfg, pods_cfg = self.load_config(json_config_file_path)
        sys.path.append(pods_cfg.GetPodsPyModulePath().Get())
        logging.basicConfig(filename=logger_cfg.GetFilePath().Get(), filemode='w', format='%(asctime)s -%(levelname)s- %(message)s', level=logger_cfg.GetVerbosity().Get()) 
        self.bind_signal_handlers()
        self.setup_daemon_thread()
        self.setup_client(client_cfg)
        self.init_pods(pods_cfg, client_cfg)
    
    def load_config(self, json_config_file_path):
        try:
            json_config = json.load(open(json_config_file_path))
            parameters = params.Parameters(json_config)
            return parameters.GetLogger(), parameters.GetClient(), parameters.GetPods()
        except IOError:
            raise ProgramKilled
        except json.decoder.JSONDecodeError:
            raise ProgramKilled

    def bind_signal_handlers(self):
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        self.shutdown_flag.set()
        logging.info("shutdown signal received")
        raise ProgramKilled
    
    def setup_daemon_thread(self):
        self.shutdown_flag = threading.Event()
        self.scheduler = schedule
        self.scheduler_thread = threading.Thread(name = 'scheduler daemon', target = self.daemon_scheduler)
        self.scheduler_thread.setDaemon(True)
    
    def setup_client(self,client_cfg):
        pass

    def init_pods(self, pods_cfg, client_cfg):
        self.pods_map = { }
        try:
            pods_list = json.load(open(pods_cfg.GetPodsListFilePath().Get()))
            #to be removed when config migration will be complete
            client_config_tmp=json.dumps(client_cfg, default=lambda x: x.Serializable())
            for pod in pods_list:
                pod_tmp = IOTUnit(pod, json.loads(client_config_tmp), self.scheduler)
                self.pods_map[pod['name']] = pod_tmp
        except Exception:
           logging.error("init iot units failed")
           raise ValueError
        logging.info("iot units initialized -> %s", self.pods_map.keys())

    def mqtt_threads_start(self):
        for pod in self.pods_map.values():
            pod.start_mqtt_loop()
        logging.info("clients loop started")
    
    def mqtt_threads_stop(self):
        for pod in self.pods_map.values():
            pod.stop_mqtt_loop()
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