
// This code just takes the light sensors and uses them to trigger a sound. when you pass over the tubes of the lichen. 



// Pin definitions
const int sensorPins[8] = {A0, A1, A2, A3, A4, A5, A6, A7}; // Light sensor pins
const int buzzerPin = 9; // Piezo buzzer pin

// Threshold for light sensor activation
const int threshold = 500;

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
            tone(buzzerPin, frequencies[i]); // Play sound
            delay(200); // Wait for the sound to finish
            noTone(buzzerPin); // Stop the sound
        }
    }
}