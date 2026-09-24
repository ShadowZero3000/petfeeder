import logging
import sys
import threading
import time
import unittest
from unittest import mock

# The Pi-only libraries can't be installed off the Pi, so stub them out
sys.modules.setdefault("RPi", mock.MagicMock())
sys.modules.setdefault("RPi.GPIO", sys.modules["RPi"].GPIO)

from telebot import apihelper  # noqa: E402

from petfeeder import mechanical  # noqa: E402
from petfeeder.mechanical import Feeder  # noqa: E402
from petfeeder.telegram import Telegram  # noqa: E402


class TelegramThreadLeakTest(unittest.TestCase):
    def setUp(self):
        # Nothing listens on port 9, so every poll fails with a network
        # error, like the Pi's WiFi dropping out
        self.api_url = apihelper.API_URL
        apihelper.API_URL = "http://127.0.0.1:9/bot{0}/{1}"
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        apihelper.API_URL = self.api_url
        logging.disable(logging.NOTSET)

    def test_failed_polls_do_not_leak_threads(self):
        before = threading.active_count()
        telegram = Telegram("123:fake", 0)
        # The run loop retries every second, so this is several failed polls
        time.sleep(4)
        telegram.stop()

        # Only the Telegram thread itself should have been added
        self.assertLessEqual(threading.active_count(), before + 1)
        names = [t.name for t in threading.enumerate()]
        self.assertNotIn("PollingThread", names)


class FakeReedSwitch():
    triggered = False


class FeederThreadLeakTest(unittest.TestCase):
    def setUp(self):
        # Build a Feeder without starting the real reed switch thread
        self.feeder = Feeder.__new__(Feeder)
        self.feeder._feed_pin = 11
        self.feeder._reed_switch = FakeReedSwitch()
        self.feeder._max_cycle_time = 0.2
        self.feeder.manager = mock.MagicMock()
        mechanical.GPIO.reset_mock()
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_timeout_warns_and_stops_motor_without_leaking(self):
        before = threading.active_count()
        # The reed switch never triggers, like a jammed feeder
        self.feeder.feed(3)

        self.assertEqual(threading.active_count(), before)
        self.assertEqual(
            self.feeder.manager.action.call_args_list,
            [mock.call("warning", message="Feed error: Reed switch didn't "
                                          "detect properly")] * 3)
        # Motor is left off
        mechanical.GPIO.output.assert_called_with(11, mechanical.GPIO.LOW)

    def test_normal_feed(self):
        switch = self.feeder._reed_switch

        def turn_motor():
            time.sleep(0.02)
            switch.triggered = True
            time.sleep(0.02)
            switch.triggered = False

        motor = threading.Thread(target=turn_motor)
        motor.start()
        self.feeder.feed(1)
        motor.join()

        self.feeder.manager.action.assert_not_called()
        mechanical.GPIO.output.assert_called_with(11, mechanical.GPIO.LOW)


if __name__ == "__main__":
    unittest.main()
