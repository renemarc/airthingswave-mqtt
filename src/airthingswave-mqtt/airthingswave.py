import yaml
import logging
import paho.mqtt.client as mqtt
from bluepy.btle import UUID, Peripheral
from datetime import datetime
import sys
import time
import struct
import re

class Sensor:
    def __init__(self, name, uuid, format_type, unit, scale):
        self.name = name
        self.uuid = uuid
        self.format_type = format_type
        self.unit = unit
        self.scale = scale

class AirthingsWave_mqtt:
    def __init__(self, config_file):
        with open(config_file, 'r') as f:
            self.config=yaml.load(f)
        self.waves=list()
        if self.check_config(self.config):
            self.mqtt_client = mqtt.Client()
            self.mqtt_connect(self.config)
        self.sensors = []
        self.sensors.append(Sensor("DateTime", UUID(0x2A08), 'HBBBBB', "\t", 0))
        self.sensors.append(Sensor("Temperature", UUID(0x2A6E), 'h', "deg C\t", 1.0/100.0))
        self.sensors.append(Sensor("Humidity", UUID(0x2A6F), 'H', "%\t\t", 1.0/100.0))
        self.sensors.append(Sensor("Radon-Day", "b42e01aa-ade7-11e4-89d3-123b93f75cba", 'H', "Bq/m3\t", 1.0))
        self.sensors.append(Sensor("Radon-Long-Term", "b42e0a4c-ade7-11e4-89d3-123b93f75cba", 'H', "Bq/m3\t", 1.0))

    def check_config(self, conf):
        if "mqtt" not in conf:
            return False
        if "broker" not in conf["mqtt"]:
            return False
        if "port" not in conf["mqtt"]:
            return False
        if "waves" in conf:
            for wave in conf["waves"]:
                if "addr" in wave and "name" in wave:
                    self.waves.append(wave)
                else:
                    print("Malformed config item: {0}".format(wave))
        return True

    def mqtt_connect(self, conf):
	self.mqtt_conf=self.config["mqtt"]
	self.mqtt_client.connect(self.mqtt_conf["broker"], self.mqtt_conf["port"])

    def ble_connect(self, addr):
	p = Peripheral(addr)
	return p

    def ble_disconnect(self, p):
       p.disconnect()

    #
    # Given a peripheral handle, populate readings for that peripheral
    #
    def get_readings(self, p):
        readings = dict()
        for s in self.sensors:
            str_out = ""
            ch  = p.getCharacteristics(uuid=s.uuid)[0]
            if (ch.supportsRead()):
                val = ch.read()
                val = struct.unpack(s.format_type, val)
                if s.name == "DateTime":
                    readings[s.name] = str(datetime(val[0], val[1], val[2], val[3], val[4], val[5]))
                else:
                    readings[s.name] = str(val[0] * s.scale)
	
        return readings

    def publish_readings(self, name, readings):
        print("name: {0}  readings: {1}".format(name,readings))
        for s in self.sensors:
            topic = "{0}/{1}".format(name, s.name)
            payload = "{0}".format(readings[s.name])
            print("{0} / {1}".format(topic,payload))
            self.mqtt_client.publish(topic,payload,retain=False)
            # Mosquitto doesn't seem to get messages published back to back
            time.sleep(0.1)
