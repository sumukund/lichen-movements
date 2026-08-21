// Save this as dance_speed_receiver.ino

const int speakerPin = 9; // Pin connected to your piezo buzzer/speaker

// 8 notes spreading across multiple octaves (Lower speed = deeper notes, High speed = high pitches)
const int notes[] = {131, 165, 196, 262, 330, 392, 523, 659}; // C3, E3, G3, C4, E4, G4, C5, E5

void setup() {
  Serial.begin(9600); 
  pinMode(speakerPin, OUTPUT);
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();

    if (command >= '0' && command <= '7') {
      int noteIndex = command - '0';
      tone(speakerPin, notes[noteIndex]); // Play the speed-mapped note
    } 
    else if (command == 'M') {
      noTone(speakerPin); // Mute when dancing stops
    }
  }
}

