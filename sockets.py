#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request, Response
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    """ An example world
    {
        'a':{'x':1, 'y':2},
        'b':{'x':2, 'y':3}
    }
    """
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        self.counter = 1

    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())

    def world(self):
        return self.space

    def setCounter(self, value):
        self.counter = value

    def getNextCounter(self):
        return self.counter

myWorld = World()

def set_listener( entity, data ):
    ''' do something with the update ! '''
    # send it out to all of our connections/clients?

myWorld.add_set_listener( set_listener )

# From broadcast.py
clients = list()

def send_all(entity):
    for client in clients:
        client.put( entity )

def send_all_json(obj):
    send_all(json.dumps(obj))

# From chat.py
class Client:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, v):
        self.queue.put_nowait(v)

    def get(self):
        return self.queue.get()


@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return flask.redirect('/static/index.html')

def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLEMENT ME
    # From broadcast.py
    try:
        while True:
            entityData = ws.receive()
            print "WS RECV: %s" % entityData
            if (entityData is not None):
                # if the entity is not None, then send info to everyone
                #myWorld.set(entityData["entity"], entityData["data"])
                #if entity in myWorld.world().keys():
                #    for key in data.keys():
                #        myWorld.update(entity, key, data[key])
                #else: # This is a new entry
                #    myWorld.set(entity, data)

                # Old implementation
                packet = json.loads(entityData)
                #print "packet: %s" % packet
                #print "packet.__class__: %s" % packet.__class__
                if "entity" in packet.keys():
                    print packet.keys()
                    myWorld.set(packet["entity"], packet["data"])
                    myWorld.setCounter(packet["counter"])
                    send_all_json(packet)
                    # end old implementation
                else:
                    key = packet.keys()[0]
                    data = packet[key]
                    myWorld.set(key, data)
                    send_all_json(packet)
            else:
                break
    except:
        """ done """
        pass

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    # XXX: TODO IMPLEMENT ME
    # From broadcast.py
    client = Client()
    clients.append(client)
    g = gevent.spawn(read_ws, ws, client)
    print "Subcribing"
    try:
        while True:
            #block here
            # We should just get the whole world and send it here
            entity = client.get()
            #print entity
            ws.send(entity)
    except Exception as e: #WebSocketError as e:
        print "WS Error: %s" % e
    finally:
        clients.remove(client)
        gevent.kill(g)

# Took this from my assignment 4
def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data != ''):
        return json.loads(request.data)
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    return None

@app.route("/world", methods=['POST','GET'])
def world():
    '''you should probably return the world here'''
    # Took this from my assignment 4
    resp = Response(status=200)
    worldData = myWorld.world()
    counter = myWorld.getNextCounter()
    jsonData = json.dumps({"world": worldData, "counter": counter})
    #jsonData = json.dumps({"world": worldData})
    resp.set_data(jsonData)
    return resp

@app.route("/entity/<entity>")
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    # Took this from my assignment 4
    resp = Response(status=200)
    resp.set_data(json.dumps(myWorld.get(entity)))
    return resp


@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    # Took this from my assignment 4
    myWorld.clear()
    resp = Response(status=200)
    return resp


if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
