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

constexpr unsigned long WIFI_RETRY_INTERVAL_MS = 10'000;
constexpr unsigned long MQTT_RETRY_INTERVAL_MS = 5'000;
constexpr unsigned long WIFI_CONNECT_TIMEOUT_MS = 15'000;

// Most 5 V relay boards are active LOW. Change this to false if your relay
// switches on when its input is HIGH.
constexpr bool RELAY_ACTIVE_LOW = true;

struct RelayChannel {
  const char *id;
  const char *displayName;
  uint8_t pin;
  bool isOn;
};

RelayChannel relays[] = {
    {"living-room", "Phòng khách", 16, false},
    {"bedroom", "Phòng ngủ", 17, false},
    {"kitchen", "Nhà bếp", 18, false},
    {"balcony", "Ban công", 19, false},
};

constexpr size_t RELAY_COUNT = sizeof(relays) / sizeof(relays[0]);

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

unsigned long lastWifiAttempt = 0;
unsigned long lastMqttAttempt = 0;

void setRelay(RelayChannel &relay, bool turnOn) {
  relay.isOn = turnOn;
  const uint8_t activeLevel = RELAY_ACTIVE_LOW ? LOW : HIGH;
  const uint8_t inactiveLevel = RELAY_ACTIVE_LOW ? HIGH : LOW;
  digitalWrite(relay.pin, turnOn ? activeLevel : inactiveLevel);
}

String stateTopic(const RelayChannel &relay) {
  return String(MQTT_ROOT) + "/lights/" + relay.id + "/state";
}

String setTopic(const RelayChannel &relay) {
  return String(MQTT_ROOT) + "/lights/" + relay.id + "/set";
}

void publishRelayState(const RelayChannel &relay) {
  if (!mqttClient.connected()) {
    return;
  }

  char payload[192];
  snprintf(payload, sizeof(payload),
           "{\"device_id\":\"%s\",\"id\":\"%s\",\"name\":\"%s\",\"on\":%s,\"gpio\":%u}",
           DEVICE_ID, relay.id, relay.displayName, relay.isOn ? "true" : "false",
           relay.pin);
  mqttClient.publish(stateTopic(relay).c_str(), payload, true);
}

void publishAllRelayStates() {
  for (const auto &relay : relays) {
    publishRelayState(relay);
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
    publishAllRelayStates();
    return;
  }

  bool turnOn = false;
  if (!parseOnOffPayload(payload, length, turnOn)) {
    Serial.printf("[MQTT] Ignored invalid payload on %s\n", topic);
    return;
  }

  if (receivedTopic == ALL_LIGHTS_SET_TOPIC) {
    for (auto &relay : relays) {
      setRelay(relay, turnOn);
      publishRelayState(relay);
    }
    return;
  }

  for (auto &relay : relays) {
    if (receivedTopic == setTopic(relay)) {
      setRelay(relay, turnOn);
      publishRelayState(relay);
      Serial.printf("[RELAY] %s -> %s\n", relay.id, turnOn ? "ON" : "OFF");
      return;
    }
  }
}

void initializeRelays() {
  // Write the safe OFF level before switching each pin to OUTPUT. This helps
  // avoid a short relay pulse during boot.
  const uint8_t inactiveLevel = RELAY_ACTIVE_LOW ? HIGH : LOW;
  for (auto &relay : relays) {
    digitalWrite(relay.pin, inactiveLevel);
    pinMode(relay.pin, OUTPUT);
    setRelay(relay, false);
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

  for (const auto &relay : relays) {
    mqttClient.subscribe(setTopic(relay).c_str(), 1);
  }

  publishAllRelayStates();
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(200);
  initializeRelays();

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
