import json
import select
import sys
import time

import utime
from machine import SPI, Pin
from st7789_ext import ST7789

TFT_WIDTH = 128
TFT_HEIGHT = 160
READ_TIMEOUT_SEC = 0.05
EMERGENCY_BACKOFF_AFTER_SEC = 50
TICKS_TO_EMERGENCY_BACKOFF = EMERGENCY_BACKOFF_AFTER_SEC // READ_TIMEOUT_SEC

ONBOARD_LED = Pin(25, Pin.OUT)
COOLER_PIN = Pin(0, Pin.OUT)
TFT_BACKLIGHT_PIN = Pin(12, Pin.OUT)

display = ST7789(
    SPI(1, baudrate=40000000, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11)),
    TFT_WIDTH,
    TFT_HEIGHT,
    reset=Pin(19, Pin.OUT),
    dc=Pin(21, Pin.OUT),
    cs=Pin(20, Pin.OUT),
)

COLOR_GREEN = display.color(0, 255, 0)
COLOR_RED = display.color(255, 0, 0)
COLOR_WHITE = display.color(255, 255, 255)
COLOR_BLACK = display.color(0, 0, 0)
COLOR_GRAY = display.color(80, 80, 80)

GIGABYTE = 1024**3


def interpolate_color(value, min_value, max_value):
    value = max(min_value, min(value, max_value))
    normalized = (value - min_value) / (max_value - min_value)

    if normalized < 0.5:
        ratio = normalized * 2
        red = 0
        green = int(ratio * 255)
        blue = int((1 - ratio) * 255)
    else:
        ratio = (normalized - 0.5) * 2
        red = int(ratio * 255)
        green = int((1 - ratio) * 255)
        blue = 0

    return display.color(red, green, blue)


def get_cpu_load(metrics):
    cpu_load = metrics.get("cpu_load", 0)
    return f"{cpu_load}%", interpolate_color(cpu_load, 0, 100)


def get_cpu_freq(metrics):
    freq_current = metrics.get("freq_current", 0)
    freq_min = metrics.get("freq_min", 0)
    freq_max = metrics.get("freq_max", 0)
    return f"{freq_current / 1000:.1f}GHz", interpolate_color(freq_current, freq_min, freq_max)


def get_cpu_temp(metrics):
    cpu_temp = metrics.get("cpu_temp", 0)
    return str(cpu_temp), interpolate_color(cpu_temp, 30, 100)


def get_ram_usage(metrics):
    used_memory = metrics.get("used_memory", 0) / GIGABYTE
    total_memory = metrics.get("total_memory", 0) / GIGABYTE
    ram_usage = (used_memory / total_memory) * 100 if total_memory else 0
    return (
        f"{used_memory:.1f}/{total_memory:.1f} GB",
        interpolate_color(ram_usage, 0, 100),
    )


def get_swap_usage(metrics):
    swap_used = metrics.get("swap", 0) / GIGABYTE
    swap_total = metrics.get("total_swap", 0) / GIGABYTE
    swap_usage = (swap_used / swap_total) * 100 if swap_total else 0
    return (
        f"{swap_used:.1f}/{swap_total:.1f} GB",
        interpolate_color(swap_usage, 0, 100),
    )


def get_disk_usage(metrics):
    free_space = metrics.get("free_space", 0) / GIGABYTE
    total_disk_size = metrics.get("total_disk_size", 0) / GIGABYTE
    used_space = total_disk_size - free_space
    return (
        f"{used_space:.0f}/{total_disk_size:.0f} GB",
        interpolate_color(used_space, 0, total_disk_size),
    )


def get_external_storages(metrics):
    external_storages = metrics.get("external_storages", [])
    for storage in external_storages:
        location = storage.get("location", "Unknown")
        usage, color = get_disk_usage(storage)
        yield f"{location} {usage}", color


def get_raid_state(metrics):
    raid_state = metrics.get("raid_state", "inactive")
    color = COLOR_GREEN if raid_state == "healthy" else COLOR_RED
    return raid_state, color


def get_uptime(metrics):
    uptime_sec = int(metrics.get("uptime", 0))
    days = uptime_sec // (24 * 3600)
    hours = (uptime_sec % (24 * 3600)) // 3600
    minutes = (uptime_sec % 3600) // 60
    uptime = f"{days}d {hours}h {minutes}m"
    return uptime, COLOR_GRAY


def get_time(metrics):
    timestamp = metrics.get("timestamp", 0)
    _, _, _, hours, minutes, seconds, *_ = utime.localtime(timestamp + 3 * 3600)
    formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return formatted_time, COLOR_GRAY


def get_cooler_state(metrics):
    cooler_state = metrics.get("cooler_state", False)
    color = COLOR_GREEN if cooler_state else COLOR_RED
    return "ON" if cooler_state else "OFF", color


def display_metrics(metrics):
    row_height = 15

    display.rect(0, 0, TFT_WIDTH, row_height, COLOR_BLACK, fill=True)
    display.text(0, 0, *get_time(metrics), bgcolor=COLOR_BLACK)

    display.rect(55, row_height, TFT_WIDTH, row_height * 2, COLOR_BLACK, fill=True)
    display.text(0, row_height, "Uptime", fgcolor=COLOR_WHITE, bgcolor=COLOR_BLACK)
    display.text(55, row_height, *get_uptime(metrics), bgcolor=COLOR_BLACK)

    display.rect(30, row_height * 2, TFT_WIDTH, row_height * 3, COLOR_BLACK, fill=True)
    display.text(0, row_height * 2, "CPU", fgcolor=COLOR_WHITE, bgcolor=COLOR_BLACK)
    display.text(30, row_height * 2, *get_cpu_load(metrics), bgcolor=COLOR_BLACK)
    display.text(80, row_height * 2, *get_cpu_freq(metrics), bgcolor=COLOR_BLACK)

    display.rect(70, row_height * 3, TFT_WIDTH, row_height * 4, COLOR_BLACK, fill=True)
    display.text(0, row_height * 3, "CPU-temp", fgcolor=COLOR_WHITE, bgcolor=COLOR_BLACK)
    display.text(70, row_height * 3, *get_cpu_temp(metrics), bgcolor=COLOR_BLACK)

    display.rect(60, row_height * 4, TFT_WIDTH, row_height * 5, COLOR_BLACK, fill=True)
    display.text(0, row_height * 4, "Cooler", fgcolor=COLOR_WHITE, bgcolor=COLOR_BLACK)
    display.text(60, row_height * 4, *get_cooler_state(metrics), bgcolor=COLOR_BLACK)

    display.rect(40, row_height * 5, TFT_WIDTH, row_height * 6, COLOR_BLACK, fill=True)
    display.text(0, row_height * 5, "RAM", fgcolor=COLOR_WHITE, bgcolor=COLOR_BLACK)
    display.text(40, row_height * 5, *get_ram_usage(metrics), bgcolor=COLOR_BLACK)

    display.rect(45, row_height * 6, TFT_WIDTH, row_height * 7, COLOR_BLACK, fill=True)
    display.text(0, row_height * 6, "Swap", fgcolor=COLOR_WHITE, bgcolor=COLOR_BLACK)
    display.text(45, row_height * 6, *get_swap_usage(metrics), bgcolor=COLOR_BLACK)

    display.rect(50, row_height * 7, TFT_WIDTH, row_height * 8, COLOR_BLACK, fill=True)
    display.text(0, row_height * 7, "RAID", fgcolor=COLOR_WHITE, bgcolor=COLOR_BLACK)
    display.text(50, row_height * 7, *get_raid_state(metrics), bgcolor=COLOR_BLACK)

    display.rect(45, row_height * 8, TFT_WIDTH, row_height * 9, COLOR_BLACK, fill=True)
    display.text(0, row_height * 8, "Disk", fgcolor=COLOR_WHITE, bgcolor=COLOR_BLACK)
    display.text(45, row_height * 8, *get_disk_usage(metrics), bgcolor=COLOR_BLACK)

    for i, external_storage in enumerate(get_external_storages(metrics)):
        display.rect(0, row_height * (9 + i), TFT_WIDTH, row_height * (10 + i), COLOR_BLACK, fill=True)
        display.text(0, row_height * (9 + i), *external_storage, bgcolor=COLOR_BLACK)


def is_night_mode(metrics) -> bool:
    timestamp = metrics.get("timestamp", 0)
    _, _, _, hours, *_ = utime.localtime(timestamp + 3 * 3600)
    return hours >= 21 or hours <= 6


if __name__ == "__main__":
    display.init()
    TFT_BACKLIGHT_PIN.on()
    ONBOARD_LED.value(0)
    COOLER_PIN.value(0)

    idle_ticks = 0
    while True:
        try:
            time.sleep(READ_TIMEOUT_SEC)

            if idle_ticks >= TICKS_TO_EMERGENCY_BACKOFF:
                COOLER_PIN.value(1)
                ONBOARD_LED.value(1)

            if sys.stdin in select.select([sys.stdin], [], [], READ_TIMEOUT_SEC)[0]:
                raw_data = sys.stdin.buffer.readline().decode("utf-8").strip()
                metrics = json.loads(raw_data)

                idle_ticks = 0
                COOLER_PIN.value(metrics.get("cooler_state", 0))
                ONBOARD_LED.value(0)
                display_metrics(metrics)

                if is_night_mode(metrics):
                    TFT_BACKLIGHT_PIN.off()
                else:
                    TFT_BACKLIGHT_PIN.on()
            else:
                idle_ticks += 1
        except Exception as e:
            idle_ticks += 1
            print(f"Error: {e}")
