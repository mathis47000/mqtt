#! /usr/bin/python3

import socket
import logging
import sys
import os
import traceback
import select
from sys import stdin

PORT = 1883
TYPE_CONNECT = 0x10
TYPE_CONNACK = 0x20
TYPE_PUBLISH = 0x30
TYPE_SUBSCRIBE = 0x82
TYPE_SUBACK = 0x90
TYPE_DISCONNECT = 0xe0

### auxiliary routines ###

def create_mqtt_publish_msg(topic, value, retain=False):
    """ 
    Creates a mqtt packet of type PUBLISH with DUP Flag=0 and QoS=0.
    >>> create_mqtt_publish_msg("temperature", "45", False).hex()
    '300f000b74656d70657261747572653435'
    >>> create_mqtt_publish_msg("temperature", "45", True).hex()
    '310f000b74656d70657261747572653435'
    """
    retain_code = 0
    if retain:
        retain_code = 1
    # 0011 0000 : Message Type = Publish ; Dup Flag = 0 ; QoS = 0
    msg_mqtt_flags = (TYPE_PUBLISH + retain_code).to_bytes(1, byteorder='big')
    msg_topic = topic.encode("ascii")
    msg_value = bytes(value, "ascii")
    msg_topic_length = len(msg_topic).to_bytes(2, byteorder='big')
    msg = msg_topic_length + msg_topic + msg_value
    msg_length = len(msg).to_bytes(1, byteorder='big')
    return msg_mqtt_flags + msg_length + msg

def create_mqtt_subscriber_msg(topic, sub_id):
    """ 
    Creates a mqtt packet of type SUBSCRIBE with QoS=0.
    >>> create_mqtt_subscriber_msg("temper",1).hex()
    '820b0001000674656d70657200'
    """
    msg_mqtt_flags = (TYPE_SUBSCRIBE).to_bytes(1, byteorder='big')
    msg_mqtt_id = sub_id.to_bytes(2, byteorder='big')
    Qos = (0).to_bytes(1, byteorder='big')
    msg_topic = topic.encode("ascii")
    msg_topic_length = len(msg_topic).to_bytes(2, byteorder='big')
    msg = msg_mqtt_id + msg_topic_length + msg_topic + Qos
    msg_length = len(msg).to_bytes(1, byteorder='big')
    return msg_mqtt_flags + msg_length + msg

def create_mqtt_connect_msg(connect_id):
    """ 
    Creates a mqtt packet of type CONNECT
    >>> create_mqtt_connect_msg("mosq-6F4yNCdkrVx80t8BVp").hex()
    '102300044d5154540402003c00176d6f73712d364634794e43646b72567838307438425670'
    >>> create_mqtt_connect_msg("mosq-1BtWeOul8kXqCGAolF").hex()
    '102300044d5154540402003c00176d6f73712d31427457654f756c386b58714347416f6c46'
    """
    msg_mqtt_header = (TYPE_CONNECT).to_bytes(1, byteorder='big')
    protocol = "MQTT".encode("ascii")
    protocol_l = len(protocol).to_bytes(2, byteorder='big')
    version = (4).to_bytes(1, byteorder='big')
    connect_flags = (2).to_bytes(1, byteorder='big')
    keep_alive = (60).to_bytes(2, byteorder='big')
    client_id = connect_id.encode("ascii")
    client_id_l = len(client_id).to_bytes(2, byteorder='big')
    msg = protocol_l + protocol + version + connect_flags + keep_alive + client_id_l + client_id
    msg_l = len(msg).to_bytes(1, byteorder='big')
    return msg_mqtt_header + msg_l + msg

def create_mqtt_disconnect_msg():
    """ 
    Creates a mqtt packet of type DISCONNECT
    >>> create_mqtt_disconnect_msg().hex()
    'e000'
    """
    msg_mqtt_header = (TYPE_DISCONNECT).to_bytes(1, byteorder='big')
    msg_l = (0).to_bytes(1, byteorder='big')
    return msg_mqtt_header + msg_l

def create_mqtt_connack_msg():
    """ 
    Creates a mqtt packet of type CONNECT
    >>> create_mqtt_connack_msg().hex()
    '20020000'
    """
    msg_mqtt_header = (TYPE_CONNACK).to_bytes(1, byteorder='big')
    ack_flags = (0).to_bytes(1, byteorder='big')
    code = (0).to_bytes(1, byteorder='big')
    msg = ack_flags + code
    msg_l = len(msg).to_bytes(1, byteorder='big')
    return msg_mqtt_header + msg_l + msg

def create_mqtt_suback_msg(sub_id):
    """ 
    Creates a mqtt packet of type CONNECT
    >>> create_mqtt_suback_msg(1).hex()
    '9003000100'
    """
    msg_mqtt_header = (TYPE_SUBACK).to_bytes(1, byteorder='big')
    msg_id = sub_id.to_bytes(2, byteorder='big')
    Qos = (0).to_bytes(1, byteorder='big')
    msg = msg_id + Qos
    msg_l = len(msg).to_bytes(1, byteorder='big')
    return msg_mqtt_header + msg_l + msg

def get_pub_topic(msg):
    """ 
    Decode topic of type PUBLISH
    >>> get_pub_topic(create_mqtt_publish_msg("temper","24"))
    'temper'
    """
    topic_l = int(msg[2:4].hex(),16)
    topic = msg[4:topic_l+4].decode("UTF-8")
    return topic

def get_pub_value(msg):
    """ 
    Decode value of type PUBLISH
    >>> get_pub_value(create_mqtt_publish_msg("temper","24"))
    '24'
    >>> get_pub_value(create_mqtt_publish_msg("temperdefqdfqdffdq","24323"))
    '24323'
    """
    topic_l = int(msg[2:4].hex(),16)
    msg_l = int(msg[1:2].hex(),16)
    value = msg[topic_l+4:msg_l+4].decode("UTF-8")
    return value

def get_sub_topic(msg):
    """ 
    Decode value of type PUBLISH
    >>> get_sub_topic(create_mqtt_subscriber_msg("temper", 1))
    'temper'
    >>> get_sub_topic(create_mqtt_subscriber_msg("temperdefqdfqdffdq",123))
    'temperdefqdfqdffdq'
    """
    topic_l = int(msg[4:6].hex(),16)
    topic = msg[6:topic_l+6].decode("UTF-8")
    return topic

def get_sub_id(msg):
    """ 
    Decode value of type PUBLISH
    >>> get_sub_id(create_mqtt_subscriber_msg("temper", 1))
    1
    >>> get_sub_id(create_mqtt_subscriber_msg("temperdefqdfqdffdq",123))
    123
    """
    id = int(msg[2:4].hex(),16)
    return id

def get_connect_id(msg):
    """ 
    Decode value of type PUBLISH
    >>> get_connect_id(create_mqtt_connect_msg("temper"))
    'temper'
    >>> get_connect_id(create_mqtt_connect_msg("mosq-1BtWeOul8kXqCGAolF"))
    'mosq-1BtWeOul8kXqCGAolF'
    """
    id_l = int(msg[13:14].hex(),16)
    id = msg[14:id_l+14].decode('UTF-8')
    return id

def get_head(msg):
    """ 
    Decode value of type PUBLISH
    >>> get_head(create_mqtt_publish_msg("temper","24"))
    48
    >>> get_head(create_mqtt_disconnect_msg())
    224
    """
    return int(msg[0:1].hex(),16)

### main routines ###

def run_publisher(addr, topic, pub_id, retain=False):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(addr)
    s.send(create_mqtt_connect_msg(str(pub_id)))
    connack = s.recv(1500)
    if connack.hex() == '20020000':
        while True:
            value = input()
            s.send(create_mqtt_publish_msg(topic, value, retain))
            if 2 == 1:
                s.send(create_mqtt_disconnect_msg())
                break
        s.close
    
  
def run_subscriber(addr, topic, sub_id):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(addr)
    s.send(create_mqtt_connect_msg(str(sub_id)))
    connack = s.recv(1500)
    if connack.hex() == '20020000':
        s.send(create_mqtt_subscriber_msg(topic, sub_id))
        while True:
            msg = s.recv(1500)
            if get_head(msg) == int(TYPE_SUBACK):
                print("subscribed to " + topic)
            elif get_head(msg) == int(TYPE_PUBLISH):
                print(get_pub_value(msg))
            elif 2 == 1:
                s.send(create_mqtt_disconnect_msg())
                break    
        s.close

def run_server(addr):
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, 0)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    l = []
    sub = []

    while True:
        r, _, _ = select.select(l + [s], [], [])
        for s2 in r:
            if s2 == s:
                s3, a = s.accept()
                connection = s3.recv(1500)
                # connect msg
                if get_head(connection) == int(TYPE_CONNECT):
                    print("new client:", a, s3)
                    l = l + [s3]
                    s3.send(create_mqtt_connack_msg())
                else:
                    print("erreur de trame CONNECTION: " + connection)
            else:
                msg = s2.recv(1500)
                # publish msg
                if get_head(msg) == int(TYPE_PUBLISH):
                    for subscribe in sub:
                        sub_socket, sub_topic = subscribe
                        if sub_topic == get_pub_topic(msg):
                            sub_socket.send(msg)
                # subscribe msg
                elif get_head(msg) == int(TYPE_SUBSCRIBE):
                    sub = sub + [(s2,get_sub_topic(msg))]
                    s2.send(create_mqtt_suback_msg(get_sub_id(msg)))
                # disconnect msg
                elif len(msg) == 0:
                    print("client disconnected")
                    s2.close()
                    l.remove(s2)
                    continue
                s2.sendall(msg)
# run_server(('',PORT))
# run_subscriber(('',PORT), "temper", 1)
