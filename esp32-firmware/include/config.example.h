#pragma once

// Copy this file to config.h and replace the values for your network.
#define WIFI_SSID "YOUR_WIFI_NAME"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// Local Mosquitto example: laptop LAN IP, port 1883, MQTT_USE_TLS 0.
// Cloud example: provider endpoint, normally port 8883, MQTT_USE_TLS 1.
// Never use localhost/127.0.0.1 because that means the ESP32 itself.
#define MQTT_HOST "192.168.1.10"
#define MQTT_PORT 1883
#define MQTT_USE_TLS 0

// Leave both empty when the MQTT broker does not require authentication.
#define MQTT_USERNAME ""
#define MQTT_PASSWORD ""

// For TLS, paste the broker CA certificate between the markers. Certificate
// validation is the default. Insecure TLS exists only for short-lived local
// diagnosis and must not be used for the cloud demo.
#define MQTT_TLS_ALLOW_INSECURE 0
#define MQTT_CA_CERT R"EOF(
-----BEGIN CERTIFICATE-----
PASTE_BROKER_CA_CERTIFICATE_HERE
-----END CERTIFICATE-----
)EOF"
