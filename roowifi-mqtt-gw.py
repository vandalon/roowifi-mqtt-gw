#!/usr/bin/env python
import socket
import time
import struct
import paho.mqtt.client as mqtt
import datetime

roomba_host = '192.168.1.234'
sleep = 0.5
roomba_status = 'unknown'
mqtt_host = 'localhost'
mqtt_roomba_command_topic = 'home/roomba/command'
mqtt_roomba_topic = 'home/roomba/' #Trailing slash is mandetory!


def connect_roomba():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect((roomba_host, 9001))
    s.send(chr(128))
    return s

s = connect_roomba()
s.close()
time.sleep(3)
s = connect_roomba()

def roomba_state():
    global sleep
    global roomba_status
    s.send(chr(142))
    s.send(chr(0))
    time.sleep(0.5)
    data = s.recv(26)
    print("%s: %s -- %s"% (datetime.datetime.now(), sleep, repr(data)))
    states = dict(zip(('wheeldrops','wall','cliffL','cliffFL','cliffFR','cliffR','virtualWall','motorOC','dirtL','dirtR','opcode','button','distance','angle','chargingState','voltage','current','temp','charge','capacity'), (struct.unpack('>bbbbbbbbBBBbhhbHhbHH', data))))
    if states['chargingState'] == 0 and states['current'] < -250:
        states['running'] = 'ON'
    else:
        states['running'] = 'OFF'
    roomba_status = states['running']
    battery = states['charge']*100/states['capacity']
    states['battery'] = battery
    if battery < 50: sleep = 60
    elif battery < 25: sleep = 300
    elif battery < 10: sleep = 3600

    for item in states:
        mqttClient.publish(mqtt_roomba_topic+item, payload=states[item], qos=0, retain=False)

    return states

def on_connect(client, userdata, flags, rc):
    print("MQTT Connected with result code "+str(rc))
    client.subscribe(mqtt_roomba_command_topic)

def on_message(client, userdata, msg):
    global roomba_status
    if str(msg.payload) == 'CLEAN':
        if roomba_status == 'OFF':
            s.send(chr(135))
    if str(msg.payload) == 'SPOT':
        if roomba_status == 'OFF':
            s.send(chr(134))
        else:
            s.send(chr(135))
            time.sleep(0.5)
            s.send(chr(134))
    if str(msg.payload) == 'DOCK':
        if roomba_status == 'OFF':
            s.send(chr(143))
        else:
            s.send(chr(135))
            time.sleep(0.5)
            s.send(chr(143))
    if str(msg.payload) == 'OFF' and roomba_status == 'ON':
            s.send(chr(135))
    time.sleep(3)
    roomba_state()

mqttClient = mqtt.Client()
mqttClient.on_connect = on_connect
mqttClient.on_message = on_message
mqttClient.connect(mqtt_host, 1883, 60)

mqttClient.loop_start()
def loop():
    while True:
        roomba_state()
        time.sleep(sleep)

while True:
    try:
        loop()
    except socket.timeout:
        print('Oops... reconnecting')
        s.close()
        time.sleep(5)
        s = connect_roomba()
    except:
        break

s.close()
