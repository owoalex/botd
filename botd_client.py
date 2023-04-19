#!/bin/python3

from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import json
from io import BytesIO
import re
import sys
import requests
import threading

class BotClient(threading.Thread):
    def __init__(self, thread_name, thread_ID):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.thread_ID = thread_ID
 
        # helper function to execute the threads
    def run(self):
        time.sleep(1)
        print("Connecting to server @ %s" % (remote_server))
        remote_server_base_uri = "http://" + remote_server
        params = {"type": "BOT", "port": local_server_port}
        request = requests.post(url = remote_server_base_uri + "/register", json = params)
        data = request.json()
        print(data)
        
        #print(str(self.thread_name) +" "+ str(self.thread_ID));

class BotServer(BaseHTTPRequestHandler):
    def do_POST(self):
        path_components = self.path.split("/")
        if (len(path_components) >= 1):
            if (path_components[0] == ""):
                path_components.pop(0)
        if (len(path_components) == 0):
            path_components.push("")
            
        if (self.headers['Content-Length'] == None):
            self.do_GET()
            return
        
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length).decode("utf-8")
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
        
        if (re.compile("^motor[0-9]+$").match(path_components[0])):
            self.send_response(200)
            self.end_headers()
            reply_body = json.dumps({
                    "status": "OK",
                    "request": body
                }, indent=4)
            self.wfile.write((reply_body + "\n").encode("utf-8"))
        elif (re.compile("^camera[0-9]+$").match(path_components[0])):
            self.send_response(200)
            self.end_headers()
            reply_body = json.dumps({
                    "status": "OK",
                    "request": body
                }, indent=4)
            self.wfile.write((reply_body + "\n").encode("utf-8"))
        else:
            self.do_GET()
        
    def do_PUT(self):
        path_components = self.path.split("/")
        if (len(path_components) >= 1):
            if (path_components[0] == ""):
                path_components.pop(0)
        if (len(path_components) == 0):
            path_components.push("")
        
        if (re.compile("^screen[0-9]+$").match(path_components[0])):
            timestamp = time.time()
            filename = "display/" + path_components[1] + "-" + str(timestamp) + ".jpeg"

            file_length = int(self.headers['Content-Length'])
            with open(filename, 'wb') as output_file:
                output_file.write(self.rfile.read(file_length))
            self.send_response(201, "Created")
            self.end_headers()
            reply_body = json.dumps({
                "status": "OK"
            }, indent=4)
            self.wfile.write((reply_body + "\n").encode("utf-8"))
        else:
            self.send_response(404)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            reply_body = json.dumps({
                "status": "INVALID_PUT_LOCATION"
            }, indent=4)
            self.wfile.write((reply_body + "\n").encode("utf-8"))
    
    def do_GET(self):
        path_components = self.path.split("/")
        if (len(path_components) >= 1):
            if (path_components[0] == ""):
                path_components.pop(0)
        if (len(path_components) == 0):
            path_components.push("")
            
        if (path_components[0] == ""):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            reply_body = json.dumps({
                "status": "OK"
            }, indent=4)
            self.wfile.write((reply_body + "\n").encode("utf-8"))
        else:
            self.send_response(404)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            reply_body = json.dumps({
                "status": "ENDPOINT_NOT_FOUND"
            }, indent=4)
            self.wfile.write((reply_body + "\n").encode("utf-8"))
            

if __name__ == "__main__":  
    switch_name = "PYFILE"
    host_name = ""
    remote_server = None
    local_server_port = 8081
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
    if remote_server == None:
        print("No remote server supplied!")
    else:
        client_thread = BotClient("main_client", 128);
        web_server = HTTPServer((host_name, local_server_port), BotServer)
        if host_name == "":
            print("Client responder starting on port %s" % (local_server_port))
        else:
            print("Client responder starting http://%s:%s" % (host_name, local_server_port))
        client_thread.start()
        try:
            web_server.serve_forever()
        except KeyboardInterrupt:
            pass
        web_server.server_close()
        print("Client stopped.")
