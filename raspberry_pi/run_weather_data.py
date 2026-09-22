#!/usr/bin/env python3
"""
Weather yarn servo controller for Raspberry Pi.

Fetches live weather (relative humidity + precipitation) from the free
Open-Meteo API (no API key needed) and sweeps all servos continuously
0 -> target -> 0 -> target ... until the next refresh, then re-targets.

SETUP
    sudo apt install python3-gpiozero python3-pigpio pigpio
    sudo systemctl enable --now pigpiod      # steadier servo PWM (Pi 4 and older)

RUN
    python3 weather_yarn_servos.py --lat 12.34 --lon -56.78

NOTES
    * Power the servos from an external 5 V supply (not the Pi's 5 V pin) and
      connect its ground to a Pi ground pin.
    * SERVO_PINS are BCM GPIO numbers - change them to match your wiring.
"""

import argparse
import json
import math
import signal
import sys
import threading
import time
import urllib.parse
import urllib.request

from gpiozero import AngularServo

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
LATITUDE = None   
LONGITUDE = None  

SERVO_PINS = [11, 12, 13, 15, 16, 18, 19, 22, 23, 24]   # BCM numbering (NOT the Arduino pins)

REFRESH_INTERVAL_S = 600     # how often to pull new weather
RETRY_INTERVAL_S = 60        # retry delay if an API call fails

DRY_SWEEP_DURATION_S = 75.0
WET_SWEEP_DURATION_S = 60.0
RAIN_FOR_MAX_SPEED_MM_H = 5.0

TICK_S = 0.02                # motion update rate (50 Hz)

# Same pulse range the Arduino Servo library uses (544-2400 us)
MIN_PULSE_S = 0.544 / 1000
MAX_PULSE_S = 2.400 / 1000


# ----------------------------------------------------------------------------
# Weather -> motion math (ported 1:1 from the Arduino sketch)
# ----------------------------------------------------------------------------
def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def round_half_up(x):
    # Matches C's round() (Python's round() uses banker's rounding)
    return int(math.floor(x + 0.5))


def humidity_to_servo_angle(humidity):
    humidity = clamp(humidity, 0.0, 100.0)
    if humidity <= 70.0:
        return round_half_up(humidity / 70.0 * 50.0)

    excess = humidity - 70.0
    minimum = 100.0
    maximum = 1.05 ** 30 * 100.0
    scaled = (1.05 ** excess * 100.0 - minimum) / (maximum - minimum)
    return round_half_up(clamp(50.0 + scaled * 130.0, 0.0, 180.0))


def sweep_duration_for_precipitation(precipitation):
    rain_strength = clamp(precipitation / RAIN_FOR_MAX_SPEED_MM_H, 0.0, 1.0)
    return DRY_SWEEP_DURATION_S - rain_strength * (
        DRY_SWEEP_DURATION_S - WET_SWEEP_DURATION_S
    )


# ----------------------------------------------------------------------------
# Weather API
# ----------------------------------------------------------------------------
def fetch_weather(lat, lon):
    """Return (relative_humidity_percent, precipitation_mm_per_hour)."""
    query = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "current": "relative_humidity_2m,precipitation",
    })
    url = f"https://api.open-meteo.com/v1/forecast?{query}"
    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.load(response)
    current = data["current"]
    return float(current["relative_humidity_2m"]), float(current["precipitation"])


class WeatherPoller(threading.Thread):
    """Fetches weather in the background so a slow network never stalls the servos."""

    def __init__(self, lat, lon):
        super().__init__(daemon=True)
        self.lat, self.lon = lat, lon
        self._lock = threading.Lock()
        self._latest = None
        self._halt = threading.Event()

    def run(self):
        while not self._halt.is_set():
            try:
                reading = fetch_weather(self.lat, self.lon)
                with self._lock:
                    self._latest = reading
                wait = REFRESH_INTERVAL_S
            except Exception as exc:  # network down, bad JSON, etc.
                print(f"Weather fetch failed ({exc}); retrying in {RETRY_INTERVAL_S}s.")
                wait = RETRY_INTERVAL_S
            self._halt.wait(wait)

    def take_latest(self):
        """Return a fresh (humidity, precipitation) once, else None."""
        with self._lock:
            reading, self._latest = self._latest, None
        return reading

    def stop(self):
        self._halt.set()


# ----------------------------------------------------------------------------
# Servo motion
# ----------------------------------------------------------------------------
class YarnSweeper:
    def __init__(self, servos):
        self.servos = servos
        self.angle = 0.0
        self.target = 0
        self.moving_up = True
        self.duration_s = DRY_SWEEP_DURATION_S
        self._last_written = None

    def apply_weather(self, humidity, precipitation):
        humidity = clamp(humidity, 0.0, 100.0)
        precipitation = max(0.0, precipitation)
        self.target = humidity_to_servo_angle(humidity)
        self.duration_s = sweep_duration_for_precipitation(precipitation)

        if self.target == 0:
            self.angle = 0.0
            self.moving_up = True
        elif self.angle >= self.target:
            self.moving_up = False
        elif self.angle <= 0:
            self.moving_up = True

        print(
            f"Humidity: {humidity:.1f}% | Precipitation: {precipitation:.2f} mm/h | "
            f"Target: {self.target} deg | Full sweep: {self.duration_s:.1f} s"
        )

    def update(self, dt):
        """Advance the sweep by dt seconds."""
        if self.target > 0:
            step = (2.0 * self.target / self.duration_s) * dt  # deg this tick
            if self.moving_up:
                self.angle += step
                if self.angle >= self.target:
                    self.angle = float(self.target)
                    self.moving_up = False
            else:
                self.angle -= step
                if self.angle <= 0:
                    self.angle = 0.0
                    self.moving_up = True
        self._write(self.angle)

    def _write(self, angle):
        angle = round(clamp(angle, 0.0, 180.0), 1)
        if angle == self._last_written:
            return
        self._last_written = angle
        for servo in self.servos:
            servo.angle = angle

    def park(self):
        self._write(0.0)
        time.sleep(0.5)


def make_pin_factory():
    """Prefer pigpio (hardware-timed PWM, no jitter); fall back to gpiozero's default."""
    try:
        from gpiozero.pins.pigpio import PiGPIOFactory
        return PiGPIOFactory()
    except Exception as exc:
        print(f"pigpio unavailable ({exc}); using default pin factory (servos may jitter).")
        return None


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Weather yarn servo controller")
    parser.add_argument("--lat", type=float, default=LATITUDE)
    parser.add_argument("--lon", type=float, default=LONGITUDE)
    args = parser.parse_args()
    if args.lat is None or args.lon is None:
        parser.error("set --lat and --lon (or LATITUDE / LONGITUDE at the top of the file)")

    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))  # clean stop under systemd

    factory = make_pin_factory()
    servos = [
        AngularServo(
            pin,
            min_angle=0,
            max_angle=180,
            initial_angle=0,
            min_pulse_width=MIN_PULSE_S,
            max_pulse_width=MAX_PULSE_S,
            pin_factory=factory,
        )
        for pin in SERVO_PINS
    ]

    sweeper = YarnSweeper(servos)
    poller = WeatherPoller(args.lat, args.lon)
    poller.start()
    print("Weather yarn servo controller ready.")

    last = time.monotonic()
    try:
        while True:
            now = time.monotonic()
            dt = min(now - last, 0.5)  # guard against long stalls
            last = now

            reading = poller.take_latest()
            if reading is not None:
                sweeper.apply_weather(*reading)

            sweeper.update(dt)
            time.sleep(TICK_S)
    except KeyboardInterrupt:
        pass
    finally:
        poller.stop()
        sweeper.park()
        for servo in servos:
            servo.detach()
            servo.close()
        print("Stopped.")


if __name__ == "__main__":
    main()