#pragma once

// Copy this file to config.h and replace the values for your local network.
// MQTT_HOST must be the laptop's LAN IP address, not localhost/127.0.0.1.
#define WIFI_SSID "YOUR_WIFI_NAME"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

#define MQTT_HOST "192.168.1.10"
#define MQTT_PORT 1883

// Leave both empty when the MQTT broker does not require authentication.
#define MQTT_USERNAME ""
#define MQTT_PASSWORD ""
