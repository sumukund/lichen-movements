#include <Servo.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

// Receives live weather lines from run_weather_data.py:
//     humidity_percent,precipitation_mm_per_hour\n
const uint8_t NUM_SERVOS = 6;
Servo servos[NUM_SERVOS];
const uint8_t servoPins[NUM_SERVOS] = {8, 9, 10, 11, 12, 13};

// Dry weather completes one 0 -> target -> 0 sweep in the same five minutes
// between API updates. Rain shortens the sweep, so wet weather moves faster.
const unsigned long DRY_SWEEP_DURATION_MS = 75000UL;
const unsigned long WET_SWEEP_DURATION_MS = 75000UL;
const float RAIN_FOR_MAX_SPEED_MM_H = 5.0;

int appliedAngle = 0;
int targetAngle = 0;
bool movingUp = true;
float currentHumidity = 0.0;
float currentPrecipitation = 0.0;
unsigned long stepDelayMs = 1000UL;
unsigned long lastServoStepMs = 0;

const uint8_t WEATHER_BUFFER_SIZE = 40;
char weatherBuffer[WEATHER_BUFFER_SIZE];
uint8_t weatherBufferLength = 0;


float clampFloat(float value, float minimum, float maximum) {
  if (value < minimum) return minimum;
  if (value > maximum) return maximum;
  return value;
}


int humidityToServoAngle(float humidity) {
  // Same humidity-to-angle function used by the Raspberry Pi controller.
  humidity = clampFloat(humidity, 0.0, 100.0);
  if (humidity <= 70.0) {
    return (int)round((humidity / 70.0) * 50.0);
  }

  float excessHumidity = humidity - 70.0;
  float minimum = 100.0;
  float maximum = pow(1.05, 30.0) * 100.0;
  float scaled = (pow(1.05, excessHumidity) * 100.0 - minimum) /
                 (maximum - minimum);
  return (int)round(clampFloat(50.0 + scaled * 130.0, 0.0, 180.0));
}


unsigned long sweepDurationForPrecipitation(float precipitation) {
  float rainStrength = clampFloat(
    precipitation / RAIN_FOR_MAX_SPEED_MM_H, 0.0, 1.0
  );
  float duration = DRY_SWEEP_DURATION_MS - rainStrength *
                   (DRY_SWEEP_DURATION_MS - WET_SWEEP_DURATION_MS);
  return (unsigned long)round(duration);
}


unsigned long stepDelayForWeather(int angle, float precipitation) {
  // There are angle steps on the way up and the way down. This makes a dry
  // full sweep span the API interval regardless of the humidity target.
  if (angle <= 0) {
    return DRY_SWEEP_DURATION_MS;
  }
  return max(1UL, sweepDurationForPrecipitation(precipitation) /
                  (unsigned long)(2 * angle));
}


void writeAllServos(int angle) {
  for (uint8_t i = 0; i < NUM_SERVOS; i++) {
    servos[i].write(angle);
  }
}


void applyWeather(float humidity, float precipitation) {
  currentHumidity = clampFloat(humidity, 0.0, 100.0);
  currentPrecipitation = max(0.0f, precipitation);
  targetAngle = humidityToServoAngle(currentHumidity);
  stepDelayMs = stepDelayForWeather(targetAngle, currentPrecipitation);

  if (targetAngle == 0) {
    appliedAngle = 0;
    movingUp = true;
    writeAllServos(appliedAngle);
  }

  // Keep the current motion continuous when weather changes. If the new
  // target is below the current angle, immediately head back toward zero.
  if (appliedAngle >= targetAngle) {
    movingUp = false;
  } else if (appliedAngle <= 0) {
    movingUp = true;
  }

  Serial.print("Humidity: ");
  Serial.print(currentHumidity, 1);
  Serial.print("% | Precipitation: ");
  Serial.print(currentPrecipitation, 2);
  Serial.print(" mm/h | Target: ");
  Serial.print(targetAngle);
  Serial.print(" deg | Full sweep: ");
  Serial.print(sweepDurationForPrecipitation(currentPrecipitation) / 1000.0, 1);
  Serial.print(" s | Step delay: ");
  Serial.print(stepDelayMs);
  Serial.println(" ms");
}


void readWeatherSerial() {
  while (Serial.available() > 0) {
    char character = (char)Serial.read();

    if (character == '\r') {
      continue;
    }
    if (character == '\n') {
      weatherBuffer[weatherBufferLength] = '\0';
      char *comma = strchr(weatherBuffer, ',');
      if (comma != NULL) {
        *comma = '\0';
        char *humidityEnd;
        char *precipitationEnd;
        float humidity = strtof(weatherBuffer, &humidityEnd);
        float precipitation = strtof(comma + 1, &precipitationEnd);

        if (humidityEnd != weatherBuffer && precipitationEnd != comma + 1) {
          applyWeather(humidity, precipitation);
        } else {
          Serial.println("Ignored invalid weather payload.");
        }
      } else if (weatherBufferLength > 0) {
        Serial.println("Ignored weather payload without a comma.");
      }
      weatherBufferLength = 0;
    } else if (weatherBufferLength < WEATHER_BUFFER_SIZE - 1) {
      weatherBuffer[weatherBufferLength++] = character;
    } else {
      // Discard an overlong line so a partial value is never applied.
      weatherBufferLength = 0;
      Serial.println("Ignored overlong weather payload.");
    }
  }
}


void updateServoPosition(unsigned long now) {
  if (targetAngle <= 0 || now - lastServoStepMs < stepDelayMs) {
    return;
  }

  lastServoStepMs = now;
  if (movingUp) {
    appliedAngle++;
    if (appliedAngle >= targetAngle) {
      appliedAngle = targetAngle;
      movingUp = false;
    }
  } else {
    appliedAngle--;
    if (appliedAngle <= 0) {
      appliedAngle = 0;
      movingUp = true;
    }
  }
  writeAllServos(appliedAngle);
}


void setup() {
  Serial.begin(9600);
  for (uint8_t i = 0; i < NUM_SERVOS; i++) {
    servos[i].attach(servoPins[i]);
  }
  writeAllServos(appliedAngle);
  Serial.println("Weather yarn servo controller ready.");
}


void loop() {
  readWeatherSerial();
  updateServoPosition(millis());
}
