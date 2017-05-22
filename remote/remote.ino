/********************************************************
 * This sketch is intended to be run on a wemos D1 mini.
 *     I shall add a schematic when I get a moment.
 ********************************************************/

#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

WiFiUDP udp;
unsigned int localudpPort = 4210;

String remoteIp = "192.168.0.65";
unsigned int remoteudpPort = 5005;

const char* ssid = "Orphan";
const char* password = "Endorphin";

char packetBuffer[255];
int packetBufferIndex = 0;

long unsigned int lastInterrupt = 0;
long unsigned int debounceTime = 250;

void setup() {
    Serial.begin(9600);
    Serial.println("Connecting to wifi...");
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(100);
    }
    Serial.println("Wifi connected");
    pinMode(D4, OUTPUT);
    pinMode(D6, INPUT);
    
    digitalWrite(D4, LOW);
    udp.begin(remoteudpPort);
    Serial.println("UDP connected");
    attachInterrupt(D7, pinD7Interrupt, RISING);
    attachInterrupt(D1, pinD1Interrupt, RISING);
    attachInterrupt(D2, pinD2Interrupt, RISING);
    attachInterrupt(D8, pinD8Interrupt, RISING);
    attachInterrupt(D5, pinD5Interrupt, RISING);
    attachInterrupt(D3, pinD3Interrupt, FALLING);
}

void pinD7Interrupt() {
    if (lastInterrupt + debounceTime < millis()) {
        Serial.println("C");
        packetBuffer[packetBufferIndex++] = 'C';
        lastInterrupt = millis();
    }
}

void pinD1Interrupt() {
    if (lastInterrupt + debounceTime < millis()) {
        Serial.println("S");
        packetBuffer[packetBufferIndex++] = 'S';
        lastInterrupt = millis();
    }
}

void pinD2Interrupt() {
    if (lastInterrupt + debounceTime < millis()) {
        Serial.println("L");
        packetBuffer[packetBufferIndex++] = 'L';
        lastInterrupt = millis();
    }
}

void pinD3Interrupt() {
    if (lastInterrupt + debounceTime < millis()) {
        Serial.println("D");
        packetBuffer[packetBufferIndex++] = 'D';
        lastInterrupt = millis();
    }
}

void pinD8Interrupt() {
    if (lastInterrupt + debounceTime < millis()) {
        Serial.println("R");
        packetBuffer[packetBufferIndex++] = 'R';
        lastInterrupt = millis();
    }
}

void pinD5Interrupt() {
    if (lastInterrupt + debounceTime < millis()) {
        Serial.println("W");
        packetBuffer[packetBufferIndex++] = 'W';
        lastInterrupt = millis();
    }
}

void loop() {
    if (packetBufferIndex != 0) {
        udp.beginPacket(remoteIp.c_str(),remoteudpPort);
        //noInterrupts();
        udp.write(packetBuffer, packetBufferIndex);
        packetBufferIndex = 0;
        //interrupts();;
        udp.endPacket();
    }
}
