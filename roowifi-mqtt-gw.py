#!/usr/bin/env python
import socket
import time
import struct
import paho.mqtt.client as mqtt
import datetime

roomba_host = '192.168.1.234'
sleep = 0.5
roomba_status = 'unknown'
charge_status = 'unknown'
mqtt_host = 'localhost'
mqtt_roomba_command_topic = 'home/roomba/command'
mqtt_roomba_topic = 'home/roomba/' # Trailing slash is mandetory!


def connect_roomba():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect((roomba_host, 9001))
    return s

s = connect_roomba()
s.close()
time.sleep(3)
s = connect_roomba()

def roomba_state():
    global roomba_status
    global charge_status
    global sleep
    s.send(chr(142))
    s.send(chr(0))
    time.sleep(0.5)
    data = s.recv(26)
    states = dict(zip(('wheeldrops','wall','cliffL','cliffFL','cliffFR','cliffR','virtualWall','motorOC','dirtL','dirtR','opcode','button','distance','angle','chargingState','voltage','current','temp','charge','capacity'), (struct.unpack('>bbbbbbbbBBBbhhbHhbHH', data))))
    charge_status = states['chargingState']
    if charge_status  == 0 and states['current'] < -250:
        states['running'] = 'ON'
    else:
        states['running'] = 'OFF'
    roomba_status = states['running']
    # When battery very empty, roombe reports very high charge values. 
    if states['charge'] > 4000: states['charge'] = 0
    battery = round(states['charge']*100/float(states['capacity']),2)
    states['battery'] = battery
    if roomba_status == 'OFF' and charge_status == 0:
        if battery >= 25: sleep = 60
        elif battery < 25: sleep = 300
        elif battery < 10: sleep = 3600
    elif charge_status > 0: sleep = 5
    else: sleep = 0.5
    # Publish to mqtt
    for item in states:
        mqttClient.publish(mqtt_roomba_topic+item, payload=states[item], qos=0, retain=False)
    return sleep


def on_connect(client, userdata, flags, rc):
    print("MQTT Connected with result code "+str(rc))
    client.subscribe(mqtt_roomba_command_topic)

def on_message(client, userdata, msg):
    attempt = 0
    cmd = 0
    if str(msg.payload) == 'CLEAN': cmd = 135
    elif str(msg.payload) == 'SPOT':
        cmd = 134
        if roomba_status != 'OFF':
            s.send(chr(135))
            time.sleep(0.5)
    elif str(msg.payload) == 'DOCK':
        cmd = 143
        if roomba_status != 'OFF':
            s.send(chr(135))
            time.sleep(0.5)
    if str(msg.payload) != 'OFF' and str(msg.payload) != 'UNDOCK':
        roomba_state()
        while roomba_status == 'OFF':
            print('Sending %s, attempt %s' % (cmd, attempt))
            s.send(chr(128))
            s.send(chr(cmd))
            if charge_status == 0: time.sleep(2)
            else: time.sleep(5)
            roomba_state()
            attempt += 1
            if attempt == 5: break
    elif str(msg.payload) == 'OFF' and roomba_status == 'ON':
        s.send(chr(135))
        time.sleep(2)
        roomba_state()
    elif str(msg.payload) == 'UNDOCK' and charge_status > 0:
        print('Undocking...')
	s.send(chr(130))
	s.send(chr(137))
	s.send(chr(255))
	s.send(chr(56))
	s.send(chr(128))
	s.send(chr(0))
	time.sleep(3)
	s.send(chr(137))
	s.send(chr(0))
	s.send(chr(0))
	s.send(chr(0))
	s.send(chr(0))
        roomba_state()

mqttClient = mqtt.Client()
mqttClient.on_connect = on_connect
mqttClient.on_message = on_message
mqttClient.connect(mqtt_host, 1883, 60)

mqttClient.loop_start()
def loop():
    while True:
        wait = roomba_state()
        timer=0
        while timer < wait:
            time.sleep(0.5)
            timer += 0.5
            if wait != sleep: break

while True:
    try:
        loop()
    except socket.timeout:
        print('Oops... reconnecting')
        s.close()
        time.sleep(5)
        s = connect_roomba()

s.close()
