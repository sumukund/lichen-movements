import cv2
import serial
import time
import numpy as np

# 1. Initialize Serial Port to Arduino Nano
arduino_port = "COM5" 
arduino = serial.Serial(port=arduino_port, baudrate=9600, timeout=0.1)
time.sleep(2) 
print(f"Connected to Arduino on {arduino_port}")

# 2. Open Webcam
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
prev_frame = None

# --- TUNING PARAMETERS ---
MAX_DANCE_SPEED = 2000000  # The speed value where notes hit the absolute highest pitch
MIN_MOTION_CUTOFF = 80000  # Any speed lower than this is treated as standing still (Muted)
# -------------------------

print("Dance Speed Synth Active. Move to play higher or lower tones. Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break
        
    frame = cv2.flip(frame, 1)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    if prev_frame is None:
        prev_frame = gray
        continue

    # Calculate raw structural changes between frames
    frame_delta = cv2.absdiff(prev_frame, gray)
    _, thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)
    
    # Raw movement speed number
    movement_speed = int(np.sum(thresh))
    prev_frame = gray

    # 3. Translate raw speed into 8 distinct tiers (0 to 7)
    if movement_speed < MIN_MOTION_CUTOFF:
        # Standing still or subtle background noise -> Mute
        arduino.write(b'M')
        status_text = "Muted (Still)"
        text_color = (0, 0, 255)
        bar_height = 0
    else:
        # Normalize the speed value between 0.0 and 1.0 based on your MAX limit
        normalized_speed = min(movement_speed / MAX_DANCE_SPEED, 1.0)
        
        # Convert the decimal scale into an integer index from 0 to 7
        note_index = int(normalized_speed * 7)
        
        # Send raw tier byte over USB
        arduino.write(str(note_index).encode())
        status_text = f"Dancing! Pitch Tier: {note_index}"
        text_color = (0, 255, 0)
        bar_height = int(normalized_speed * 200)

    # 4. Visual Interface Layout
    # Render an on-screen audio/speed volume visualizer bar
    cv2.rectangle(frame, (30, 250), (60, 250 - bar_height), text_color, cv2.FILLED)
    cv2.rectangle(frame, (30, 250), (60, 50), (255, 255, 255), 2)
    
    # Debug metrics overlay
    cv2.putText(frame, status_text, (80, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2)
    cv2.putText(frame, f"Raw Speed: {movement_speed}", (80, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    cv2.imshow("Dance Speed Synthesizer", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
arduino.close()

