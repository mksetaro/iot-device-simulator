# IoT Device Simulator


Python IoT device simulator consisting of an IoT Container running units representing IoT devices defined in a json file (see [iotunits.json](examples/iotunits.json)), a smart elevator and a temperature sensor implementation can be found in the [examples](examples) folder.

## Usage guide - Run examples

Install Python package in virtualenv
```
python3 -m venv venv
source venv/bin/activate
pip install -e <path-to-project-root>
```

Adapt [config.json](iotsim/config/config.json) to your working environment
```
{
    "logger": {
        "file_path": "iot-container.log",
        "verbosity": "DEBUG"
    },
    "client": {
        "id": "test_client",
        "type": "mqtt", #mqtt only client supported atm
        "host": "localhost",
        "port": 1883,
        "root_ca": "",
        "client_certificate": "",
        "client_key": ""
    },
    "pods": {
        "pods_list_file_path": "<path-to-pods-list.json>",
        "pods_py_module_path": "<path-to-pods-py-modules>"
    }
}
```


Run simulator
```
python <path-to-project-root>/iotsim/src/app.py --config <path-to-config.json>
```
if no argument are set the app will make use of the default config-default.json

Run simulator as Docker container
```
docker build -t <image-name> <path-do-dockerfile-parent-folder>
docker run --rm -d --network host --name <container-id> <image-name>
```
Read app log in docker container
```
docker exec -it <container-name> tail -f /workspace/iot-container.log
```

## Implement your own IoT Units

An IoT unit can be anything you wish, the package makes use of [importlib](https://docs.python.org/3/library/importlib.html) to import user defined module at runtime just by declaring them in the iotunits.json.

The Units make use of user defined registers (simulating the volatile memory of the device) to manipulate and share data between control_loop, publishers and subscribers. Register works in a dictionary fashion and the keys and init value must be defined in the json definition of your unit.

```
{
    "name": "iot-unit", #name of the unit
    "control_loop_module": "user-define-unit.control-loop-module", #null if periodic activity is not needed
    "control_loop_sleep_ms": cyle_time, #cycle time of the periodic activity
    "registers": {}, #register
    "publishers": [{...}], #publishers list
    "subscribers": [{...}] #subscribers list
}
```
##### Control loop
Unit package structure

```
|-- user-define-unit/
    |-- __init__.py
    |-- control-loop-module.py
    |-- request-module.py

```
Control loop function must have the signature below:
```
        IoT Unit registers
            |
def run(registers,):
    #TODO Implement your logic
    #registers['key'] = some-value     
```
##### Publishers

Publishers are mapped to a register key and publish the value corresponding to the key.
Two different kind of publishers are available. An IoT unit can have any number of publishers

```
NOTIFICATION #Triggered by some event and publishing a register value (see smart_elevator example)
PERIODIC #Publisher periodically publishing a register value (see temperature_sensor example)
```

Json definition
```
{
    "id": "publisher-id",
    "type": "publisher-type",
    "cycle_time_ms": cycle-time,  #used only by periodic publishers
    "read": "register-key",       #register key accessed by publisher
    "topic": "mqtt-topic"
}
```
##### Subscribers

Subscribers are triggered by a message received on their mqtt-topic and have two-fold usage: write some data received on topic to the register value they're mapped to or trigger a function in a RPC fashion and then notify the results through a NOTIFICATION publisher

```
DATA_WRITE #Used to update the register value they're mapped to(see temperature_sensor example)
REQUEST #Triggers a function and then notifies results through notification publisher (see smart_elevator example)
```

Json definition
```
{
    "id": "subscriber-id",
    "type": "subscriber-type",
    "request_module": "user-define-unit.request-module",    #works like the control loop, declare key-value only for REQUEST subscribers
    "write": "register-key",                                #register key accessed by subscriber when writing data, declare key-value only for DATA_WRITE subscribers
    "notifier": "notifier-publisher-id",                    #publisher id to be used by REQUEST subscriber to notify request results, declare key-value only for REQUEST subscribers
    "topic": "unit/robot_request"                           #mqtt-topic of the subscription
}
```
Request function for **REQUEST** subscribers must have the following signature
```                    
                #IoT Unit registers
                        |         #payload from mqtt topic  
                        |         |         #trigger func for notifier pub 
                        |         |         |
def process_request(registers, payload, notify_func):
    #TODO implementation goes here
    #do something
    #notify_func()
```


## TODO LIST

- [ ] Code clean up
- [ ] Unit testing
- [ ] Improve documentation
- [ ] Improve overall abstraction
- [ ] Improve Python packaging
- [ ] Refactor project as an IoT Container usable also with physical devices
- [ ] Refactor project in order to make use of an arbitrary communication protocol 

## Contributors

* [Michelangelo Setaro](https://github.com/mksetaro) 
  
## Contribution

If you wish to contribute contact:

* Automata Community - automata.community@gmail.com
* Michelangelo Setaro - mksetaro@gmail.com