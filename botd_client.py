#!/bin/python3

from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import json
from io import BytesIO
import re
import sys
import os
import base64
import requests
import threading

#define global variables
current_order = None
bot_definition = None
video_devices = {}
video_buffers = {}


class BotClient(threading.Thread):
    #initialise BotClient
    def __init__(self, thread_name, thread_ID):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.thread_ID = thread_ID
 
        # helper function to execute the threads
    def run(self):
        global current_order
        global bot_definition
        global video_devices
        global video_buffers
        time.sleep(1)
        print("Connecting to server @ %s" % (remote_server))
        remote_server_base_uri = "http://" + remote_server
        bot_definition["port"] = local_server_port
        request = requests.post(url = remote_server_base_uri + "/register", json = bot_definition)
        data = request.json()
        #print(data)
        
        
        if (bot_definition["type"] == "CONTROLLER"):
            print("Setting remote to bot0")
            bot_definition["remote_bot_id"] = "bot0"
        
        current_order = None
        
        while True:

            if not (current_order == None):
                #if current_order has expired, set current_order to None
                if (current_order["expiry"] < time.time()):
                    current_order = None
                    #Set all actuators pins GPIOs to low
                    for actuator in bot_definition["actuators"]:
                        for pin in actuator["motor_pins"]:
                            GPIO.output(actuator["motor_pins"][pin], GPIO.LOW)
                else:
                    output_motor_levels = {}
                    
                    for actuator in bot_definition["actuators"]:
                        output_motor_levels[actuator["name"]] = 0
                    print(current_order)
                    if "x_vel" in current_order:
                        for motor in bot_definition["intents"]["x"]:
                            output_motor_levels[motor] += bot_definition["intents"]["x"][motor] * current_order["x_vel"]
                    if "y_vel" in current_order:
                        print("MOVE Y")
                    if "yaw_vel" in current_order:
                        for motor in bot_definition["intents"]["yaw"]:
                            output_motor_levels[motor] += bot_definition["intents"]["yaw"][motor] * current_order["yaw_vel"]
                    #print(output_motor_levels)
                    
                    for actuator in bot_definition["actuators"]:
                        if actuator["type"] == "BRUSHED":
                            if output_motor_levels[actuator["name"]] > 0.1:
                                GPIO.output(actuator["motor_pins"]["cw"], GPIO.HIGH)
                                GPIO.output(actuator["motor_pins"]["ccw"], GPIO.LOW)
                            elif output_motor_levels[actuator["name"]] < -0.1:
                                GPIO.output(actuator["motor_pins"]["cw"], GPIO.LOW)
                                GPIO.output(actuator["motor_pins"]["ccw"], GPIO.HIGH)
                            else:
                                GPIO.output(actuator["motor_pins"]["cw"], GPIO.LOW)
                                GPIO.output(actuator["motor_pins"]["ccw"], GPIO.LOW)
            #
            if "cameras" in bot_definition:
                for camera in bot_definition["cameras"]:
                    if video_devices[camera["name"]].isOpened():
                        ret, frame = video_devices[camera["name"]].read()
                        #cv2.imshow("uwu", frame)
                        #cv2.waitKey()
                        
                        #cv2.imwrite("test.jpg", frame)
                        
                        frame_encode = cv2.imencode(".jpg", frame)[1]
                        data_encode = numpy.array(frame_encode)
                        byte_encode = data_encode.tobytes()
                        video_buffers[camera["name"]] = byte_encode
                    else:
                        print("COULD NOT READ CAMERA (NOT OPENED)")
            time.sleep(0.1)
            
        #print(str(self.thread_name) +" "+ str(self.thread_ID));
        
class BotServerHost(threading.Thread):
    def __init__(self, thread_name, thread_ID):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.thread_ID = thread_ID
 
        # helper function to execute the threads
    def run(self):
        global current_order
        global bot_definition
        client_thread = BotClient("main_client", 128);
        client_thread.start()
        
        web_server = HTTPServer((host_name, local_server_port), BotServer)
        if host_name == "":
            print("Client responder starting on port %s" % (local_server_port))
        else:
            print("Client responder starting http://%s:%s" % (host_name, local_server_port))
        try:
            web_server.serve_forever()
        except KeyboardInterrupt:
            pass
        web_server.server_close()
        print("Client stopped.")
        

class BotServer(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return
    
    def do_POST(self):
        global current_order
        global bot_definition
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
        elif (path_components[0] == "cmd"):
            #print("INTENT:")
            #print(body)
            self.send_response(200)
            self.end_headers()
            reply_body = json.dumps({
                    "status": "OK",
                    "intent": body
                }, indent=4)
            self.wfile.write((reply_body + "\n").encode("utf-8"))
            
            current_order = body
            current_order["expiry"] = current_order["expiry"] + time.time()
            
            ## TODO : PARSE INTENT
        else:
            self.do_GET()
        
    def do_PUT(self):
        global current_order
        global bot_definition
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
        global current_order
        global bot_definition
        global video_buffers
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
        elif (re.compile("^camera[0-9]+$").match(path_components[0])):
            if (len(path_components) >= 2):
                if (path_components[1] == "latest.jpg"):
                    cameraidx = int(re.search(r'\d{0,3}$', path_components[0]).group())
                    self.send_response(200)
                    self.end_headers()
                    reply_body = bytes(video_buffers[bot_definition["cameras"][cameraidx]["name"]])
                    self.wfile.write(reply_body)
                else:
                    self.send_response(404)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    reply_body = json.dumps({
                        "status": "ENDPOINT_NOT_FOUND",
                        "error_at": path_components[1]
                    }, indent=4)
                    self.wfile.write((reply_body + "\n").encode("utf-8"))
            else:
                cameraidx = int(re.search(r'\d{0,3}$', path_components[0]).group())
                self.send_response(200)
                self.end_headers()
                try:
                    reply_body = json.dumps({
                            "status": "OK",
                            "camera_index": cameraidx,
                            "camera_name": bot_definition["cameras"][cameraidx]["name"],
                            "buffer": base64.b64encode(video_buffers[bot_definition["cameras"][cameraidx]["name"]]).decode("utf-8") 
                        }, indent=4)
                except IndexError:
                    reply_body = json.dumps({
                            "status": "INVALID_CAMERA_INDEX",
                            "camera_index": cameraidx
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
    config_file = None
    local_server_port = 8081
    for arg in sys.argv:
        if switch_name == None:
            if (arg.startswith("-")):
                if (arg.startswith("--")):
                    if (arg == "--port"):
                        switch_name = "PORT"
                    if (arg == "--remote"):
                        switch_name = "REMOTE_SERVER"
                else:
                    if (arg == "-p"):
                        switch_name = "PORT"
                    if (arg == "-r"):
                        switch_name = "REMOTE_SERVER"
            else:
                config_file = arg
        elif switch_name == "PORT":
            local_server_port = int(arg)
            switch_name = None
        elif switch_name == "REMOTE_SERVER":
            remote_server = arg
            switch_name = None
        elif switch_name == "PYFILE":
            switch_name = None
        else:
            print("Argument parse error!")
    if remote_server == None:
        print("No remote server supplied!")
    elif config_file == None:
        print("No config file supplied!")
        print("python3 botd_client.py --remote <ip_address>[:port] <config_file>")
    else:
        f = open(config_file)
        bot_definition = json.load(f)
        f.close()
        
        server_thread = BotServerHost("main_server", 64);
        server_thread.start()
        
        if (bot_definition["type"] == "BOT"):
            if "cameras" in bot_definition:
                import cv2
                import numpy
                for camera in bot_definition["cameras"]:
                    videodev = os.readlink(camera["path"]).split("/")[-1]
                    videodevidx = re.search(r'\d{0,3}$', videodev).group()
                    videodevpath = "/dev/video" + str(videodevidx)
                    print("Camera %s at OpenCV path %s" % (camera["name"], videodevpath))
                    video_buffers[camera["name"]] = bytearray()
                    video_devices[camera["name"]] = cv2.VideoCapture(videodevpath)
                    if not video_devices[camera["name"]].isOpened():
                        print("FAILED TO OPEN CAMERA")
            if (bot_definition["control_scheme"] == "TELEMETRY_ONLY"):
                print("Telemetry-only robot")
            if (bot_definition["control_scheme"] == "RPI_ONBOARD_GPIO"):
                try:
                    import RPi.GPIO as GPIO
                    GPIO.setmode(GPIO.BOARD)
                    #GPIO.setup(36, GPIO.OUT)
                    #GPIO.setup(38, GPIO.OUT)
                    #GPIO.setup(40, GPIO.OUT)
                    for actuator in bot_definition["actuators"]:
                        for pin in actuator["motor_pins"]:
                            print("Activating motor pin %s" % (actuator["motor_pins"][pin]))
                            GPIO.setup(actuator["motor_pins"][pin], GPIO.OUT)
                            GPIO.output(actuator["motor_pins"][pin], GPIO.LOW)
                        #for pin in actuator["encoder_pins"]:
                        #    print("Activating encoder pin %s" % (pin))
                        #    GPIO.setup(pin, GPIO.INPUT)
                        
                    bot_definition["motors_active"] = True
                except ImportError:
                    print("CANNOT START RPI CONTROL WITHOUT RPI MODULE")
                    print("Try: pip install RPi.GPIO")
                    
        elif (bot_definition["type"] == "CONTROLLER"):
            if (bot_definition["control_scheme"] == "VIRTUAL_KEYBOARD"):
                try:
                    import keyboard
                    print("Starting virtual controller!")
                    while True:
                        key = keyboard.read_key()
                        intents = []
                        expiry = 0
                        for keymap in bot_definition["keymap"]:
                            if (keymap["key"] == key):
                                intents = intents + keymap["intents"]
                                if expiry < keymap["expiry"]:
                                    expiry = keymap["expiry"]
                        built_intent = {"expiry": expiry}
                        send_intent = False
                        for intent in intents:
                            send_intent = True
                            if intent["axis"] in built_intent:
                                built_intent[intent["axis"]] = intent["rate"] + built_intent[intent["axis"]]
                            else:
                                built_intent[intent["axis"]] = intent["rate"]
                        
                        if send_intent:
                            if "remote_bot_id" in bot_definition:
                                remote_server_base_uri = "http://" + remote_server
                                bot_definition["port"] = local_server_port
                                request = requests.post(url = remote_server_base_uri + "/" + bot_definition["remote_bot_id"] + "/cmd", json = built_intent)
                                data = request.json()
                            else:
                                print("NO REMOTE BOT")
                                
                            
                                
                except ImportError:
                    print("CANNOT START VIRTUAL CONTROLLER WITHOUT KEYBOARD MODULE")
                    print("Try: pip install keyboard")
                    print("Note: On linux this script requires root")
                
            
        
        
