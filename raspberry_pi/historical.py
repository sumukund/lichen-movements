import argparse
import csv
import math
from pathlib import Path
import time
from gpiozero import AngularServo

# ---------- configuration ----------

CSV_FILE = Path(__file__).with_name("twin_cities_weather_history.csv") 
SERVO_PINS = [17, 18, 4, 22, 23, 24, 25, 5, 6, 26]     # BCM GPIO numbers

REFRESH_S = 60  # Refresh CSV reading every 60 seconds
RETRY_S = 10    # Retry sooner if reading CSV fails

# Time for one full 0 -> target -> 0 cycle in seconds.
DRY_SWEEP_DURATION_S = 25.0  # Adjust sweep speed as needed
WET_SWEEP_DURATION_S = 15.0
RAIN_FOR_MAX_SPEED_MM_H = 5.0


# ---------- calculations ----------


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def round_half_up(x):
    return int(math.floor(x + 0.5))


def humidity_to_servo_angle(humidity):
    """Exaggerated mapping across typical ambient humidity range (30% to 85%)."""
    humidity = clamp(humidity, 0.0, 100.0)
    min_rh, max_rh = 30.0, 85.0

    if humidity <= min_rh:
        return 0
    if humidity >= max_rh:
        return 180

    scaled = (humidity - min_rh) / (max_rh - min_rh)
    return round_half_up(scaled * 180.0)


def sweep_duration_for_precipitation(precipitation):
    rain = clamp(precipitation / RAIN_FOR_MAX_SPEED_MM_H, 0.0, 1.0)
    return DRY_SWEEP_DURATION_S - rain * (
        DRY_SWEEP_DURATION_S - WET_SWEEP_DURATION_S
    )


def step_delay_for_weather(angle, precipitation):
    if angle <= 0:
        return DRY_SWEEP_DURATION_S
    return sweep_duration_for_precipitation(precipitation) / (2 * angle)


# ---------- CSV reader ----------


def fetch_csv_reading(csv_path=CSV_FILE):
    """Reads the latest reading (last row) from the CSV file."""
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path.resolve()}")

    with path.open("r", encoding="utf-8") as source:
        rows = [row for row in csv.reader(source) if row]

    if not rows:
        raise ValueError(f"CSV file is empty: {path.resolve()}")

    last_row = rows[-1]

    # Format: timestamp, humidity, precipitation (e.g. 2025-11-06T09:00,79,0.0)
    try:
        humidity = float(last_row[1])
        precipitation = float(last_row[2])
        timestamp = last_row[0]
        return timestamp, humidity, precipitation
    except (IndexError, ValueError) as exc:
        raise ValueError(f"Could not parse CSV row {last_row}: {exc}") from exc


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
    parser.add_argument(
        "--csv",
        type=Path,
        default=CSV_FILE,
        help="Path to CSV file containing readings",
    )
    parser.add_argument(
        "--pins",
        help="BCM GPIO numbers of the servo signal wires, e.g. 17,18,27,22",
    )
    args = parser.parse_args()

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
    print(f"CSV weather yarn servo controller ready. Reading from: {args.csv}")

    try:
        while True:
            # ---- read CSV every minute ----
            if time.monotonic() >= next_refresh:
                try:
                    timestamp, humidity, precipitation = fetch_csv_reading(args.csv)
                    target = humidity_to_servo_angle(humidity)
                    step_delay = step_delay_for_weather(target, precipitation)
                    sweep_s = sweep_duration_for_precipitation(precipitation)
                    next_refresh = time.monotonic() + REFRESH_S

                    print(
                        f"[{timestamp}] Humidity: {humidity:.1f}% | Precipitation: {precipitation:.2f} mm/h | "
                        f"Target: {target} deg | Full sweep: {sweep_s:.1f} s | "
                        f"Step delay: {step_delay * 1000:.0f} ms"
                    )

                    if target == 0:
                        print(
                            "Target is 0 deg (humidity too low), servos idling at 0."
                        )

                except Exception as exc:
                    next_refresh = time.monotonic() + RETRY_S
                    print(
                        f"CSV read failed ({exc}); keeping target {target} deg, retry in {RETRY_S}s."
                    )

                if target == 0:
                    angle, moving_up = 0, True
                    write_all(0)
                elif angle >= target:
                    moving_up = False

            if target <= 0:
                time.sleep(1)
                continue

            # ---- continuous 1-degree sweeps between 0 and target ----
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
