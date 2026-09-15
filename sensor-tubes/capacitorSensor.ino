
#include <CapacitiveSensor.h>

CapacitiveSensor capsensors[8] = {
    CapacitiveSensor(4, 2), // Sensor 1: send pin 4, receive pin 2
    CapacitiveSensor(4, 3), // Sensor 2: send pin 4, receive pin 3
    CapacitiveSensor(4, 5), // Sensor 3: send pin 4, receive pin 5
    CapacitiveSensor(4, 6), // Sensor 4: send pin 4, receive pin 6
    CapacitiveSensor(4, 7), // Sensor 5: send pin 4, receive pin 7
    CapacitiveSensor(4, 8), // Sensor 6: send pin 4, receive pin 8
    CapacitiveSensor(4, 10), // Sensor 7: send pin 4, receive pin 10
    CapacitiveSensor(4, 11)  // Sensor 8: send pin 4, receive pin 11
};

// Threshold for capacitive sensor activation
const long capThreshold = 1000;

// Define sensor pins and buzzer pin
const int sensorPins[8] = {2, 3, 5, 6, 7, 8, 10, 11}; // Corresponding to the receive pins
const int buzzerPin = 9; // Pin for the buzzer
const int threshold = 500; // Activation threshold for sensors



// Frequencies for each ball's sound (in Hz)
const int frequencies[8] = {262, 294, 330, 349, 392, 440, 494, 523}; // C4, D4, E4, F4, G4, A4, B4, C5

void setup() {
    // Initialize sensor pins as input
    for (int i = 0; i < 8; i++) {
        pinMode(sensorPins[i], INPUT);
    }
    
    // Initialize buzzer pin as output
    pinMode(buzzerPin, OUTPUT);
}

void loop() {
    for (int i = 0; i < 8; i++) {
        int sensorValue = analogRead(sensorPins[i]); // Read sensor value
        
        if (sensorValue > threshold) { // Check if sensor is triggered
            tone(buzzerPin, frequencies[i], 200); // Play sound for 200ms
            delay(200); // Wait for the sound to finish
        }
    }
}