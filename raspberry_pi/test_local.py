#!/usr/bin/env python3
"""Replay the weather servo controller against the local historical CSV."""

import argparse
import csv
import math
from pathlib import Path


HISTORY_FILE = Path(__file__).with_name("twin_cities_weather_history.csv")
DRY_SWEEP_DURATION_S = 75.0
WET_SWEEP_DURATION_S = 25.0
RAIN_FOR_MAX_SPEED_MM_H = 5.0


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def round_half_up(value):
    return int(math.floor(value + 0.5))


def humidity_to_servo_angle(humidity):
    humidity = clamp(humidity, 0.0, 100.0)
    if humidity <= 70.0:
        return round_half_up(humidity / 70.0 * 50.0)
    excess = humidity - 70.0
    maximum = 1.05**30 * 100.0
    scaled = (1.05**excess * 100.0 - 100.0) / (maximum - 100.0)
    return round_half_up(clamp(50.0 + scaled * 130.0, 0.0, 180.0))


def sweep_duration_for_precipitation(precipitation):
    rain = clamp(precipitation / RAIN_FOR_MAX_SPEED_MM_H, 0.0, 1.0)
    return DRY_SWEEP_DURATION_S - rain * (
        DRY_SWEEP_DURATION_S - WET_SWEEP_DURATION_S
    )


def step_delay_for_weather(angle, precipitation):
    if angle <= 0:
        return DRY_SWEEP_DURATION_S
    return sweep_duration_for_precipitation(precipitation) / (2 * angle)


def read_history(path):
    """Load every valid hourly reading, with a useful error for malformed CSVs."""
    required = {"time", "relative_humidity_2m", "precipitation_mm"}
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

        rows = []
        for line, row in enumerate(reader, start=2):
            try:
                rows.append((
                    row["time"],
                    float(row["relative_humidity_2m"]),
                    float(row["precipitation_mm"]),
                ))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid weather value on CSV line {line}: {exc}") from exc
    if not rows:
        raise ValueError(f"No weather readings found in {path}")
    return rows


def replay_history(path, limit=None):
    rows = read_history(path)
    if limit is not None:
        rows = rows[:limit]

    print(f"Replaying {len(rows):,} hourly readings from {path}\n")
    print("Timestamp           RH     Rain   Target  Sweep   Step delay")
    print("------------------- -----  ------  ------  ------  ----------")
    for timestamp, humidity, precipitation in rows:
        target = humidity_to_servo_angle(humidity)
        sweep = sweep_duration_for_precipitation(precipitation)
        delay = step_delay_for_weather(target, precipitation)
        print(
            f"{timestamp:19} {humidity:5.1f}%  {precipitation:6.2f}  "
            f"{target:4d} deg  {sweep:5.1f}s  {delay * 1000:8.0f} ms"
        )
    print(f"\nFinished replay of {len(rows):,} readings.")


def main():
    parser = argparse.ArgumentParser(
        description="Replay the servo controller calculations for weather CSV data."
    )
    parser.add_argument(
        "csv", nargs="?", type=Path, default=HISTORY_FILE,
        help=f"weather history CSV (default: {HISTORY_FILE.name})",
    )
    parser.add_argument(
        "--limit", type=int,
        help="replay only the first N rows (default: replay all rows)",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    try:
        replay_history(args.csv, args.limit)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
