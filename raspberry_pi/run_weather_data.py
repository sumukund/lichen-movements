import math
import time
import requests
from gpiozero import AngularServo

# --- Configuration ---
# Coordinates for Minneapolis (change if needed)
LATITUDE = 44.9778
LONGITUDE = -93.2650

# GPIO pins corresponding to the 6 servos
SERVO_PINS = [18, 23, 24, 25, 12, 16]

# Initialize servos with explicit pulse widths for standard 0-180° hobby servos
servos = [
    AngularServo(
        pin, min_angle=0, max_angle=180, min_pulse_width=0.0005, max_pulse_width=0.0025
    )
    for pin in SERVO_PINS
]


def exponential_humidity_to_servo_angle(humidity):
  """Exact math port of your C++ exponential scaling function."""
  if humidity <= 70:
    # Minimal movement for humidity 0-70%
    # Python equivalent of map()
    return (humidity / 70.0) * 50.0
  else:
    excess_humidity = humidity - 70.0
    exp_scaled = math.pow(1.05, excess_humidity)
    base_min = math.pow(1.05, 0) * 100.0
    base_max = math.pow(1.05, 30) * 100.0
    # Map range [base_min, base_max] to [50, 180]
    scaled_val = (exp_scaled * 100.0 - base_min) / (base_max - base_min)
    return 50.0 + scaled_val * 130.0


def fetch_current_humidity():
  """Fetches real-time relative humidity from Open-Meteo API."""
  url = "https://api.open-meteo.com/v1/forecast"
  params = {
      "latitude": LATITUDE,
      "longitude": LONGITUDE,
      "hourly": "relative_humidity_2m",
      "timezone": "auto",
  }
  try:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    # Grab the most recent hourly humidity value from the timeline
    humidity = data["hourly"]["relative_humidity_2m"][-1]
    return float(humidity)
  except Exception as e:
    print(f"Error fetching weather data: {e}")
    return None


def set_all_servos(angle):
  """Updates all 6 servos to a target angle (0 to 180)."""
  for servo in servos:
    servo.angle = angle


def main():
  print("Starting Real-Time Weather Servo Controller...")

  # Initial fetch and setup
  current_humidity = fetch_current_humidity()
  if current_humidity is None:
    current_humidity = 50.0  # Fallback default

  target_angle = exponential_humidity_to_servo_angle(current_humidity)
  print(
      f"Initial Humidity: {current_humidity}% | Target Angle: {target_angle:.1f}°"
  )
  set_all_servos(target_angle)

  # Loop to poll Open-Meteo API every 15 minutes (weather updates hourly, but 15m is safe)
  POLL_INTERVAL_SEC = 900

  try:
    while True:
      time.sleep(POLL_INTERVAL_SEC)
      new_humidity = fetch_current_humidity()
      if new_humidity is not None:
        target_angle = exponential_humidity_to_servo_angle(new_humidity)
        print(
            f"Updated Humidity: {new_humidity}% | New Target Angle:"
            f" {target_angle:.1f}°"
        )
        set_all_servos(target_angle)
  except KeyboardInterrupt:
    print("\nProgram stopped by user. Detaching servos.")
    for servo in servos:
      servo.detach()


if __name__ == "__main__":
  main()