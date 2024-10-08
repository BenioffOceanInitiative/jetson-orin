#include "EspMQTTClient.h"

const int pwm = D2;     // Pin that the Mosfet module is connected to
const int apin = 0;     // Analog read pin, comes from the light sensor
int prevTime = 0;
int reading;
int brightness = 125;   // default PWM setting (0-255, about 50% brightness)
int interval = 1000;    // Delay for reading light sensor (milliseconds)
int threshold = 512;    // Threshold reading from light sensor to turn the light on (0 - 1024)

EspMQTTClient client(
    "MyNetwork",        // wifi network name
    "MyPassword",       // wifi password
    "192.168.0.0",      // MQTT Broker server ip
    //"MQTTUsername",   // Can be omitted if not needed
    //"MQTTPassword",   // Can be omitted if not needed
    "gwynnda_light",    // Client name that uniquely identify your device
    8883                // The MQTT port, defaults to 1883 if omitted
);

void setup()
{
  // Serial.begin(115200);
  pinMode(pwm, OUTPUT);
  pinMode(apin, INPUT);
  client.enableLastWillMessage("gwynnda_light/lastwill", "I am going offline"); // You can activate the retain flag by setting the third parameter to true
  analogWrite(pwm, 0);
}

void onConnectionEstablished()
{
  // Set the topics you will be publishing / subscribing to
  client.subscribe("gwynnda/light/brightness", [](const String &payload)      
                   {
                     brightness = payload.toInt();
                     analogWrite(pwm, brightness);
                     // Serial.println("Recieved Brightness Payload");
                     // Serial.println(payload);
                   });

  client.subscribe("gwynnda/light/threshold", [](const String &payload)
                   {
                     threshold = payload.toInt();
                     // Serial.println("Received Threshold payload");
                     // Serial.println(payload);
                     // Serial.println(threshold);
                   });

  // feedback every 5 seconds
  client.executeDelayed(5 * 1000, []()
                        {
    client.publish("gwynnda/light/brightness_setting", String(brightness));
    client.publish("gwynnda/light/threshold_setting",String(threshold)); });
}

void loop()
{
  int currentTime = millis();
  if (currentTime - prevTime > interval)
  {
    prevTime = currentTime;
    reading = analogRead(apin);
    // Serial.println(reading);
    if (reading > threshold)
    {
      analogWrite(pwm, brightness);
    }
    else
    {
      analogWrite(pwm, 0);
    }
  }

  client.loop();
}
