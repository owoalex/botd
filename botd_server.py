#!/bin/python3

from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import json
from io import BytesIO
import re
import os
import sys
import requests
import math
import threading

bot_list = []
controller_list = []
config = {
        "disconnection_time": 5
    }

class ClientMonitor(threading.Thread):
    def __init__(self, thread_name):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
 
        # helper function to execute the threads
    def run(self):
        global bot_list
        global controller_list
        global config
        
        time.sleep(1)
        while (True):
            time.sleep(1)
            #print("Polling clients")
            for bot in bot_list:
                if bot["connected"]:
                    try:
                        remote_server_base_uri = "http://" + bot["ip"] + ":" + str(bot["port"])
                        params = {}
                        request = requests.get(url = remote_server_base_uri + "/", params = params)
                        data = request.json()
                        #print(data)
                        bot["last_status"] = data
                        bot["last_status_at"] = time.time()
                    except:
                        ttd = (bot["last_status_at"] + config["disconnection_time"]) - time.time()
                        if ttd > 0.5:
                            print("Bot @ %s is not responding, will disconnect in %s seconds" % ((bot["ip"] + ":" + str(bot["port"])), str(round(ttd))))
                        else:
                            print("Disconnecting unresponsive robot @ %s :(" % (bot["ip"] + ":" + str(bot["port"])))
                            bot["connected"] = False
            for controller in controller_list:
                if controller["connected"]:
                    try:
                        remote_server_base_uri = "http://" + controller["ip"] + ":" + str(controller["port"])
                        params = {}
                        request = requests.get(url = remote_server_base_uri + "/", params = params)
                        data = request.json()
                        #print(data)
                        controller["last_status"] = data
                        controller["last_status_at"] = time.time()
                    except:
                        ttd = (controller["last_status_at"] + config["disconnection_time"]) - time.time()
                        if ttd > 0.5:
                            print("Controller @ %s is not responding, will disconnect in %s seconds" % ((controller["ip"] + ":" + str(controller["port"])), str(round(ttd))))
                        else:
                            print("Disconnecting unresponsive controller @ %s :/" % (controller["ip"] + ":" + str(controller["port"])))
                            controller["connected"] = False

class BotServer(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    #process info given to pi from client
    #do_POST responsibilities
    #   configuration
    #   

    def do_POST(self):
        path_components = self.path.split("/")
        if (len(path_components) >= 1):
            if (path_components[0] == ""):
                path_components.pop(0)
        if (len(path_components) == 0):
            path_components.push("")

        #if has no content, treat this post request as a get 
        if (self.headers['Content-Length'] == None):
            self.do_GET()
            return

        #get content length as bytes
        content_length = int(self.headers['Content-Length'])
        #get content of post request in a variable 
        body = self.rfile.read(content_length).decode("utf-8")
        #try convert body from JSON to a generic dictionary. If fails, send back a message saying u fucked up
        try:
            body = json.loads(body)
        except ValueError:  # includes simplejson.decoder.JSONDecodeError
            self.send_response(401)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            reply_body = json.dumps({
                "status": "INVALID_JSON_PAYLOAD"
            }, indent=4)
            self.wfile.write((reply_body + "\n").encode("utf-8"))
            return
        
        #if thats all worked then we start processing it:
        
        #if the request's first part says register then register the contents
        if (path_components[0] == "register"):
            error = None
            
            device_definition = body
            device_definition["ip"] = self.client_address[0]
            device_definition["connected"] = True
            
            idx = -1
            
            if (error == None):
                if not ("port" in body):
                    error = "MISSING_DEVICE_PORT"
            
            if (error == None):
                if ("type" in body):
                    if (body["type"] == "BOT"):
                        bot_list.append(device_definition)
                        idx = len(bot_list) - 1
                        print("New robot (bot%s) @ %s :D" % (str(idx), (device_definition["ip"] + ":" + str(device_definition["port"]))))
                    elif (body["type"] == "CONTROLLER"):
                        controller_list.append(device_definition)
                        idx = len(controller_list) - 1
                        print("New controller (controller%s) @ %s :>" % (str(idx), (device_definition["ip"] + ":" + str(device_definition["port"]))))
                    else:
                        error = "INVALID_DEVICE_TYPE"
                else:
                    error = "MISSING_DEVICE_TYPE"
                    
            
            if (error == None):
                self.send_response(200)
                self.end_headers()
                reply_body = json.dumps({
                        "status": "OK",
                        "request": body,
                        "device_index": idx
                    }, indent=4)
                self.wfile.write((reply_body + "\n").encode("utf-8"))
            else:
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                reply_body = json.dumps({
                    "status": error
                }, indent=4)
                self.wfile.write((reply_body + "\n").encode("utf-8"))

        #if first part of path references a bot then ...
        elif (re.compile("^bot[0-9]+$").match(path_components[0])):
            if (len(path_components) > 1):

                #if second part is cmd then they're sending a command, we process that
                if (path_components[1] == "cmd"):
                    bot_number = int(path_components[0][3:])
                    destination_definition = bot_list[bot_number]
                    #print(destination_definition["ip"])
                    #print(destination_definition["port"])
                    self.send_response(200)
                    self.end_headers()
                    reply_body = json.dumps({
                            "status": "OK",
                            "intent": body
                        }, indent=4)
                    self.wfile.write((reply_body + "\n").encode("utf-8"))
                    
                    remote_bot_base_uri = "http://" + destination_definition["ip"] + ":" + str(destination_definition["port"])
                    bot_request = requests.post(url = remote_bot_base_uri + "/cmd", json = body)
                    ret_data = bot_request.json()

                #if second part isnt a command then assume they're just requesting status and return that
            else:
                self.send_response(200)
                self.end_headers()
                reply_body = json.dumps({
                        "status": "OK",
                        "request": body
                    }, indent=4)
                self.wfile.write((reply_body + "\n").encode("utf-8"))

        #same as before but ask for data of a controller instead of a bot
        elif (re.compile("^controller[0-9]+$").match(path_components[0])):
            self.send_response(200)
            self.end_headers()
            reply_body = json.dumps({
                    "status": "OK",
                    "request": body
                }, indent=4)
            self.wfile.write((reply_body + "\n").encode("utf-8"))
        
        #if its none of those then assume its a get request
        else:
            self.do_GET()
        

    #for processing put requests (uploading files e.g. photos for a video feed)
    def do_PUT(self):
        path_components = self.path.split("/")
        if (len(path_components) >= 1):
            if (path_components[0] == ""):
                path_components.pop(0)
        if (len(path_components) == 0):
            path_components.push("")
        
        #if start of request lists a bot then they're identifiying themselves as a bot, use this data to...
        if (re.compile("^bot[0-9]+$").match(path_components[0])):

            #if second part says camera then they're uploading camera data, process that
            #this is processed by just writing it to a file for later use
            if (re.compile("^cam[0-9]+$").match(path_components[1])):
                timestamp = time.time()
                filename = "camera/" + path_components[1] + "-" + str(timestamp) + ".jpeg"

                file_length = int(self.headers['Content-Length'])
                with open(filename, 'wb') as output_file:
                    output_file.write(self.rfile.read(file_length))
                self.send_response(201, "Created")
                self.end_headers()
                reply_body = json.dumps({
                    "status": "OK"
                }, indent=4)
                self.wfile.write((reply_body + "\n").encode("utf-8"))
            
            #if second part of request isnt recognised then reply with error
            else:
                self.send_response(404)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                reply_body = json.dumps({
                    "status": "INVALID_BOT_ENDPOINT"
                }, indent=4)
                self.wfile.write((reply_body + "\n").encode("utf-8"))
        #if part of first request isnt a bot then return error
        else:
            self.send_response(404)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            reply_body = json.dumps({
                "status": "INVALID_PUT_LOCATION"
            }, indent=4)
            self.wfile.write((reply_body + "\n").encode("utf-8"))
    
    #processing get requests, requesting data innit fam
    def do_GET(self):
        path_components = self.path.split("/")
        if (len(path_components) >= 1):
            if (path_components[0] == ""):
                path_components.pop(0)
        if (len(path_components) == 0):
            path_components.push("")
            
        #if first part of request is empty then just send basic response "I got your request, Im working"
        if (path_components[0] == ""):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            reply_body = json.dumps({
                "status": "OK"
            }, indent=4)
            self.wfile.write((reply_body + "\n").encode("utf-8"))
        
        #if first part says devices then return list of devices
        elif (path_components[0] == "devices"):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            reply_body = json.dumps({
                "status": "OK",
                "bots": bot_list,
                "controllers": controller_list
            }, indent=4)
            self.wfile.write((reply_body + "\n").encode("utf-8"))
        
        #if first part is register then throw error because that should be going to POST not GET
        #(could this rerout it to a do_post instead of throwing error?)
        elif (path_components[0] == "register"):
            self.send_response(401)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            reply_body = json.dumps({
                "status": "POST_ONLY_ENDPOINT"
            }, indent=4)
            self.wfile.write((reply_body + "\n").encode("utf-8"))
        
        #if anything else throw error
        else:
            self.send_response(404)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            reply_body = json.dumps({
                "status": "ENDPOINT_NOT_FOUND"
            }, indent=4)
            self.wfile.write((reply_body + "\n").encode("utf-8"))
            

#this part just runs the server and calls the above stuff when the requests come through
if __name__ == "__main__":        
    switch_name = "PYFILE"
    host_name = ""
    local_server_port = 8080
    for arg in sys.argv:
        if switch_name == None:
            if (arg.startswith("-")):
                if (arg.startswith("--")):
                    if (arg == "--port"):
                        switch_name = "PORT"
                else:
                    if (arg == "-p"):
                        switch_name = "PORT"
            else:
                remote_server = arg
        elif switch_name == "PORT":
            local_server_port = int(arg)
            switch_name = None
        elif switch_name == "PYFILE":
            switch_name = None
        else:
            print("Argument parse error!")
    web_server = HTTPServer((host_name, local_server_port), BotServer)
    client_monitor = ClientMonitor("client_monitor");
    if host_name == "":
        print("Host server starting on port %s" % (local_server_port))
    else:
        print("Host server starting http://%s:%s" % (host_name, local_server_port))
    client_monitor.start();
    try:
        web_server.serve_forever()
    except KeyboardInterrupt:
        pass
    web_server.server_close()
    print("Server stopped.")
    os._exit(0)
