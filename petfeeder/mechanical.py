import RPi.GPIO as GPIO  # Import Raspberry Pi GPIO library
import threading  # Allow for threading

from logging import debug, error
from time import sleep


class ReedSwitch(threading.Thread):
    def __init__(self, channel):
        threading.Thread.__init__(self)
        self.triggered = False
        self.channel = channel
        GPIO.setup(self.channel, GPIO.IN)
        self.daemon = True
        self.start()

    def run(self):
        previous = None
        while True:
            current = GPIO.input(self.channel)

            sleep(0.01)

            if current == 0 and previous == 1:
                self.triggered = False
                debug("Reed switch released")
                sleep(0.05)  # Stay ok for a bit
            elif current == 1 and previous == 0:
                self.triggered = True
                debug("Reed switch pressed")
                sleep(0.05)  # Stay triggered for a bit

            previous = current


# Not sure this needs a thread
class Feeder():
    def __init__(self, feed_pin, read_pin, max_cycle_time=5):
        self._feed_pin = feed_pin
        self._read_pin = read_pin
        self._reed_switch = ReedSwitch(self._read_pin)
        self._max_cycle_time = max_cycle_time

    def wait_until_feed_stops(self):
        while not self._reed_switch.triggered:
            sleep(0.01)
        while self._reed_switch.triggered:
            sleep(0.01)

    def feed(self, servings):
        for _ in range(servings):
            self.activate_feeder()

    def activate_feeder(self):
        # TODO: Make sure that if it runs too long we do something about that
        try:
            debug("Starting feed motor")
            GPIO.output(self._feed_pin, GPIO.LOW)

            # This threads so it can time out safely.
            # We don't want to run endlessly on accident.
            wait_thread = threading.Thread(target=self.wait_until_feed_stops)
            wait_thread.start()
            wait_thread.join(timeout=self._max_cycle_time)
            if wait_thread.isAlive():
                raise Exception("Reed switch didn't detect properly")

            GPIO.output(self._feed_pin, GPIO.HIGH)
            debug("Feed motor stopped")

        except Exception as err:
            GPIO.output(self._feed_pin, GPIO.HIGH)
            error("Error encountered. Motor stopped. Error: %s", err)


# Deprecated, but maybe still useful code
# def observe_meal():
#     # current date and time
#     now = datetime.now().timestamp()
#     logging.info("Meal started at: %s", now.isoformat())
#     endtime = now + 20 # 20 second window for food counting, sliding
#     servings = 1
#     lastReading = 0
#     while datetime.now().timestamp() < endtime:
#         currentReading = GPIO.input(LISTEN_PIN)
#         if currentReading != lastReading:
#             lastReading = currentReading
#             if currentReading == 0:
#                 # If it's a fresh read of zero, it's another feeding stop
#                 # trigger, so another serving
#                 servings += 1
#                 endtime = datetime.now().timestamp() + 20
#                 logging.info("serving detected")
#                 GPIO.output(FEED_PIN,GPIO.HIGH)

#         sleep(0.01)
#     print("Servings total: %s" % servings)
#     return servings

def initialize_feeder(listen_pin, feed_pin):
    GPIO.setwarnings(False)    # Ignore warning for now
    GPIO.setmode(GPIO.BOARD)   # Use physical pin numbering

    # Make sure it's off when we start
    GPIO.setup(feed_pin, GPIO.OUT, initial=GPIO.HIGH)

    return Feeder(feed_pin, listen_pin)
