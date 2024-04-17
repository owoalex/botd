#!/bin/python3

from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import json
from io import BytesIO
import re
import sys
import copy
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
        #bot_definition["port"] = local_server_port
        request = requests.post(url = remote_server_base_uri + "/register", json = bot_definition)
        data = request.json()
        #print(data)
        
        
        if (bot_definition["type"] == "CONTROLLER"):
            if not "remote_bot_id" in bot_definition:
                print("Bot ID not set, defaulting to bot0")
                bot_definition["remote_bot_id"] = "bot0"
            print("Connecting to " + bot_definition["remote_bot_id"] + " (use flag --bot <bot_id> to change this)")
        
        current_order = None
        
        while True:

            if not (current_order == None):
                #if current_order has expired, set current_order to None
                output_motor_levels = {}
                
                if (current_order["expiry"] < time.time()):
                    current_order = None
                    
                    for actuator in bot_definition["actuators"]:
                        output_motor_levels[actuator["name"]] = 0
                    #Set all actuators pins GPIOs to low
                    #for actuator in bot_definition["actuators"]:
                    #    
                    #    for pin in actuator["motor_pins"]:
                    #        GPIO.output(actuator["motor_pins"][pin], GPIO.LOW)
                else:
                    output_motor_levels = {}
                    
                    
                    print(current_order)
                    if "x_vel" in current_order:
                        for motor in bot_definition["intents"]["x"]:
                            if not motor in output_motor_levels:
                                output_motor_levels[motor] = 0
                            output_motor_levels[motor] += bot_definition["intents"]["x"][motor] * current_order["x_vel"]
                    if "y_vel" in current_order:
                        print("MOVE Y")
                    if "yaw_vel" in current_order:
                        for motor in bot_definition["intents"]["yaw"]:
                            if not motor in output_motor_levels:
                                output_motor_levels[motor] = 0
                            output_motor_levels[motor] += bot_definition["intents"]["yaw"][motor] * current_order["yaw_vel"]
                    #print(output_motor_levels)
                    
                for actuator in bot_definition["actuators"]:
                    if actuator["name"] in output_motor_levels:
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
                        elif actuator["type"] == "ABSTRACTED_HTTP":
                            int_level = str(round(output_motor_levels[actuator["name"]]))
                            float_level = str(output_motor_levels[actuator["name"]])
                            remote_bot = bot_definition["http_middleware_address"]
                            print("Sending abstracted HTTP instruction to %s" % (remote_bot))
                            parsed_path = actuator["endpoint"].replace("$int;", int_level).replace("$float;", float_level)
                            remote_bot_uri = "http://" + remote_bot + "/" + parsed_path
                            request = requests.get(url = remote_bot_uri)
                            
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
        
        
        if bot_definition["hostname"] == "":
            print("Client responder starting on port %s" % (bot_definition["port"]))
        else:
            print("Client responder starting http://%s:%s" % (bot_definition["hostname"], bot_definition["port"]))
            
        web_server = HTTPServer((bot_definition["hostname"], bot_definition["port"]), BotServer)
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
    import random
    
    switch_name = "PYFILE"
    host_name = ""
    remote_server = None
    remote_bot = None
    config_file = None
    local_server_port = random.randint(38000, 38999)
    for arg in sys.argv:
        if switch_name == None:
            if (arg.startswith("-")):
                if (arg.startswith("--")):
                    if (arg == "--port"):
                        switch_name = "PORT"
                    if (arg == "--remote"):
                        switch_name = "REMOTE_SERVER"
                    if (arg == "--bot"):
                        switch_name = "REMOTE_BOT"
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
        elif switch_name == "REMOTE_BOT":
            remote_bot = "bot" + arg
            switch_name = None
        elif switch_name == "PYFILE":
            switch_name = None
        else:
            print("Argument parse error!")
    if remote_server == None:
        print("No remote server supplied!")
        print("python3 botd_client.py --remote <ip_address>[:port] <config_file>")
    elif config_file == None:
        print("No config file supplied!")
        print("python3 botd_client.py --remote <ip_address>[:port] <config_file>")
    else:
        f = open(config_file)
        bot_definition = json.load(f)
        f.close()
        
        bot_definition["port"] = local_server_port
        bot_definition["hostname"] = host_name
        
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
            if (bot_definition["control_scheme"] == "SIMPLE_HTTP_SERVER"):
                print("Simple HTTP Server")
            if (bot_definition["control_scheme"] == "TELEMETRY_ONLY"):
                print("Telemetry-only robot")
            if (bot_definition["control_scheme"] == "MIXED"):
                print("Mixed control robot")
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
                    
            #print(bot_definition)
            server_thread = BotServerHost("main_server", 64);
            server_thread.start()
        elif (bot_definition["type"] == "CONTROLLER"):
            if not remote_bot == None:
                bot_definition["remote_bot_id"] = remote_bot
            server_thread = BotServerHost("main_server", 64);
            server_thread.start()
            
            
            if (bot_definition["control_scheme"] == "KEYBOARD_ROOT"):
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
                                request = requests.post(url = remote_server_base_uri + "/" + bot_definition["remote_bot_id"] + "/cmd", json = built_intent)
                                data = request.json()
                            else:
                                print("NO REMOTE BOT")
                                
                            
                                
                except ImportError:
                    print("CANNOT START VIRTUAL CONTROLLER WITHOUT KEYBOARD MODULE")
                    print("Try: pip install keyboard")
                    print("Note: On linux this script requires root")
                    quit()
            elif (bot_definition["control_scheme"] == "PYGLET_CONTROLLER"):
                try:
                    import pyglet

                    from pyglet.shapes import Circle, Rectangle, Arc


                    window = pyglet.window.Window(720, 480)
                    batch = pyglet.graphics.Batch()


                    @window.event
                    def on_draw():
                        window.clear()
                        batch.draw()


                    class ControllerDisplay:
                        """A class to visualize all the Controller inputs."""

                        def __init__(self, batch):

                            self.label = pyglet.text.Label("No Controller connected.", x=10, y=window.height - 20,
                                                        multiline=True, width=720, batch=batch)

                            self.left_trigger = Rectangle(70, 310, 40, 10, batch=batch)
                            self.right_trigger = Rectangle(610, 310, 40, 10, batch=batch)
                            self.d_pad = Rectangle(280, 185, 10, 10, batch=batch)

                            self.left_stick = Arc(180, 240, 20, batch=batch)
                            self.left_stick_label = pyglet.text.Label("(0.00, 0.00)", x=180, y=50, anchor_x='center', batch=batch)
                            self.left_stick_bar_x = Rectangle(180, 30, 0, 10, batch=batch)
                            self.left_stick_bar_y = Rectangle(180, 10, 0, 10, batch=batch)

                            self.right_stick = Arc(540, 240, 20, batch=batch)
                            self.right_stick_label = pyglet.text.Label("(0.00, 0.00)", x=540, y=50, anchor_x='center', batch=batch)
                            self.right_stick_bar_x = Rectangle(540, 30, 0, 10, batch=batch)
                            self.right_stick_bar_y = Rectangle(540, 10, 0, 10, batch=batch)

                            self.l_outline1 = Arc(180, 240, 75, color=(44, 44, 44), batch=batch)
                            self.l_outline2 = Arc(285, 190, 35, color=(44, 44, 44), batch=batch)
                            self.r_outline1 = Arc(540, 240, 75, color=(44, 44, 44), batch=batch)
                            self.r_outline2 = Arc(435, 190, 35, color=(44, 44, 44), batch=batch)

                            self.buttons = {'a': Circle(435, 170, 9, color=(124, 178, 232), batch=batch),
                                            'b': Circle(455, 190, 9, color=(255, 102, 102), batch=batch),
                                            'x': Circle(415, 190, 9, color=(255, 105, 248), batch=batch),
                                            'y': Circle(435, 210, 9, color=(64, 226, 160), batch=batch),
                                            'leftshoulder': Rectangle(70, 290, 40, 10, batch=batch),
                                            'rightshoulder': Rectangle(610, 290, 40, 10, batch=batch),
                                            'start': Circle(390, 240, 9, batch=batch),
                                            'guide': Circle(360, 240, 9, color=(255, 255, 100), batch=batch),
                                            'back': Circle(330, 240, 9, batch=batch),
                                            'leftstick': Circle(180, 240, 9, batch=batch),
                                            'rightstick': Circle(540, 240, 9, batch=batch)}
                            
                            self.raw_values = {
                                    "left_stick_x": 0,
                                    "left_stick_y": 0,
                                    "right_stick_x": 0,
                                    "right_stick_y": 0,
                                    "left_trigger": 0,
                                    "right_trigger": 0
                                }

                            for button in self.buttons.values():
                                button.visible = False

                        def on_button_press(self, controller, button_name):
                            if button := self.buttons.get(button_name, None):
                                button.visible = True

                            controller.rumble_play_weak(1.0, 0.1)

                        def on_button_release(self, controller, button_name):
                            if button := self.buttons.get(button_name, None):
                                button.visible = False

                        def on_dpad_motion(self, controller, dpleft, dpright, dpup, dpdown):
                            position = [280, 185]
                            if dpup:
                                position[1] += 25
                            if dpdown:
                                position[1] -= 25
                            if dpleft:
                                position[0] -= 25
                            if dpright:
                                position[0] += 25
                            self.d_pad.position = position

                        def on_stick_motion(self, controller, stick, xvalue, yvalue):
                            if stick == "leftstick":
                                self.raw_values["left_stick_x"] = xvalue
                                self.raw_values["left_stick_y"] = yvalue
                                self.left_stick.position = 180+xvalue*50, 240+yvalue*50
                                self.left_stick_label.text = f"({xvalue:.2f}, {yvalue:.2f})"
                                self.left_stick_bar_x.width = xvalue * 100
                                self.left_stick_bar_y.width = yvalue * 100
                            elif stick == "rightstick":
                                self.raw_values["right_stick_x"] = xvalue
                                self.raw_values["right_stick_y"] = yvalue
                                self.right_stick.position = 540+xvalue*50, 240+yvalue*50
                                self.right_stick_label.text = f"({xvalue:.2f}, {yvalue:.2f})"
                                self.right_stick_bar_x.width = xvalue * 100
                                self.right_stick_bar_y.width = yvalue * 100

                        def on_trigger_motion(self, controller, trigger, value):
                            if trigger == "lefttrigger":
                                self.raw_values["left_trigger"] = value
                                self.left_trigger.y = 310 + (value*50)
                                #controller.rumble_play_weak(value, duration=5)
                            elif trigger == "righttrigger":
                                self.raw_values["right_trigger"] = value
                                self.right_trigger.y = 310 + (value*50)
                                #controller.rumble_play_strong(value, duration=5)


                    controller_display = ControllerDisplay(batch=batch)


                    def on_connect(controller):
                        controller.open()
                        controller.rumble_play_weak(1.0, 0.1)
                        controller_display.label.text = f"Detected: {controller.name}\nController GUID: {controller.guid}"
                        controller.push_handlers(controller_display)


                    def on_disconnect(controller):
                        controller_display.label.text = "No Controller connected."
                        controller.remove_handlers(controller_display)


                    # ControllerManager instance to handle hot-plugging:
                    controller_manager = pyglet.input.ControllerManager()
                    controller_manager.on_connect = on_connect
                    controller_manager.on_disconnect = on_disconnect

                    # Handle already connected controller:
                    if controllers := controller_manager.get_controllers():
                        on_connect(controllers[0])
                        
                    def update(dt):
                        intents = []
                        expiry = dt + 0.001
                        
                        built_intent = {}
                        if "default_intent" in bot_definition:
                            built_intent = copy.deepcopy(bot_definition["default_intent"])
                        #built_intent["expiry"] = expiry
                        send_intent = False
                        for keymap in bot_definition["keymap"]:
                            if keymap["input"] in controller_display.raw_values:
                                intentval = keymap["intents"]
                                for i in range(0,len(intentval)):
                                    intentval[i]["value"] = controller_display.raw_values[keymap["input"]]
                                intents = intents + intentval
                                if expiry < keymap["expiry"]:
                                    expiry = keymap["expiry"]
                        built_intent["expiry"] = expiry
                        for intent in intents:
                            send_intent = True
                            active = True
                            if "dead_below" in intent:
                                if intent["value"] < intent["dead_below"]:
                                    active = False
                            if "dead_above" in intent:
                                if intent["value"] > intent["dead_above"]:
                                    active = False
                            if active:
                                val = (intent["mult"] * intent["value"]) + intent["offset"]
                                if intent["axis"] in built_intent:
                                    built_intent[intent["axis"]] = val + built_intent[intent["axis"]]
                                else:
                                    built_intent[intent["axis"]] = val
                        
                        if "remote_bot_id" in bot_definition:
                            remote_server_base_uri = "http://" + remote_server
                            request = requests.post(url = remote_server_base_uri + "/" + bot_definition["remote_bot_id"] + "/cmd", json = built_intent)
                            data = request.json()
                        else:
                            print("NO REMOTE BOT")

                    pyglet.clock.schedule_interval(update, 0.1)

                    pyglet.app.run()
                except:
                    print("ERROR!!!")
                    e = sys.exc_info()
                    print(e)
            elif (bot_definition["control_scheme"] == "KEYBOARD"):
                try:
                    import sys
                    import tty
                    import termios
                    while True:
                        fd = sys.stdin.fileno()
                        old_settings = termios.tcgetattr(fd)
                        try:
                            tty.setraw(sys.stdin.fileno())
                            ch = sys.stdin.read(1)
                        finally:
                            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                        if ch.encode("utf-8").hex() == "03":
                            # horrible bodge
                            quit()
                            raise KeyboardInterrupt
                        
                        print(ch.encode("utf-8").hex())
                        
                        key=ch
                        
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
                                request = requests.post(url = remote_server_base_uri + "/" + bot_definition["remote_bot_id"] + "/cmd", json = built_intent)
                                data = request.json()
                            else:
                                print("NO REMOTE BOT")
                                
   
                except KeyboardInterrupt:
                    print("Keyboard interrupt, bailing out")
                                
                
            
        
        
