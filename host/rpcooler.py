#!/usr/bin/env python3
import logging
import time
from os import getenv

import serial
from dotenv import load_dotenv

load_dotenv("/etc/rpcooler.conf")

SERIAL_DEVICE_PATH = getenv("SERIAL_DEVICE_PATH", "/dev/ttyACM0")
CPU_TEMP_PATH = getenv("CPU_TEMP_PATH", "/sys/class/thermal/thermal_zone0/temp")
COOLER_ON_TEMP = int(getenv("COOLER_ON_TEMP"))
COOLER_ON_FRAMES = int(getenv("COOLER_ON_FRAMES", "0"))
INTERVAL = int(getenv("INTERVAL_MS", "1000")) / 1000


def get_cpu_temp() -> int | None:
    try:
        with open(CPU_TEMP_PATH, "r") as f:
            return int(f.readlines()[0].strip()[:-3])
    except Exception as exp:
        logging.error("Couldn't parse cpu temperature: %s", exp)
        return None


def create_should_turn_on_cooler():
    frame = None

    def should_turn_on_cooler(temperature: int) -> bool:
        nonlocal frame
        if temperature > COOLER_ON_TEMP:
            frame = 0
            return True
        if frame is not None and frame < COOLER_ON_FRAMES:
            frame += 1
            return True
        frame = None
        return False

    return lambda t: should_turn_on_cooler(t).to_bytes(1, "big")


if __name__ == "__main__":
    should_turn_on_cooler = create_should_turn_on_cooler()
    serial_device = serial.Serial(SERIAL_DEVICE_PATH)
    while serial_device:
        time.sleep(INTERVAL)
        cpu_temp = get_cpu_temp()
        if cpu_temp is None:
            continue
        serial_device.write(should_turn_on_cooler(cpu_temp))
        serial_device.write(b"\n")
