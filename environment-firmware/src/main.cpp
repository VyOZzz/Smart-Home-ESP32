#include <Arduino.h>
#include <DHT.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include <ctime>

#include "config.h"

#ifndef MQTT_USE_TLS
#define MQTT_USE_TLS 0
#endif

#ifndef MQTT_TLS_ALLOW_INSECURE
#define MQTT_TLS_ALLOW_INSECURE 0
#endif

#ifndef MQTT_CA_CERT
#define MQTT_CA_CERT ""
#endif

#ifndef ENVIRONMENT_DEVICE_ID
#define ENVIRONMENT_DEVICE_ID "esp32-environment"
#endif

#ifndef DHT_DATA_PIN
#define DHT_DATA_PIN 23
#endif

#ifndef SENSOR_SAMPLE_INTERVAL_MS
#define SENSOR_SAMPLE_INTERVAL_MS 10000UL
#endif

namespace {

constexpr unsigned long WIFI_RETRY_INTERVAL_MS = 10000UL;
constexpr unsigned long MQTT_RETRY_INTERVAL_MS = 5000UL;
constexpr unsigned long WIFI_CONNECT_TIMEOUT_MS = 15000UL;
constexpr unsigned long NTP_SYNC_TIMEOUT_MS = 10000UL;
constexpr unsigned long MINIMUM_DHT22_INTERVAL_MS = 2000UL;
constexpr time_t MIN_VALID_UNIX_TIME = 1577836800;  // 2020-01-01 UTC

static_assert(SENSOR_SAMPLE_INTERVAL_MS >= MINIMUM_DHT22_INTERVAL_MS,
              "DHT22 sampling interval must be at least 2000 ms");

DHT dht(DHT_DATA_PIN, DHT22);
WiFiClient wifiClient;
WiFiClientSecure secureWifiClient;
PubSubClient mqttClient;

unsigned long lastWifiAttempt = 0;
unsigned long lastMqttAttempt = 0;
unsigned long lastSensorSample = 0;
bool clockSynchronized = false;

String stateTopic() {
  return String("smarthome/environment/") + ENVIRONMENT_DEVICE_ID + "/state";
}

String statusTopic() {
  return String("smarthome/environment/") + ENVIRONMENT_DEVICE_ID + "/status";
}

String getStateTopic() {
  return String("smarthome/environment/") + ENVIRONMENT_DEVICE_ID + "/get-state";
}

bool ensureClockForTls() {
#if MQTT_USE_TLS && !MQTT_TLS_ALLOW_INSECURE
  if (clockSynchronized && time(nullptr) >= MIN_VALID_UNIX_TIME) {
    return true;
  }

  Serial.println("[TLS] Synchronizing clock with NTP...");
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  const unsigned long startedAt = millis();
  while (time(nullptr) < MIN_VALID_UNIX_TIME &&
         millis() - startedAt < NTP_SYNC_TIMEOUT_MS) {
    delay(250);
  }

  clockSynchronized = time(nullptr) >= MIN_VALID_UNIX_TIME;
  if (!clockSynchronized) {
    Serial.println("[TLS] NTP sync failed; MQTT connection postponed.");
  }
  return clockSynchronized;
#else
  return true;
#endif
}

void startWifiConnection() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.printf("[WiFi] Connecting to %s\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  const unsigned long startedAt = millis();
  while (WiFi.status() != WL_CONNECTED &&
         millis() - startedAt < WIFI_CONNECT_TIMEOUT_MS) {
    delay(250);
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[WiFi] Connected. IP: %s\n",
                  WiFi.localIP().toString().c_str());
  } else {
    Serial.println("[WiFi] Connection timed out; will retry.");
  }
}

bool readAndPublishEnvironment() {
  const float humidity = dht.readHumidity();
  const float temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("[DHT22] Invalid reading; nothing published.");
    return false;
  }

  if (humidity < 0.0F || humidity > 100.0F || temperature < -40.0F ||
      temperature > 80.0F) {
    Serial.println("[DHT22] Out-of-range reading; nothing published.");
    return false;
  }

  char payload[192];
  snprintf(payload, sizeof(payload),
           "{\"device_id\":\"%s\",\"temperature_c\":%.1f,"
           "\"humidity_percent\":%.1f}",
           ENVIRONMENT_DEVICE_ID, temperature, humidity);

  const bool published = mqttClient.publish(stateTopic().c_str(), payload, true);
  if (published) {
    Serial.printf("[DHT22] Temperature %.1f C, humidity %.1f %%\n", temperature,
                  humidity);
  } else {
    Serial.println("[MQTT] Failed to publish environment reading.");
  }
  return published;
}

void onMqttMessage(char *topic, byte *, unsigned int) {
  if (String(topic) == getStateTopic()) {
    readAndPublishEnvironment();
  }
}

void connectMqtt() {
  if (WiFi.status() != WL_CONNECTED || mqttClient.connected()) {
    return;
  }

  if (!ensureClockForTls()) {
    return;
  }

  char clientId[64];
  const uint64_t chipId = ESP.getEfuseMac();
  snprintf(clientId, sizeof(clientId), "%s-%04X", ENVIRONMENT_DEVICE_ID,
           static_cast<uint16_t>(chipId & 0xFFFF));

  char onlinePayload[128];
  char offlinePayload[128];
  snprintf(onlinePayload, sizeof(onlinePayload),
           "{\"device_id\":\"%s\",\"online\":true}",
           ENVIRONMENT_DEVICE_ID);
  snprintf(offlinePayload, sizeof(offlinePayload),
           "{\"device_id\":\"%s\",\"online\":false}",
           ENVIRONMENT_DEVICE_ID);

  const String deviceStatusTopic = statusTopic();
  bool connected = false;
  if (strlen(MQTT_USERNAME) > 0) {
    connected = mqttClient.connect(clientId, MQTT_USERNAME, MQTT_PASSWORD,
                                   deviceStatusTopic.c_str(), 1, true,
                                   offlinePayload);
  } else {
    connected = mqttClient.connect(clientId, deviceStatusTopic.c_str(), 1, true,
                                   offlinePayload);
  }

  if (!connected) {
    Serial.printf("[MQTT] Connection failed, state=%d\n", mqttClient.state());
    return;
  }

  Serial.println("[MQTT] Connected.");
  mqttClient.publish(deviceStatusTopic.c_str(), onlinePayload, true);
  mqttClient.subscribe(getStateTopic().c_str(), 1);

  // Publish immediately after reconnect so the backend does not wait for the
  // next periodic sample. Invalid DHT22 reads remain unpublished.
  readAndPublishEnvironment();
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(200);
  dht.begin();

#if MQTT_USE_TLS
#if MQTT_TLS_ALLOW_INSECURE
  secureWifiClient.setInsecure();
#else
  secureWifiClient.setCACert(MQTT_CA_CERT);
#endif
  mqttClient.setClient(secureWifiClient);
#else
  mqttClient.setClient(wifiClient);
#endif

  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setCallback(onMqttMessage);
  mqttClient.setBufferSize(512);
  mqttClient.setKeepAlive(30);

  startWifiConnection();
  connectMqtt();
  lastSensorSample = millis();
}

void loop() {
  const unsigned long now = millis();

  if (WiFi.status() != WL_CONNECTED) {
    if (now - lastWifiAttempt >= WIFI_RETRY_INTERVAL_MS) {
      lastWifiAttempt = now;
      startWifiConnection();
    }
    return;
  }

  if (!mqttClient.connected()) {
    if (now - lastMqttAttempt >= MQTT_RETRY_INTERVAL_MS) {
      lastMqttAttempt = now;
      connectMqtt();
    }
    return;
  }

  mqttClient.loop();

  if (now - lastSensorSample >= SENSOR_SAMPLE_INTERVAL_MS) {
    lastSensorSample = now;
    readAndPublishEnvironment();
  }
}

