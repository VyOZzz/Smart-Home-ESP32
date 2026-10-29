#pragma once

// Copy this file to config.h and fill in the local network values.
// Never commit include/config.h.
#define WIFI_SSID "YOUR_WIFI_NAME"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// Use the MacBook's LAN IPv4 address. localhost and 127.0.0.1 point back to
// the ESP32 itself and cannot reach Mosquitto on the MacBook.
#define MQTT_HOST "192.168.1.10"
#define MQTT_PORT 1883
#define MQTT_USERNAME ""
#define MQTT_PASSWORD ""

#define SENSOR_DEVICE_ID "esp32-sensor"
#define SENSOR_ID "room-1"
#define SENSOR_NAME "Phòng 1"
#define DHT_DATA_PIN 4
#define SENSOR_SAMPLE_INTERVAL_MS 5000UL
