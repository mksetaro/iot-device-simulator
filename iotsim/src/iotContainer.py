#!/usr/bin/env python

import paho.mqtt.client as mqtt
import importlib
import json
import ssl
import schedule
import time
import threading
import logging

import os
from os import sys, environ
import iotsim.config.iotconfig as cfg

sys.path.append(cfg.mqtt_modules['modulesFolder'])
logging.basicConfig(filename=cfg.logger['logFilePath'], filemode='w', format='%(asctime)s -%(levelname)s- %(message)s', level=cfg.logger['loggerLevel']) 

NOTIFICATION_TYPE = 'NOTIFICATION'
SINGLE_SHOT_TYPE = 'SINGLE_SHOT'
PERIODIC_TYPE = 'PERIODIC'
DATA_WRITE_TYPE = 'DATA_WRITE'
REQUEST_TYPE = 'REQUEST'

class ProgramKilled(Exception):
    pass

class DataSubscriber:
    
    def __init__(self, subscriber_cfg, owner):
        self.owner = owner
        self.id = subscriber_cfg['id']
        self.type = subscriber_cfg['type']
        self.topic = subscriber_cfg['topic']
        self.register_subscriber(subscriber_cfg)
    
    def register_subscriber(self, cfg):
        try:
            self.owner.client.subscribe(self.topic)
            if self.type == DATA_WRITE_TYPE:
                self.register_write_key = cfg['write']
                self.owner.client.message_callback_add(self.topic, self.on_message_data_write)
            elif self.type == REQUEST_TYPE:
                self.module = importlib.import_module(cfg['request_module'])
                self.notifier_name = cfg['notifier']
                self.owner.client.message_callback_add(self.topic, self.on_message_request)        
        except Exception:
            logging.error("register_subscriber -> %s failed", self.id)
            raise ValueError
        logging.info("subscribed topic %(topic)s as %(type)s", {'topic': self.topic,'type':self.type})
    
    def on_message_data_write(self, client, userdata, message):
        logging.debug("received %(payload)s on topic %(topic)s", {'payload':message.payload,'topic':message.topic})
        self.owner.set_register_value(self.register_write_key, message.payload)

    def on_message_request(self, client, userdata, message):
        logging.debug("request %(payload)s received on topic %(topic)s", {'payload':message.payload,'topic':message.topic})
        self.owner.process_request_threaded(self.module.process_request, message.payload, self.notifier_name)
   
class DataPublisher:    
    def __init__(self, scheduler, publisher_cfg, owner):
        self.owner = owner
        self.id = publisher_cfg['id']
        self.register_read_key = publisher_cfg['read']
        self.topic = publisher_cfg['topic']
        self.type = publisher_cfg['type']
        self.register_publisher(scheduler, publisher_cfg)
        
    def register_publisher(self, scheduler, cfg):
        try:
            if self.type == PERIODIC_TYPE or self.type == SINGLE_SHOT_TYPE:       
                self.execution_timer = cfg['timer_seconds']
                scheduler.every(self.execution_timer).seconds.do(self.run_threaded, self.publish)
            elif self.type == NOTIFICATION_TYPE:
                pass
        except Exception:
            logging.error("register_publisher -> %s failed", self.id)
            raise ValueError
        logging.info("publishing on topic %(topic)s as %(type)s", {'topic': self.topic,'type':self.type})
           
    def run_threaded(self, job_func):
        job_thread = threading.Thread(target = job_func)
        job_thread.start()
        if self.type == SINGLE_SHOT_TYPE:
            return schedule.CancelJob

    def publish(self):
        payload = self.owner.get_register_value(self.register_read_key)
        self.owner.client.publish(self.topic, payload)
    
    def publish_notification(self):
        notification_thread = threading.Thread(target = self.publish)
        notification_thread.start()

class IOTUnit:
    
    def __init__(self, unit_cfg, scheduler):
        self.name = unit_cfg['name']
        self.registers = unit_cfg['registers']
        self.notifiers = {}
        self.publishers = {}
        self.subscribers = {}      
        if cfg.mqtt_client['use_certificates']:
            self.init_ssl_context()
        self.init_mqtt_connection()
        self.init_data_publishers(scheduler, unit_cfg['publishers'])
        self.init_data_subscribers(unit_cfg['subscribers'])
        self.init_control_loop(scheduler, unit_cfg)
    
    def init_ssl_context(self):
        try:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.load_verify_locations(cfg.mqtt_client['rootCA'])
            self.ssl_context.load_cert_chain(cfg.mqtt_client['clientCertificate'], cfg.mqtt_client['clientKey'])
        except Exception:
            logging.error('init_ssl_context failed for %s', self.name)
            raise ValueError
        logging.info('ssl_context created for %s', self.name)

    def init_mqtt_connection(self):
        try:
            self.client = mqtt.Client()
            if cfg.mqtt_client['use_certificates']:
                self.client.tls_set_context(self.ssl_context)
            self.client.connect(cfg.mqtt_client['host'], cfg.mqtt_client['port'])
        except Exception:
            logging.error("init_mqtt_connection failed for %s", self.name)
            raise ValueError
        logging.info('unit %(name)s successfully connected to broker %(host)s:%(port)s', {'name':self.name,'host':cfg.mqtt_client['host'],'port':cfg.mqtt_client['port']})
    def init_control_loop(self, scheduler, cfg):
        try:
            control_loop_module = cfg['control_loop_module']
            if control_loop_module is None:
                pass
            else:
                sleep_time = cfg['control_loop_sleep_ms'] 
                self.control_loop_module = importlib.import_module(control_loop_module)
                scheduler.every(sleep_time/1000).seconds.do(self.control_loop_threaded, self.control_loop_module.run)
                logging.info("control loop %(loop)s initialized for unit %(name)s",{'loop':control_loop_module, 'name':self.name})
        except Exception:
            logging.error("failed to initialize control loop for unit %s", self.name)
            raise ValueError

    def init_data_publishers(self, scheduler, pubList):
        try:
            for pub in pubList:
                pub_tmp = DataPublisher(scheduler, pub, self)
                if pub['type'] == NOTIFICATION_TYPE:
                   self.notifiers[pub['id']] = pub_tmp
                else:
                   self.publishers[pub['id']] = pub_tmp
        except Exception:
            logging.error("init data publishers failed for unit %s", self.name)
            raise ValueError
        logging.debug("init data publisher -notifiers:%(notifiers)s -publishers:%(publishers)s",{'notifiers': self.notifiers, 'publishers':self.publishers})
    def init_data_subscribers(self, subList):
        try: 
            for sub in subList:
                sub_tmp = DataSubscriber(sub, self)
                self.subscribers[sub['id']] = sub_tmp
        except Exception:
            logging.error("init data subscribers failed for unit %s", self.name)
            raise ValueError
        logging.debug("init data subscribers -subscribers:%s", self.subscribers)
    
    def get_register_value(self, key):
        return self.registers[key]
    
    def set_register_value(self, key, value):
        logging.debug("setting register %(key)s -> old value:%(oldV)s new value:%(newV)s",{'key':key, 'oldV':self.registers[key], 'newV':value})
        self.registers[key] = value

    def start_mqtt_loop(self):
        self.client.loop_start()
    
    def stop_mqtt_loop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def control_loop_threaded(self, job_func):
        job_thread = threading.Thread(target = job_func, args=(self.registers, self.notifiers))
        job_thread.start()

        
    def process_request_threaded(self, req_func, payload, notifier_name_key):
        req_thread = threading.Thread(target = req_func, args=(self.registers, payload, self.notifiers[notifier_name_key].publish_notification))
        req_thread.start()

class IOTContainer:
    
    def __init__(self):
        self.shutdown_flag = threading.Event()
        self.unitMap = { }
        self.scheduler = schedule
        self.scheduler_thread = threading.Thread(name = 'scheduler daemon', target = self.daemon_scheduler)
        self.scheduler_thread.setDaemon(True)
        self.init_iot_units()

    def signal_handler(self, signum, frame):
        self.shutdown_flag.set()
        logging.info("shutdown signal received")
        raise ProgramKilled

    def init_iot_units(self):
        try:
            self.unitList = json.load(open(cfg.mqtt_modules['iotUnitList']))
            for unit in self.unitList:
                unit_tmp = IOTUnit(unit, self.scheduler)
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

