# Smart Directions: brain
For a brief description of the architecture, please refer to [this](https://github.com/filipkrasniqi/smart-directions-publisher#brief-summary-of-the-architecture).

This code refers to the **brain** and it is written in Python.

## A note: useless code
This repository also contains first attempts of sniffing BLE using python code. In particular, we refer to the **main.py, ble_scanner.py and bl_scanner.py** in the root of the repo.

## Downloading and building
To download and build this repository, you should simply clone the repo and run ```pip install -r requirements.txt```. The keys directory contains certificates in case MQTT is encrypted.

## Used software: tools and libraries
We use [paho-mqtt](https://pypi.org/project/paho-mqtt/) to connect the MQTT client.

## Protocol
Communication among brain, devices, anchors and effectors is done with MQTT. A list of the topics with payload info follows.

### Anchors
- **ble/rssi**: each anchor sends a message of the form <MAC_ADDRESS_RBERRY_PI>$<SNIFFED_MAC_ADDRESS>$<RSSI_VAL>. The brain will store the information associating it to a device. Anchors are not aware of the current activated devices, so they will send rssi values for any sniffed device, regardless of whether such a device is actually using the system (i.e., it is currently active) or not. For navigation purposes, we should add the destination information; to do that, we wait for a proper definition of both the map and of the effectors.

### Devices
- **ble/activate**: device sends a message with payload = <ID> to the brain. Once that is subscribed, the brain will consider this device as one that is moving towards a destination (status of the device: INACTIVE -> NAVIGATING).
- **ble/deactivate**: device is considered no more navigating (status of the device: NAVIGATING -> INACTIVE).
  
### Effectors
- **ble/neighbours**: previous implementation. Brain was communicating to active devices the closest node to them.
- **ble/effectors/activate**: consistent with the current implementation of the localization system. The message is of the form: <MAC_EFFECTOR>$<DEVICE_ID>$<SHOW/NOT_SHOW>. Brain publishes a message for each pair (effector, device) to tell which of them are actually active. It will be the effector that will toggle show / not show depending on the payload.

## Code

### Map information
The map is loaded from the [assets/](https://github.com/filipkrasniqi/smart-directions-subscriber/tree/master/assets) directory. The files are mapped with Python classes in the [map/](https://github.com/filipkrasniqi/smart-directions-subscriber/tree/master/map/elements) directory. [Parser](https://github.com/filipkrasniqi/smart-directions-subscriber/blob/master/utils/parser.py) class handles parsing.

### Execution
You should run the [brain/main.py](https://github.com/filipkrasniqi/smart-directions-subscriber/blob/master/brain/brain.py). This code will run the MQTTSubscriber thread, that initializes MQTT stuff (connection, subscribing to topics) and starts the [localization timer](https://github.com/filipkrasniqi/smart-directions-subscriber/blob/master/localization/localization_thread.py), whose duty is to communicate with the effectors about the devices localization.

### Data collection
Data are stored in the MQTTSubscriber class using a Dictionary data structure. First-level keys are the IDs of the sniffed devices, the values are a second-level dictionary with:
- for key "status", a value INACTIVE / NAVIGATING, depending on whether the corresponding device required to use the system
- MAC of the anchors as keys and a queue of fixed size, containing as value a third-level dictionary of the format:
  - for key "value" the collected RSSI
  - for key "timestamp", the datetime of collection of that information. Useful in case the device stops communicating, otherwise we can't discriminate "zombie devices" (i.e., those that didn't deactivate).

### Localization
To allow more versatility in case we change the localization method, the abstract [Localization](https://github.com/filipkrasniqi/smart-directions-subscriber/blob/master/localization/localization.py) class refers to a generic localization method. Then, the [localization timer](https://github.com/filipkrasniqi/smart-directions-subscriber/blob/master/localization/localization_thread.py) will work accordingly to the instance of the Localization class. This means that to add a new way of performing localization with the collected data from the anchors one should add a new inherited class of Localization, reimplementing accordingly the topic where to public and how to build the message.

## Short term TODOs
- topic update
- connection to custom broker
- handling permissions with different users for MQTT
- add destination of device when activating it
