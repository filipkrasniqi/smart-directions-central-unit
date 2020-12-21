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
- **ble/rssi**: each anchor sends a message of the form <MAC_ADDRESS_RBERRY_PI>$<SNIFFED_MAC_ADDRESS>$<RSSI_VAL>. The brain will store the information associating it to a device. Anchors are not aware of the current activated devices, so they will send rssi values for any sniffed device, regardless of whether such a device is actually using the system (i.e., it is currently active) or not. For navigation purposes, we should add the destination information (TODO); to do that, we wait for a proper definition of both the map and of the effectors.

### Devices
- **ble/activate**: device sends a message with payload = <ID> to the brain. Once that is subscribed, the brain will consider this device as one that is moving towards a destination (status of the device: INACTIVE -> NAVIGATING).
- **ble/deactivate**: device is considered no more navigating (status of the device: NAVIGATING -> INACTIVE).
  
(TODO: we should authenticate as we did for parking, especially in this part where sensible data are used (location))
  
### Effectors
- **ble/neighbours**: previous implementation. Brain was communicating to active devices the closest node to them.
- **ble/effectors/activate**: consistent with the current implementation of the localization system. The message is of the form: <MAC_EFFECTOR>$<DEVICE_ID>$<SHOW/NOT_SHOW>. Brain publishes a message for each pair (effector, device) to tell which of them are actually active. It will be the effector that will toggle show / not show depending on the payload.

## Code
### Execution
You should run the [brain/main.py](https://github.com/filipkrasniqi/smart-directions-subscriber/blob/master/brain/brain.py).

### Map information
The map is loaded from the [assets/](https://github.com/filipkrasniqi/smart-directions-subscriber/tree/master/assets) folder.
