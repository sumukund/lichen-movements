#!/usr/bin/env python3
"""
Weather yarn servo controller - Raspberry Pi port of the Arduino sketch.

Every 15 minutes: fetch humidity + precipitation, then
  * humidity      -> target angle
  * precipitation -> sweep speed (rain makes the servos move faster)
and move all servos 0 -> target -> 0 -> target ... one degree at a time
until the next refresh.

SETUP (Pi 3B)
    sudo apt install pigpio python3-pigpio python3-gpiozero
    sudo systemctl enable --now pigpiod

RUN
    python3 weather_yarn_servos.py --lat 12.34 --lon -56.78 --pins 17,18,27,22,23,24
"""

import argparse
import csv
from datetime import date, datetime, timedelta
import json
import math
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import urlopen
import openmeteo_requests

import pandas as pd
import requests_cache
from gpiozero import AngularServo
from retry_requests import retry

LATITUDE = None  # or use --lat / --lon
LONGITUDE = None

SERVO_PINS = [17, 18, 21, 22, 23, 24, 25, 19, 26, 20]  # BCM GPIO numbers (or use --pins)

REFRESH_S = 15 * 60  # next API refresh
RETRY_S = 60  # if the API call fails, try again sooner

# Time for one full 0 -> target -> 0 cycle.
DRY_SWEEP_DURATION_S = 75.0  # no rain
WET_SWEEP_DURATION_S = 25.0  # heavy rain (3x faster)
RAIN_FOR_MAX_SPEED_MM_H = 5.0  # rain rate at/above which speed is maxed
HISTORICAL_FILE = Path(__file__).with_name("twin_cities_weather_history.csv")
HISTORICAL_LATITUDE = 44.9778
HISTORICAL_LONGITUDE = -93.2650


# ---------- calculations ----------


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def round_half_up(x):
    return int(math.floor(x + 0.5))  # same as C round()


def humidity_to_servo_angle(humidity):
    humidity = clamp(humidity, 0.0, 100.0)
    if humidity <= 70.0:
        return round_half_up(humidity / 70.0 * 50.0)
    excess = humidity - 70.0
    minimum = 100.0
    maximum = 1.05**30 * 100.0
    scaled = (1.05**excess * 100.0 - minimum) / (maximum - minimum)
    return round_half_up(clamp(50.0 + scaled * 130.0, 0.0, 180.0))


def sweep_duration_for_precipitation(precipitation):
    """Full-cycle time in seconds: DRY with no rain, blending to WET at max rain."""
    rain = clamp(precipitation / RAIN_FOR_MAX_SPEED_MM_H, 0.0, 1.0)
    return DRY_SWEEP_DURATION_S - rain * (
        DRY_SWEEP_DURATION_S - WET_SWEEP_DURATION_S
    )


def step_delay_for_weather(angle, precipitation):
    """Seconds to wait between 1-degree steps."""
    if angle <= 0:
        return DRY_SWEEP_DURATION_S
    return sweep_duration_for_precipitation(precipitation) / (2 * angle)


# ---------- weather API (Open-Meteo, no key needed) ----------


def fetch_weather(lat, lon):
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["relative_humidity_2m", "precipitation"],
    }
    responses = openmeteo.weather_api(url, params=params)

    response = responses[0]
    current = response.Current()

    current_relative_humidity_2m = current.Variables(0).Value()
    current_precipitation = current.Variables(1).Value()

    return current_relative_humidity_2m, current_precipitation


def download_historical_weather(path=HISTORICAL_FILE):
    """Save the preceding year of hourly Twin Cities weather as a CSV backup."""
    end = date.today() - timedelta(days=5)  # archive data has a short publication delay
    start = end - timedelta(days=364)
    query = urlencode({
            "latitude": HISTORICAL_LATITUDE,
            "longitude": HISTORICAL_LONGITUDE,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "hourly": "relative_humidity_2m,precipitation",
            "timezone": "America/Chicago",
        })
    with urlopen(
        f"https://archive-api.open-meteo.com/v1/archive?{query}", timeout=60
    ) as response:
        hourly = json.load(response)["hourly"]
    rows = zip(hourly["time"], hourly["relative_humidity_2m"], hourly["precipitation"])
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(("time", "relative_humidity_2m", "precipitation_mm"))
        writer.writerows(rows)
    print(f"Saved one year of hourly Twin Cities weather to {path}")


def fetch_historical_fallback(path=HISTORICAL_FILE, now=None):
    """Use the prior year's reading for the same local month, day, and hour."""
    now = now or datetime.now()
    try:
        target = now.replace(year=now.year - 1)
    except ValueError:  # February 29 has no matching day in a non-leap year.
        target = now.replace(year=now.year - 1, day=28)
    with Path(path).open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise ValueError(f"Historical weather backup is empty: {path}")
    row = min(rows, key=lambda item: abs(
        (datetime.fromisoformat(item["time"]) - target).total_seconds()
    ))
    return float(row["relative_humidity_2m"]), float(row["precipitation_mm"])


# ---------- servos ----------


def make_pin_factory():
    try:
        from gpiozero.pins.pigpio import PiGPIOFactory

        return PiGPIOFactory()
    except Exception as exc:
        print(f"pigpio not available ({exc}); using default pin factory.")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, default=44.97997)
    parser.add_argument("--lon", type=float, default=-93.26384)
    parser.add_argument(
        "--historical", action="store_true",
        help="download and save the past year of hourly Twin Cities humidity and precipitation, then exit",
    )
    parser.add_argument(
        "--pins",
        help="BCM GPIO numbers of the servo signal wires, e.g. 17,18,27,22,23,24",
    )
    args = parser.parse_args()
    if args.historical:
        download_historical_weather()
        return
    if args.lat is None or args.lon is None:
        parser.error(
            "set --lat and --lon (or LATITUDE / LONGITUDE in the file)"
        )

    pins = [int(p) for p in args.pins.split(",")] if args.pins else SERVO_PINS
    factory = make_pin_factory()
    print(
        f"Pin factory: {type(factory).__name__ if factory else 'gpiozero default'} | BCM pins: {pins}"
    )
    servos = [
        AngularServo(
            pin,
            min_angle=0,
            max_angle=180,
            initial_angle=0,
            min_pulse_width=0.544 / 1000,
            max_pulse_width=2.4 / 1000,
            pin_factory=factory,
        )
        for pin in pins
    ]

    def write_all(angle):
        for servo in servos:
            servo.angle = angle

    angle = 0
    target = 0
    moving_up = True
    step_delay = 1.0
    next_refresh = 0.0
    print("Weather yarn servo controller ready.")

    try:
        while True:
            # ---- refresh weather every 15 minutes ----
            if time.monotonic() >= next_refresh:
                try:
                    humidity, precipitation = fetch_weather(
                        args.lat, args.lon
                    )
                    target = humidity_to_servo_angle(humidity)
                    step_delay = step_delay_for_weather(target, precipitation)
                    sweep_s = sweep_duration_for_precipitation(precipitation)
                    next_refresh = time.monotonic() + REFRESH_S
                    print(
                        f"Humidity: {humidity:.1f}% | Precipitation: {precipitation:.2f} mm/h | "
                        f"Target: {target} deg | Full sweep: {sweep_s:.1f} s | "
                        f"Step delay: {step_delay * 1000:.0f} ms"
                    )
                    if target == 0:
                        print(
                            "Target is 0 deg (humidity too low), so the servos stay put."
                        )
                except Exception as exc:
                    try:
                        humidity, precipitation = fetch_historical_fallback()
                        target = humidity_to_servo_angle(humidity)
                        step_delay = step_delay_for_weather(target, precipitation)
                        next_refresh = time.monotonic() + REFRESH_S
                        print(
                            f"Live weather failed ({exc}); using prior-year reading "
                            f"from {datetime.now().year - 1} ({humidity:.1f}% RH, "
                            f"{precipitation:.2f} mm precipitation)."
                        )
                    except Exception as fallback_exc:
                        next_refresh = time.monotonic() + RETRY_S
                        print(
                            f"Weather fetch failed ({exc}) and historical fallback is unavailable "
                            f"({fallback_exc}); keeping current target, retry in {RETRY_S}s."
                        )

                if target == 0:
                    angle, moving_up = 0, True
                    write_all(0)
                elif angle >= target:
                    moving_up = False

            if target <= 0:
                time.sleep(1)
                continue

            # ---- one 1-degree step, back and forth between 0 and target ----
            if moving_up:
                angle += 1
                if angle >= target:
                    angle = target
                    moving_up = False
            else:
                angle -= 1
                if angle <= 0:
                    angle = 0
                    moving_up = True
            write_all(angle)
            time.sleep(step_delay)

    except KeyboardInterrupt:
        pass
    finally:
        write_all(0)
        time.sleep(0.5)
        for servo in servos:
            servo.detach()
            servo.close()
        print("Stopped.")


if __name__ == "__main__":
    main()
