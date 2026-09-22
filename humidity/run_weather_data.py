"""FOR ARDUINO!
"""

import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


LATITUDE = 44.9778
LONGITUDE = -93.2650
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
POLL_INTERVAL_SEC = 300
REQUEST_TIMEOUT_SEC = 15

# Change this default to the Mega's port, or supply --port when running.
DEFAULT_ARDUINO_PORT = "/dev/cu.usbmodem141301"
BAUD_RATE = 9600


def fetch_current_weather():
    """Return current relative humidity (%) and precipitation rate (mm/hour)."""
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": "relative_humidity_2m,precipitation",
        "timezone": "auto",
    }
    request_url = f"{WEATHER_URL}?{urlencode(params)}"
    with urlopen(request_url, timeout=REQUEST_TIMEOUT_SEC) as response:
        current = json.load(response)["current"]

    return (
        float(current["relative_humidity_2m"]),
        max(0.0, float(current.get("precipitation", 0.0))),
    )


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Send live humidity and precipitation to an Arduino Mega."
    )
    parser.add_argument(
        "--port",
        default=DEFAULT_ARDUINO_PORT,
        help=f"Mega serial port (default: {DEFAULT_ARDUINO_PORT}).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Send one weather update, then exit.",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Print the serial payload instead of connecting to a Mega.",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    serial_connection = None

    if not args.simulate:
        try:
            import serial
        except ImportError as error:
            print(f"Could not import pyserial: {error}")
            return

        try:
            serial_connection = serial.Serial(args.port, BAUD_RATE, timeout=1)
            # A Mega resets when its serial port opens.
            time.sleep(2)
            print(f"Connected to Arduino Mega on {args.port}")
        except (OSError, serial.SerialException) as error:
            print(f"Could not connect to Arduino Mega: {error}")
            return

    try:
        while True:
            try:
                humidity, precipitation = fetch_current_weather()
                payload = f"{humidity:.2f},{precipitation:.2f}\n"

                if serial_connection is None:
                    print(f"SIMULATED Arduino Mega payload -> {payload.strip()}")
                else:
                    serial_connection.write(payload.encode("utf-8"))
                    print(f"Sent to Arduino Mega -> {payload.strip()}")
            except (HTTPError, URLError, OSError, KeyError, TypeError, ValueError) as error:
                print(f"Weather update failed: {error}")

            if args.once:
                return
            time.sleep(POLL_INTERVAL_SEC)
    except KeyboardInterrupt:
        print("\nStopping weather sender.")
    finally:
        if serial_connection is not None:
            serial_connection.close()


if __name__ == "__main__":
    main()
