import select
import sys
import time

from machine import Pin

SLEEP_TIME=0.05

onboard_led = Pin(25, Pin.OUT)
onboard_led.value(0)

cooler = Pin(0, Pin.OUT)
cooler.value(0)

while True:
    time.sleep(SLEEP_TIME)
    if sys.stdin not in select.select([sys.stdin], [], [], SLEEP_TIME)[0]:
        continue
    cooler_state = sys.stdin.buffer.readline(1)
    onboard_led.value(cooler_state)
    cooler.value(cooler_state)
