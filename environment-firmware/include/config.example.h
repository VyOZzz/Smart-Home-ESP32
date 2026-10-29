#pragma once

// Copy this file to config.h and fill in values for your network.
// Never commit include/config.h.
#define WIFI_SSID "YOUR_WIFI_NAME"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// Local broker: MacBook LAN IP, port 1883 and MQTT_USE_TLS 0.
// Cloud broker: provider endpoint, normally port 8883 and MQTT_USE_TLS 1.
#define MQTT_HOST "192.168.1.10"
#define MQTT_PORT 1883
#define MQTT_USE_TLS 0
#define MQTT_USERNAME ""
#define MQTT_PASSWORD ""

// Certificate validation is the default for TLS. Insecure TLS is provided only
// for short-lived local diagnosis and must remain disabled for cloud use.
#define MQTT_TLS_ALLOW_INSECURE 0
#define MQTT_CA_CERT R"EOF(
-----BEGIN CERTIFICATE-----
PASTE_BROKER_CA_CERTIFICATE_HERE
-----END CERTIFICATE-----
)EOF"

#define ENVIRONMENT_DEVICE_ID "esp32-environment"
#define DHT_DATA_PIN 23
#define SENSOR_SAMPLE_INTERVAL_MS 10000UL

