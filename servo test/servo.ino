#include <Servo.h>
Servo myServo;

void setup() {
  myServo.attach(9); // Check that your signal wire is in Digital Pin 9
}

void loop() {
  myServo.write(0);
  delay(1000);
  myServo.write(90);
  delay(1000);
  myServo.write(180);
  delay(1000);
}
