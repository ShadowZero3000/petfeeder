#!/usr/bin/env python3

import RPi.GPIO as GPIO  # Import Raspberry Pi GPIO library

from time import sleep
import atexit
import logging

from petfeeder.store import Store
from petfeeder.manager import Manager


# GPIO cleanup
def gpio_cleanup():
    GPIO.cleanup()


def main():
    atexit.register(gpio_cleanup)

    # Initialization and globals
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting")

    Store('config.pkl')
    manager = Manager()

    # Everything actually starts processing here
    manager.run()

    while True:
        sleep(1)


main()
