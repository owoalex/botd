#!/bin/python3

from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import json
from io import BytesIO
import re

bot_list = []
controller_list = []

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
    hostName = ""
    serverPort = 8080
    webServer = HTTPServer((hostName, serverPort), BotServer)
    print("Server started http://%s:%s" % (hostName, serverPort))
    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    webServer.server_close()
    print("Server stopped.")
