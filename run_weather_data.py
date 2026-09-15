import serial
import time
import requests

# Set your Arduino Mega COM port (e.g., 'COM3' on Windows or '/dev/cu.usbmodemXXXX' on Mac)
arduino_port = "/dev/cu.usbmodem143201"
baud_rate = 9600

ser = serial.Serial(arduino_port, baud_rate, timeout=1)
time.sleep(2)  # Allow connection to settle

url = "https://api.open-meteo.com/v1/forecast?latitude=44.9778&longitude=-93.2650&current=temperature_2m,relative_humidity_2m"

while True:
  try:
    response = requests.get(url).json()
    current = response["current"]
    temp = current["temperature_2m"]
    hum = current["relative_humidity_2m"]
    
    print(response)
    print(current)
    print(temp)
    print(hum)

    payload = f"{temp},{hum}\n"
    ser.write(payload.encode("utf-8"))
    print(f"Sent to Arduino Mega -> {payload.strip()}")

  except Exception as e:
    print(f"Error fetching API: {e}")

  # Update every 10 minutes to respect API rates and keep servos shifting
  time.sleep(600)