#include <Arduino.h>
#include <PubSubClient.h>
#include <WiFi.h>

#include <cctype>

#include "config.h"

namespace {

constexpr char MQTT_ROOT[] = "smarthome";
constexpr char DEVICE_ID[] = "esp32-main";
constexpr char DEVICE_STATUS_TOPIC[] = "smarthome/esp32/status";
constexpr char DEVICE_GET_STATE_TOPIC[] = "smarthome/esp32/get-state";
constexpr char ALL_LIGHTS_SET_TOPIC[] = "smarthome/lights/all/set";

constexpr unsigned long WIFI_RETRY_INTERVAL_MS = 10000UL;
constexpr unsigned long MQTT_RETRY_INTERVAL_MS = 5000UL;
constexpr unsigned long WIFI_CONNECT_TIMEOUT_MS = 15000UL;

// The learning setup wires LEDs from 3.3 V to each GPIO, so LOW turns them on.
constexpr bool OUTPUT_ACTIVE_LOW = true;

struct LightChannel {
  const char *id;
  const char *displayName;
  uint8_t pin;
  bool isOn;
};

LightChannel lights[] = {
    {"living-room", "Phòng khách", 16, false},
    {"bedroom", "Phòng ngủ", 17, false},
    {"kitchen", "Nhà bếp", 18, false},
    {"balcony", "Ban công", 19, false},
};

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

unsigned long lastWifiAttempt = 0;
unsigned long lastMqttAttempt = 0;

void setLightOutput(LightChannel &light, bool turnOn) {
  light.isOn = turnOn;
  const uint8_t activeLevel = OUTPUT_ACTIVE_LOW ? LOW : HIGH;
  const uint8_t inactiveLevel = OUTPUT_ACTIVE_LOW ? HIGH : LOW;
  digitalWrite(light.pin, turnOn ? activeLevel : inactiveLevel);
}

String stateTopic(const LightChannel &light) {
  return String(MQTT_ROOT) + "/lights/" + light.id + "/state";
}

String setTopic(const LightChannel &light) {
  return String(MQTT_ROOT) + "/lights/" + light.id + "/set";
}

void publishLightState(const LightChannel &light) {
  if (!mqttClient.connected()) {
    return;
  }

  char payload[192];
  snprintf(payload, sizeof(payload),
           "{\"device_id\":\"%s\",\"id\":\"%s\",\"name\":\"%s\",\"on\":%s,\"gpio\":%u}",
           DEVICE_ID, light.id, light.displayName, light.isOn ? "true" : "false",
           light.pin);
  mqttClient.publish(stateTopic(light).c_str(), payload, true);
}

void publishAllLightStates() {
  for (const auto &light : lights) {
    publishLightState(light);
  }
}

bool parseOnOffPayload(const byte *payload, unsigned int length, bool &turnOn) {
  String command;
  command.reserve(length);

  for (unsigned int i = 0; i < length; ++i) {
    const unsigned char value = payload[i];
    if (!std::isspace(value)) {
      command += static_cast<char>(std::tolower(value));
    }
  }

  if (command == "on" || command == "1" || command == "true" ||
      command == "{\"on\":true}") {
    turnOn = true;
    return true;
  }

  if (command == "off" || command == "0" || command == "false" ||
      command == "{\"on\":false}") {
    turnOn = false;
    return true;
  }

  return false;
}

void onMqttMessage(char *topic, byte *payload, unsigned int length) {
  const String receivedTopic(topic);

  if (receivedTopic == DEVICE_GET_STATE_TOPIC) {
    publishAllLightStates();
    return;
  }

  bool turnOn = false;
  if (!parseOnOffPayload(payload, length, turnOn)) {
    Serial.printf("[MQTT] Ignored invalid payload on %s\n", topic);
    return;
  }

  if (receivedTopic == ALL_LIGHTS_SET_TOPIC) {
    for (auto &light : lights) {
      setLightOutput(light, turnOn);
      publishLightState(light);
    }
    return;
  }

  for (auto &light : lights) {
    if (receivedTopic == setTopic(light)) {
      setLightOutput(light, turnOn);
      publishLightState(light);
      Serial.printf("[LIGHT] %s -> %s\n", light.id, turnOn ? "ON" : "OFF");
      return;
    }
  }
}

void initializeLightOutputs() {
  // Write the OFF level before switching each pin to OUTPUT.
  const uint8_t inactiveLevel = OUTPUT_ACTIVE_LOW ? HIGH : LOW;
  for (auto &light : lights) {
    digitalWrite(light.pin, inactiveLevel);
    pinMode(light.pin, OUTPUT);
    setLightOutput(light, false);
  }
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
  while (WiFi.status() != WL_CONNECTED && millis() - startedAt < WIFI_CONNECT_TIMEOUT_MS) {
    delay(250);
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[WiFi] Connected. IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("[WiFi] Connection timed out; will retry.");
  }
}

void connectMqtt() {
  if (WiFi.status() != WL_CONNECTED || mqttClient.connected()) {
    return;
  }

  char clientId[48];
  const uint64_t chipId = ESP.getEfuseMac();
  snprintf(clientId, sizeof(clientId), "%s-%04X", DEVICE_ID,
           static_cast<uint16_t>(chipId & 0xFFFF));

  const char onlinePayload[] =
      "{\"device_id\":\"esp32-main\",\"online\":true}";
  const char offlinePayload[] =
      "{\"device_id\":\"esp32-main\",\"online\":false}";

  bool connected = false;
  if (strlen(MQTT_USERNAME) > 0) {
    connected = mqttClient.connect(clientId, MQTT_USERNAME, MQTT_PASSWORD,
                                   DEVICE_STATUS_TOPIC, 1, true, offlinePayload);
  } else {
    connected = mqttClient.connect(clientId, DEVICE_STATUS_TOPIC, 1, true,
                                   offlinePayload);
  }

  if (!connected) {
    Serial.printf("[MQTT] Connection failed, state=%d\n", mqttClient.state());
    return;
  }

  Serial.println("[MQTT] Connected.");
  mqttClient.publish(DEVICE_STATUS_TOPIC, onlinePayload, true);
  mqttClient.subscribe(DEVICE_GET_STATE_TOPIC, 1);
  mqttClient.subscribe(ALL_LIGHTS_SET_TOPIC, 1);

  for (const auto &light : lights) {
    mqttClient.subscribe(setTopic(light).c_str(), 1);
  }

  publishAllLightStates();
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(200);
  initializeLightOutputs();

  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setCallback(onMqttMessage);
  mqttClient.setBufferSize(512);

  startWifiConnection();
  connectMqtt();
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
}
