#include <Servo.h>

// --- Servo Setup ---
const int NUM_SERVOS = 6;
Servo servos[NUM_SERVOS];
const int servoPins[NUM_SERVOS] = {8, 9, 10, 11, 12, 13};

// Variables to hold incoming weather data
float temperature = 20.0; // Default fallback baseline
float humidity = 50.0;

void setup() {
  // Serial for debugging/receiving data from a bridge (e.g., ESP8266 on Serial1)
  Serial.begin(9600); // Change to Serial if testing directly with a Python script via USB
  
  Serial.println("Waiting for Minnesota Weather API data...");

  for (int i = 0; i < NUM_SERVOS; i++) {
    servos[i].attach(servoPins[i]);
  }

  randomSeed(analogRead(A0));
}

void loop() {
  // Check if weather data string is available from the Wi-Fi module/Serial
  if (Serial1.available() > 0) {
    String incomingData = Serial1.readStringUntil('\n');
    incomingData.trim();

    // Expecting format: "temperature,humidity" (e.g., "18.5,65")
    int commaIndex = incomingData.indexOf(',');
    if (commaIndex > 0) {
      temperature = incomingData.substring(0, commaIndex).toFloat();
      humidity = incomingData.substring(commaIndex + 1).toFloat();

      Serial.print("Received API Update -> Temp: ");
      Serial.print(temperature);
      Serial.print(" °C | Humidity: ");
      Serial.print(humidity);
      Serial.println(" %");
    }
  }


  int maxAngle = map(constrain(temperature, -20, 35), -20, 35, 20, 180);

  // Generate random positions based on the live API weather bounds
  int pos1 = random(0, maxAngle);
  int pos2 = random(0, maxAngle);
  int pos3 = random(0, maxAngle);
  int pos4 = random(0, maxAngle);
  int pos5 = random(0, maxAngle);
  int pos6 = random(0, maxAngle);

  servos[0].write(pos1);
  servos[1].write(pos2);
  servos[2].write(pos3);
  servos[3].write(pos4);
  servos[4].write(pos5);
  servos[5].write(pos6);

  // Humidity alters pause duration (Damp/Rainy = slower movement intervals)
  int delayTime = map(constrain(humidity, 20, 100), 20, 100, 1000, 5000);
  
  delay(delayTime);
}