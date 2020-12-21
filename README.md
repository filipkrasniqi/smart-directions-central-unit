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
