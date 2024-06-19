import select
import sys
import time

from machine import Pin

READ_TIMEOUT_SEC = 0.05
EMERGENCY_BACKOFF_AFTER_SEC = 50
TICKS_TO_EMERGENCY_BACKOFF = EMERGENCY_BACKOFF_AFTER_SEC // READ_TIMEOUT_SEC


ONBOARD_LED = Pin(25, Pin.OUT)
COOLER_PIN = Pin(0, Pin.OUT)


def main() -> None:
    ONBOARD_LED.value(0)
    COOLER_PIN.value(0)

    idle_ticks = 0
    while True:
        time.sleep(READ_TIMEOUT_SEC)
        if idle_ticks >= TICKS_TO_EMERGENCY_BACKOFF:
            COOLER_PIN.value(1)
            ONBOARD_LED.value(1)

        if sys.stdin in select.select([sys.stdin], [], [], READ_TIMEOUT_SEC)[0]:
            cooler_state = sys.stdin.buffer.readline()[0]
            COOLER_PIN.value(cooler_state)
            idle_ticks = 0
        else:
            idle_ticks += 1


if __name__ == "__main__":
    main()
