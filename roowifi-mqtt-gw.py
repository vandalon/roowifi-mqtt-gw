#!/usr/bin/env python
import socket
import time
import struct
import paho.mqtt.client as mqtt

roomba_host = '192.168.1.234'
mqtt_host = 'localhost'
mqtt_roomba_command_topic = 'home/roomba/command'
mqtt_roomba_topic = 'home/roomba/' #Trailing slash is mandetory!

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((roomba_host, 9001))
s.close()
time.sleep(2)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((roomba_host, 9001))

def on_connect(client, userdata, flags, rc):
    print("MQTT Connected with result code "+str(rc))
    client.subscribe(mqtt_roomba_command_topic)

def on_message(client, userdata, msg):
    s.send(chr(128))
    if str(msg.payload) == 'clean':
        s.send(chr(135))
    if str(msg.payload) == 'spot':
        s.send(chr(134))
    if str(msg.payload) == 'dock':
        s.send(chr(143))

prev_states = {}
def roomba_state(state):
    s.send(chr(142))
    if state == 2:
        s.send(chr(state))
        data = s.recv(6)
        print(repr(data))
        states = dict(zip(('opcode','button','distance','angle'), (struct.unpack('>Bbhh', data))))
    elif state == 3:
        s.send(chr(state))
        data = s.recv(10)
        print(repr(data))
        states = dict(zip(('chargingState','voltage','current','temp','charge','capacity'), (struct.unpack('>bHhbHH', data))))
        if states['chargingState'] == 0 and states['current'] < -250:
            states['running'] = 1
        else:
            states['running'] = 0
    for item in states:
        if item not in prev_states:
            prev_states[item] = ""
        if states[item] != prev_states[item]:
            mqttClient.publish(mqtt_roomba_topic+item, payload=states[item], qos=0, retain=False)
        prev_states[item] = states[item]
    return states

    

def get_states():
    roomba_state(3)
    roomba_state(2)

mqttClient = mqtt.Client()
mqttClient.on_connect = on_connect
mqttClient.on_message = on_message
mqttClient.connect(mqtt_host, 1883, 60)

mqttClient.loop_start()
while True:
    get_states()
    time.sleep(1)

s.close()
