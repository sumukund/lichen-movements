// Reads 8 piezo vibrotactile sensors and plays a tone per sensor when touched.
// Includes per-sensor debounce so one touch doesn't retrigger repeatedly,
// and Serial output so you can tune the threshold for your actual sensors.

// Pin definitions
const int sensorPins[8] = {A0, A1, A2, A3, A4, A5, A6, A7}; // Piezo sensor pins
const int buzzerPin = 9; // Piezo buzzer pin

// Threshold for vibration sensor activation — START LOW, then tune.
// Piezo discs spike briefly and much lower than light sensors did.
// Watch the Serial output while tapping the sensor and raise this
// just above your resting/noise level.
const int threshold = 40;

// Minimum time (ms) a sensor must stay quiet before it can trigger again.
// Prevents one tap from re-firing while the piezo disc is still "ringing".
const unsigned long cooldownMs = 300;

// Frequencies for each sensor's sound (in Hz)
const int frequencies[8] = {262, 294, 330, 349, 392, 440, 494, 523}; // C4, D4, E4, F4, G4, A4, B4, C5

// Tracks the last time each sensor was allowed to trigger
unsigned long lastTriggerTime[8] = {0, 0, 0, 0, 0, 0, 0, 0};

void setup() {
    Serial.begin(9600); // For tuning: watch raw sensor values in Serial Monitor

    for (int i = 0; i < 8; i++) {
        pinMode(sensorPins[i], INPUT);
    }
    pinMode(buzzerPin, OUTPUT);
}

void loop() {
    for (int i = 0; i < 8; i++) {
        int sensorValue = analogRead(sensorPins[i]);

        // Uncomment to watch raw values for tuning (noisy with all 8 printing at once —
        // easiest to test one sensor at a time by commenting out the others' pins above)
        // Serial.println(sensorValue);

        unsigned long now = millis();
        bool cooledDown = (now - lastTriggerTime[i]) > cooldownMs;

        if (sensorValue > threshold && cooledDown) {
            Serial.print("Sensor ");
            Serial.print(i);
            Serial.print(" triggered, value: ");
            Serial.println(sensorValue);

            tone(buzzerPin, frequencies[i], 200); // Play tone for 200ms (non-blocking version)
            lastTriggerTime[i] = now;
        }
    }
}
