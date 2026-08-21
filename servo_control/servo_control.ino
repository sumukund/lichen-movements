// Save this as dance_servo_controller.ino
#include <Servo.h>

Servo myServo;  // Create a servo object to control our motor
const int servoPin = 9; // Pin connected to the servo signal wire

// Map the 8 speed tiers (0-7) to 8 distinct angles (from 0 to 180 degrees)
const int angles[] = {0, 25, 50, 75, 100, 125, 150, 180};

// Track the current target angle to prevent flooded redundant commands
int currentAngle = 0; 

void setup() {
  Serial.begin(9600); // Initialize USB communication at 9600 baud
  myServo.attach(servoPin); // Link the servo object to pin 9
  myServo.write(0); // Start the servo at 0 degrees
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();

    // If Python sends a speed tier character digit between '0' and '7'
    if (command >= '0' && command <= '7') {
      int speedTier = command - '0'; // Convert character to integer index
      int targetAngle = angles[speedTier]; // Look up the designated angle
      
      myServo.write(targetAngle); // Tell the servo to rotate to the position
    }
    // Optional 'M' Mute condition: What should the servo do when you stop moving?
    else if (command == 'M') {
      myServo.write(0); // Return back to the home base (0 degrees) when resting
    }
  }
}
