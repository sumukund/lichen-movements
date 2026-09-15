#include <Servo.h>
#include "minneapolis_humidity_data.h"

// --- Servo setup ---
const uint8_t NUM_SERVOS = 6;
Servo servos[NUM_SERVOS];
const uint8_t servoPins[NUM_SERVOS] = {8, 9, 10, 11, 12, 13};

// A new calendar day is shown once per minute: 365 days = 365 minutes.
const unsigned long DAY_INTERVAL_MS = 60000UL;
const unsigned long SERVO_UPDATE_INTERVAL_MS = 100UL;
uint16_t dayIndex = 0;  // Jan 1 at reset; advances through Dec 31.
unsigned long lastDayChangeMs = 0;
unsigned long lastServoUpdateMs = 0;
int startAngle = 0;
int targetAngle = 0;
int appliedAngle = -1;

void exponential_humidity_to_servo_angle(float humidity, int &angle) {
  if (humidity <= 70) {
    // Minimal movement for humidity 0-70%
    angle = map(constrain(humidity, 0, 70), 0, 70, 0, 50);
  } else {
    // Exponential scaling for humidity 70-100%
    float excessHumidity = humidity - 70;
    float expScaled = pow(1.05, excessHumidity); // Exponential growth with base 1.05
    angle = map(expScaled * 100, 100, pow(1.05, 30) * 100, 50, 180); // Map to 50-180 degrees
  }
}

int humidityAngleForDay(uint16_t index) {
  float humidity = MINNEAPOLIS_HUMIDITY_BY_DAY[index];
  int angle;
  exponential_humidity_to_servo_angle(humidity, angle);
  return angle;
}

void printCurrentDay() {
  float humidity = MINNEAPOLIS_HUMIDITY_BY_DAY[dayIndex];

  Serial.print("Day ");
  Serial.print(dayIndex + 1);
  Serial.print(" / ");
  Serial.print(HUMIDITY_DAY_COUNT);
  Serial.print("  humidity: ");
  Serial.print(humidity, 0);
  Serial.print("%  target servo angle: ");
  Serial.println(targetAngle);
}

void updateServoPosition(unsigned long now) {
  if (now - lastServoUpdateMs < SERVO_UPDATE_INTERVAL_MS) {
    return;
  }
  lastServoUpdateMs = now;

  // Ease from the prior day's angle to this day's angle over its full minute.
  unsigned long elapsed = now - lastDayChangeMs;
  if (elapsed > DAY_INTERVAL_MS) {
    elapsed = DAY_INTERVAL_MS;
  }
  int angle = startAngle + ((targetAngle - startAngle) * (long)elapsed) / DAY_INTERVAL_MS;

  if (angle != appliedAngle) {
    for (uint8_t i = 0; i < NUM_SERVOS; i++) {
      servos[i].write(angle);
    }
    appliedAngle = angle;
  }
}

void setup() {
  Serial.begin(9600);

  for (uint8_t i = 0; i < NUM_SERVOS; i++) {
    servos[i].attach(servoPins[i]);
  }

  targetAngle = humidityAngleForDay(dayIndex);
  startAngle = targetAngle;
  appliedAngle = targetAngle;
  for (uint8_t i = 0; i < NUM_SERVOS; i++) {
    servos[i].write(appliedAngle);
  }
  printCurrentDay();
  lastDayChangeMs = millis();
}

void loop() {
  if (millis() - lastDayChangeMs >= DAY_INTERVAL_MS) {
    lastDayChangeMs += DAY_INTERVAL_MS;
    startAngle = targetAngle;
    dayIndex = (dayIndex + 1) % HUMIDITY_DAY_COUNT;
    targetAngle = humidityAngleForDay(dayIndex);
    printCurrentDay();
  }

  updateServoPosition(millis());
}
