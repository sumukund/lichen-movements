// Four momentary buttons for a VRPN button bridge.
// Wire one side of each button to the pin below and the other side to GND.
// The USB serial output is: W 1, W 0, A 1, ...

const byte buttonPins[] = {2, 3, 4, 5};
const char buttonNames[] = {'W', 'A', 'S', 'D'};
bool lastState[] = {false, false, false, false};

void setup() {
  Serial.begin(115200);

  for (byte i = 0; i < 4; i++) {
    pinMode(buttonPins[i], INPUT_PULLUP);
  }
}

void loop() {
  for (byte i = 0; i < 4; i++) {
    // INPUT_PULLUP means a pressed button reads LOW.
    bool pressed = digitalRead(buttonPins[i]) == LOW;

    if (pressed != lastState[i]) {
      lastState[i] = pressed;
      Serial.print(buttonNames[i]);
      Serial.print(' ');
      Serial.println(pressed ? 1 : 0);
      delay(10);  // tiny debounce delay
    }
  }
}
