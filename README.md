# botd
Simple robot controller framework for Raspberry Pi based robots

## Dependancies
Base dependancies include `python3` and the `requests` library.
For the keyboard "virtual controller" python3-keyboard is required.
For camera support, python3-opencv is required.
For robots, the default control scheme assumes use of the Raspberry Pi's GPIO module.

## Example:
This is an example of how to connect our favourite robot (Sherbert Lemon) to a laptop running both a server and a virtual controller. You can tweak the sherbert_lemon.json config file for your own robots.

On the laptop:
```
./botd_server.py
```
...and in a seperate window after...
```
./botd_client.py --remote 127.0.0.1:8080 virtual_controller.json --port 8082
```

NOTE: `--port` is only required when running both a client *and* server on the same machine! 8080 is the default port for both. This behaviour may change in future releases.

On the robot:
```
./botd_client.py --remote 192.168.1.88:8080 sherbert_lemon.json
```

NOTE: `192.168.1.88` should be replaced with the appropriate IP address of the botd *server*. `8080` is the default server port, but you may choose to change it using both the `--port <port>` directive and this `:<port>` on every client.
