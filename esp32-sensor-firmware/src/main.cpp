#include <Arduino.h>
#include <DHT.h>
#include <PubSubClient.h>
#include <WiFi.h>

#include "config.h"

namespace {

constexpr char STATE_TOPIC[] = "smarthome/sensors/room-1/state";
constexpr char STATUS_TOPIC[] = "smarthome/esp32-sensor/status";
constexpr char REQUEST_TOPIC[] = "smarthome/sensors/room-1/get-state";
constexpr unsigned long WIFI_RETRY_INTERVAL_MS = 10000UL;
constexpr unsigned long MQTT_RETRY_INTERVAL_MS = 5000UL;

DHT dht(DHT_DATA_PIN, DHT11);
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

unsigned long lastWifiAttempt = 0;
unsigned long lastMqttAttempt = 0;
unsigned long lastSampleAt = 0;

bool publishReading() {
  const float humidity = dht.readHumidity();
  const float temperature = dht.readTemperature();

  if (isnan(temperature) || isnan(humidity)) {
    Serial.printf("[DHT11] Read failed on GPIO %d. Check VCC=3V3, DATA=D4/GPIO4 and GND.\n",
                  DHT_DATA_PIN);
    return false;
  }

  char payload[256];
  snprintf(payload, sizeof(payload),
           "{\"device_id\":\"%s\",\"sensor_id\":\"%s\",\"name\":\"%s\","
           "\"temperature\":%.1f,\"humidity\":%.1f,\"temperature_unit\":\"C\"}",
           SENSOR_DEVICE_ID, SENSOR_ID, SENSOR_NAME, temperature, humidity);

  if (!mqttClient.publish(STATE_TOPIC, payload, true)) {
    Serial.println("[MQTT] Failed to publish retained sensor state.");
    return false;
  }

  Serial.printf("[DHT11] Temperature: %.1f C, Humidity: %.1f %%\n", temperature,
                humidity);
  return true;
}

void onMqttMessage(char *topic, byte *, unsigned int) {
  if (strcmp(topic, REQUEST_TOPIC) == 0) {
    Serial.println("[MQTT] State requested.");
    publishReading();
  }
}

void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.println("[WiFi] Connecting...");
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void connectMqtt() {
  if (WiFi.status() != WL_CONNECTED || mqttClient.connected()) {
    return;
  }

  char clientId[64];
  snprintf(clientId, sizeof(clientId), "%s-%04X", SENSOR_DEVICE_ID,
           static_cast<uint16_t>(ESP.getEfuseMac() & 0xFFFF));

  const char offlinePayload[] =
      "{\"device_id\":\"esp32-sensor\",\"online\":false}";
  bool connected = false;
  if (strlen(MQTT_USERNAME) > 0) {
    connected = mqttClient.connect(clientId, MQTT_USERNAME, MQTT_PASSWORD,
                                   STATUS_TOPIC, 1, true, offlinePayload);
  } else {
    connected = mqttClient.connect(clientId, STATUS_TOPIC, 1, true,
                                   offlinePayload);
  }

  if (!connected) {
    Serial.printf("[MQTT] Connection failed, state=%d.\n", mqttClient.state());
    return;
  }

  Serial.println("[MQTT] Connected.");
  mqttClient.publish(
      STATUS_TOPIC,
      "{\"device_id\":\"esp32-sensor\",\"online\":true}", true);
  mqttClient.subscribe(REQUEST_TOPIC, 1);
  publishReading();
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n[Boot] ESP32 DHT11 sensor starting.");

  dht.begin();
  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setCallback(onMqttMessage);
  mqttClient.setBufferSize(512);
  mqttClient.setKeepAlive(30);

  connectWifi();
}

void loop() {
  const unsigned long now = millis();

  if (WiFi.status() != WL_CONNECTED) {
    if (now - lastWifiAttempt >= WIFI_RETRY_INTERVAL_MS) {
      lastWifiAttempt = now;
      connectWifi();
    }
    delay(10);
    return;
  }

  static bool wifiReported = false;
  if (!wifiReported) {
    Serial.printf("[WiFi] Connected. IP: %s\n",
                  WiFi.localIP().toString().c_str());
    wifiReported = true;
  }

  if (!mqttClient.connected()) {
    if (now - lastMqttAttempt >= MQTT_RETRY_INTERVAL_MS) {
      lastMqttAttempt = now;
      connectMqtt();
    }
    delay(10);
    return;
  }

  mqttClient.loop();
  if (now - lastSampleAt >= SENSOR_SAMPLE_INTERVAL_MS) {
    lastSampleAt = now;
    publishReading();
  }
  delay(10);
}
