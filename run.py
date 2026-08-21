import cv2
import serial
import time
import math
from cvzone.HandTrackingModule import HandDetector

# 1. Initialize Serial Port to Arduino Nano
arduino_port = "COM4" 
arduino = serial.Serial(port=arduino_port, baudrate=9600, timeout=0.1)
time.sleep(2) # Safe reset pause
print(f"Connected to Arduino on {arduino_port}")

# 2. Open Webcam
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# 3. Initialize Hand Detector (maxHands=1 tracks your active instrument hand)
detector = HandDetector(maxHands=1, detectionCon=0.7)

# --- CONFIGURATION PARAMETERS ---
PLUCK_THRESHOLD = 35  # Pixels between thumb & middle finger tip. Lower = must touch tighter.
# --------------------------------

print("Nuanced Spatial Hand Instrument active. Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    column_width = w // 8 # Divide screen into 8 spatial zones

    # Find hands and draw bounding boxes/skeleton lines automatically
    hands, frame = detector.findHands(frame, draw=True)

    is_plucking = False
    active_column = -1

    # Draw the 8 vertical visual boundary zones on the screen
    for i in range(1, 8):
        x_line = i * column_width
        cv2.line(frame, (x_line, 0), (x_line, h), (100, 100, 100), 1)

    if hands:
        hand = hands[0] # Focus on the main hand detected
        lmList = hand["lmList"] # List of 21 landmark coordinates
        
        # Landmark 4 is Tip of Thumb, Landmark 12 is Tip of Middle Finger
        thumb_tip = lmList[4]
        middle_tip = lmList[12]

        # Calculate Euclidean distance between thumb tip and middle finger tip
        distance = math.hypot(middle_tip[0] - thumb_tip[0], middle_tip[1] - thumb_tip[1])

        # Track the center of your palm to see which column you're hovering in
        palm_center_x = hand["center"][0]
        active_column = min(palm_center_x // column_width, 7) # Keep within 0-7 array indices

        # Optional: Add a transparent or visual highlight to the active column zone
        x_start = active_column * column_width
        cv2.rectangle(frame, (x_start, 0), (x_start + column_width, h), (0, 255, 0), 2)

        # Check if gesture triggers the pluck threshold distance
        if distance < PLUCK_THRESHOLD:
            is_plucking = True

    # 4. Process Gesture Logic & Transmit Results over USB
    if is_plucking and active_column != -1:
        # Convert index number (0-7) to bytes and transmit
        command_to_send = str(active_column).encode()
        arduino.write(command_to_send)
        status_text = f"🎵 Plucking Note in Zone {active_column}"
        text_color = (0, 255, 0)
    else:
        arduino.write(b'M') # Send Mute command to Arduino
        status_text = "Idle (Bring thumb & middle finger together)"
        text_color = (0, 0, 255)

    # 5. UI Status Text Overlays
    cv2.putText(frame, status_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2)
    cv2.imshow('Spatial Vision Synthesizer', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
arduino.close()
