#!/usr/bin/env python3

import json
import logging
import subprocess
import time
from os import getenv

import psutil
import serial
from dotenv import load_dotenv

load_dotenv("/etc/rpcooler.conf")

SERIAL_DEVICE_PATH = getenv("SERIAL_DEVICE_PATH", "/dev/ttyACM0")
CPU_TEMP_PATH = getenv("CPU_TEMP_PATH", "/sys/class/thermal/thermal_zone0/temp")
COOLER_ON_TEMP = int(getenv("COOLER_ON_TEMP", "60"))
COOLER_ON_FRAMES = int(getenv("COOLER_ON_FRAMES", "1"))
INTERVAL = int(getenv("INTERVAL_MS", "1000")) / 1000
RAID_DISKS = getenv("RAID_DISKS", "sdb,sdc").split(",")


class Metrics:
    @staticmethod
    def get_cpu_temp() -> dict:
        with open(CPU_TEMP_PATH, "r") as f:
            return {"cpu_temp": int(f.readlines()[0].strip()[:-3])}

    @staticmethod
    def get_memory_metrics() -> dict:
        memory = psutil.virtual_memory()
        return {
            "used_memory": memory.used,
            "total_memory": memory.total,
        }

    @staticmethod
    def get_swap_metrics() -> dict:
        swap = psutil.swap_memory()
        return {
            "swap": swap.used,
            "total_swap": swap.total,
        }

    @staticmethod
    def get_cpu_load() -> dict:
        return {"cpu_load": psutil.cpu_percent(interval=1)}

    @staticmethod
    def get_disk_metrics() -> dict:
        disk = psutil.disk_usage("/")
        return {
            "free_space": disk.free,
            "total_disk_size": disk.total,
        }

    @staticmethod
    def get_raid_state() -> dict:
        mdstat = subprocess.run(["cat", "/proc/mdstat"], capture_output=True, text=True).stdout

        is_raid_active = "active" in mdstat
        if not is_raid_active:
            return {"raid_state": "inactive"}

        present_raid_disks = set(filter(lambda disk: disk in mdstat, RAID_DISKS))
        raid_state = "healthy" if len(present_raid_disks) == len(RAID_DISKS) else "degraded"
        missing_raid_disks = set(RAID_DISKS) - present_raid_disks
        return {"raid_state": raid_state, "missing_raid_disks": list(missing_raid_disks), "raid_disks": RAID_DISKS}

    @staticmethod
    def get_uptime() -> dict:
        return {"uptime": time.time() - psutil.boot_time()}

    @staticmethod
    def get_cpu_frequency() -> dict:
        cpu_freq = psutil.cpu_freq()
        return {
            "freq_current": cpu_freq.current if cpu_freq else None,
            "freq_min": cpu_freq.min if cpu_freq else None,
            "freq_max": cpu_freq.max if cpu_freq else None,
        }

    @classmethod
    def get_all(cls) -> dict:
        metric_getters = [
            cls.get_cpu_temp,
            cls.get_memory_metrics,
            cls.get_swap_metrics,
            cls.get_cpu_load,
            cls.get_disk_metrics,
            cls.get_raid_state,
            cls.get_uptime,
            cls.get_cpu_frequency,
        ]
        metrics = {}
        for get_metric in metric_getters:
            try:
                metrics.update(get_metric())
            except Exception as e:
                logging.error(f"Error in {get_metric.__name__}: {e}")
        return metrics


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

    return lambda t: should_turn_on_cooler(t)


def log_state(metrics: dict) -> None:
    cooler_is_on = metrics.get("cooler_state", False)
    state_text = "\033[92mON\033[0m" if cooler_is_on else "\033[91mOFF\033[0m"
    print(f"Cooler is {state_text} | Metrics: {json.dumps(metrics)}", end="\r")


if __name__ == "__main__":
    should_turn_on_cooler = create_should_turn_on_cooler()
    serial_device = serial.Serial(SERIAL_DEVICE_PATH)

    while serial_device:
        time.sleep(INTERVAL)

        metrics = Metrics.get_all()
        cpu_temp = metrics.get("cpu_temp")

        metrics["cooler_state"] = should_turn_on_cooler(cpu_temp)

        serial_device.write(json.dumps(metrics).encode("utf-8"))
        serial_device.write(b"\n")

        log_state(metrics)
