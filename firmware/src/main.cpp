#include <Arduino.h>
#include <ArduinoJson.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <WiFi.h>
#include <new>

#if __has_include("secrets.h")
#include "secrets.h"
#endif

#ifndef AXION_WIFI_SSID
#define AXION_WIFI_SSID ""
#endif

#ifndef AXION_WIFI_PASSWORD
#define AXION_WIFI_PASSWORD ""
#endif

namespace {

constexpr size_t kMaximumCommandBytes = 1024;
AsyncWebServer server(80);

struct CommandBody {
    String contents;
    const char* error = nullptr;
    uint16_t status = 200;
    bool parsed = false;
};

void releaseRequestBody(AsyncWebServerRequest* request) {
    delete static_cast<CommandBody*>(request->_tempObject);
    request->_tempObject = nullptr;
}

void handleCommandBody(
    AsyncWebServerRequest* request,
    uint8_t* data,
    size_t length,
    size_t index,
    size_t total
) {
    if (index == 0) {
        releaseRequestBody(request);
        request->_tempObject = new (std::nothrow) CommandBody();
    }

    auto* body = static_cast<CommandBody*>(request->_tempObject);
    if (body == nullptr || body->status != 200 || body->parsed) {
        return;
    }
    if (total > kMaximumCommandBytes) {
        body->status = 413;
        body->error = "command body too large";
        return;
    }
    if (index + length > total) {
        body->status = 400;
        body->error = "invalid request body";
        return;
    }
    if (index == 0 && !body->contents.reserve(total)) {
        body->status = 500;
        body->error = "unable to buffer command";
        return;
    }

    if (!body->contents.concat(reinterpret_cast<const char*>(data), length)) {
        body->status = 400;
        body->error = "invalid request body";
        return;
    }

    if (index + length != total) {
        return;
    }

    JsonDocument document;
    const DeserializationError error = deserializeJson(document, body->contents);
    if (error || !document.is<JsonObject>()) {
        body->status = 400;
        body->error = "expected a JSON object";
        body->parsed = true;
        return;
    }

    Serial.print("Comando JSON recebido: ");
    serializeJson(document, Serial);
    Serial.println();
    body->parsed = true;
}

void handleCommand(AsyncWebServerRequest* request) {
    auto* body = static_cast<CommandBody*>(request->_tempObject);
    if (body == nullptr) {
        request->send(400, "application/json", R"({"detail":"expected a JSON object"})");
        return;
    }

    const uint16_t responseStatus = body->status;
    const char* error = body->error;
    const bool parsed = body->parsed;
    releaseRequestBody(request);

    if (responseStatus != 200) {
        String response = R"({"detail":")";
        response += error == nullptr ? "invalid request body" : error;
        response += R"("})";
        request->send(responseStatus, "application/json", response);
    } else if (!parsed) {
        request->send(400, "application/json", R"({"detail":"expected a JSON object"})");
    } else {
        request->send(200, "application/json", R"({"accepted":true,"hardware_action":"none"})");
    }
}

void configureWifi() {
    if (strlen(AXION_WIFI_SSID) == 0) {
        Serial.println("Wi-Fi nao configurado; crie include/secrets.h localmente.");
        return;
    }

    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(AXION_WIFI_SSID, AXION_WIFI_PASSWORD);
    Serial.println("Conexao Wi-Fi iniciada.");
}

void configureServer() {
    server.on(
        "/api/firmware/command",
        HTTP_POST,
        handleCommand,
        nullptr,
        handleCommandBody
    );
    server.onNotFound([](AsyncWebServerRequest* request) {
        request->send(404, "application/json", R"({"detail":"route not found"})");
    });
    server.begin();
    Serial.println("Servidor HTTP iniciado na porta 80.");
}

}  // namespace

void setup() {
    Serial.begin(115200);
    configureWifi();
    configureServer();
}

void loop() {
    static bool connectionReported = false;
    const bool connected = WiFi.status() == WL_CONNECTED;

    if (connected && !connectionReported) {
        Serial.print("Wi-Fi conectado; IP: ");
        Serial.println(WiFi.localIP());
        connectionReported = true;
    } else if (!connected && connectionReported) {
        Serial.println("Wi-Fi desconectado; aguardando reconexao automatica.");
        connectionReported = false;
    }

    delay(10);
}
