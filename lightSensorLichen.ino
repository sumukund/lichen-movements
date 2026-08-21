// Reads 8 piezo vibrotactile sensors and plays a tone per sensor when touched.
// Includes per-sensor debounce so one touch doesn't retrigger repeatedly,
// and Serial output so you can tune the threshold for your actual sensors.

// Pin definitions
// For testing with just one sensor, leave only A0 here. Add pins back in
// as you wire up more sensors — numSensors below adjusts automatically.
const int sensorPins[] = {A1, A2}; // Piezoa sensor pins
const int numSensors = sizeof(sensorPins) / sizeof(sensorPins[0]);
const int buzzerPin = 9; // Piezo buzzer pin

// Threshold for vibration sensor activation — START LOW, then tune.
// Piezo discs spike briefly and much lower than light sensors did.
// Watch the Serial output while tapping the sensor and raise this
// just above your resting/noise level.
const int threshold = 250;

// Minimum time (ms) a sensor must stay quiet before it can trigger again.
// Prevents one tap from re-firing while the piezo disc is still "ringing".
const unsigned long cooldownMs = 500;

// Frequencies for each sensor's sound (in Hz). Add more as you add sensors —
// keep this list at least as long as sensorPins.
const int frequencies[] = {523, 624}; // C4, D4, E4, F4, G4, A4, B4, C5

// Tracks the last time each sensor was allowed to trigger
unsigned long lastTriggerTime[numSensors] = {0};

void setup() {
    Serial.begin(9600); // For tuning: watch raw sensor values in Serial Monitor

    for (int i = 0; i < numSensors; i++) {
        pinMode(sensorPins[i], INPUT);
    }
    pinMode(buzzerPin, OUTPUT);
}

void loop() {
    for (int i = 0; i < numSensors; i++) {
        int sensorValue = analogRead(sensorPins[i]);

        Serial.println(sensorValue); // watch this in Serial Monitor to pick a good threshold

        unsigned long now = millis();
        bool cooledDown = (now - lastTriggerTime[i]) > cooldownMs;

        if (sensorValue < threshold && cooledDown) {
            Serial.print("Sensor ");
            Serial.print(i);
            Serial.print(" triggered, value: ");
            Serial.println(sensorValue);

            tone(buzzerPin, frequencies[i], 100); // Play tone for 200ms (non-blocking version)
            lastTriggerTime[i] = now;
        }
    }
}
