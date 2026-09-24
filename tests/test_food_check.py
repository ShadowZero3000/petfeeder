import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image

# The Pi-only libraries can't be installed off the Pi, so stub them out
sys.modules.setdefault("RPi", mock.MagicMock())
sys.modules.setdefault("RPi.GPIO", sys.modules["RPi"].GPIO)
sys.modules.setdefault("picamera", mock.MagicMock())

from petfeeder import integrations  # noqa: E402
from petfeeder.integrations import FoodCheckIntegration  # noqa: E402
from petfeeder.manager import Manager  # noqa: E402

Sanitize = FoodCheckIntegration.sanitize


class SanitizeTest(unittest.TestCase):
    def test_valid_values(self):
        self.assertEqual(Sanitize("enabled", True), True)
        self.assertEqual(Sanitize("log_only", False), False)
        self.assertEqual(Sanitize("threshold", "0.05"), 0.05)
        self.assertEqual(Sanitize("pixel_delta", "30"), 30)
        self.assertEqual(Sanitize("max_captures", "50"), 50)

    def test_invalid_values(self):
        for key, value in [("threshold", "abc"), ("threshold", "1.5"),
                           ("threshold", "-0.1"), ("pixel_delta", "0"),
                           ("pixel_delta", "256"), ("pixel_delta", "2.5"),
                           ("max_captures", "0"), ("max_captures", "-3"),
                           ("bogus", "1")]:
            with self.assertRaises(Exception, msg="%s=%s" % (key, value)):
                Sanitize(key, value)

    def test_registered(self):
        self.assertIs(integrations.available_integrations()["food_check"],
                      FoodCheckIntegration)

    def test_defaults(self):
        details = FoodCheckIntegration(None).details()
        self.assertEqual(details, {
            'enabled': False, 'log_only': True, 'threshold': 0.02,
            'pixel_delta': 25, 'max_captures': 200
        })


class FakeCamera():
    enabled = True

    def __init__(self, fail_on=None):
        self.fail_on = fail_on
        self.taken = []

    def take_picture(self, filename='public/media/still.jpg'):
        label = "before" if "before" in filename else "after"
        self.taken.append(label)
        if label == self.fail_on:
            return None
        img = Image.new("L", (640, 480), 100)
        if label == "after":
            # Part of the frame changes, as if food landed in the bowl
            img.paste(200, (240, 180, 400, 300))
        img.save(filename, format="JPEG")
        return filename


class FeedFlowTest(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)
        os.makedirs("public/media")

        # Build a Manager without touching GPIO, the store or the web server
        self.manager = Manager.__new__(Manager)
        self.manager.feeder = mock.MagicMock()
        self.telegram = mock.MagicMock()
        self.camera = FakeCamera()
        self.food_check = FoodCheckIntegration(
            self.manager, enabled=True, log_only=False)
        self.manager.integrations = {
            "telegram": self.telegram,
            "camera": self.camera,
            "food_check": self.food_check,
        }

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmpdir)

    def feed(self, **kwargs):
        self.manager.action("feed", name="Breakfast", servings=2, **kwargs)

    def warnings(self):
        return [c for c in self.telegram.message.call_args_list
                if "WARNING" in c[0][0]]

    def test_food_detected(self):
        self.feed()
        self.manager.feeder.feed.assert_called_once_with(2)
        self.assertEqual(self.camera.taken, ["before", "after"])
        self.assertEqual(self.warnings(), [])
        files = sorted(os.listdir("captures"))
        self.assertEqual(len(files), 2)
        self.assertRegex(files[0], r"^\d{4}-\d\d-\d\dT\d\d-\d\d-\d\d"
                                   r"_score0\.\d{3}_after\.jpg$")
        self.assertEqual(files[1], files[0].replace("after", "before"))

    def test_no_food_warns_without_notify(self):
        # Like crash alerts, the warning goes out even on meals that
        # don't normally notify, just without a photo
        self.food_check.threshold = 1.1  # Nothing can pass this
        self.feed(notify=False)
        self.telegram.send_photo.assert_not_called()
        self.assertEqual(len(self.warnings()), 1)
        self.assertRegex(self.warnings()[0][0][0],
                         r"hopper may be empty or jammed "
                         r"\(change score \d+\.\d%\)$")

    def test_log_only_never_warns(self):
        self.food_check.threshold = 1.1
        self.food_check.log_only = True
        self.feed()
        self.assertEqual(self.warnings(), [])

    def test_notify_sends_after_photo_with_score(self):
        self.feed(notify=True)
        self.assertEqual(self.camera.taken, ["before", "after"])
        args, kwargs = self.telegram.send_photo.call_args
        self.assertTrue(args[0].endswith("_after.jpg"))
        self.assertRegex(kwargs["caption"], r"^Change score: \d+\.\d%$")

    def test_disabled_keeps_old_behavior(self):
        self.food_check.enabled = False
        self.feed(notify=True)
        self.manager.feeder.feed.assert_called_once_with(2)
        # Only the usual notify photo, with no caption
        self.assertEqual(self.camera.taken, ["after"])
        self.telegram.send_photo.assert_called_once_with(
            "public/media/still.jpg")

    def test_camera_disabled_skips_check(self):
        self.camera.enabled = False
        self.feed()
        self.manager.feeder.feed.assert_called_once_with(2)
        self.assertEqual(self.camera.taken, [])

    def test_before_photo_failure_still_feeds(self):
        self.camera.fail_on = "before"
        self.feed()
        self.manager.feeder.feed.assert_called_once_with(2)
        self.assertEqual(self.warnings(), [])

    def test_camera_exception_still_feeds(self):
        self.camera.take_picture = mock.MagicMock(
            side_effect=RuntimeError("camera exploded"))
        self.feed()
        self.manager.feeder.feed.assert_called_once_with(2)

    def test_scoring_exception_still_feeds_and_notifies(self):
        with mock.patch("petfeeder.vision.change_score",
                        side_effect=IOError("bad jpeg")):
            self.feed(notify=True)
        self.manager.feeder.feed.assert_called_once_with(2)
        self.assertEqual(self.warnings(), [])
        # Photo still sent, just without a score
        args, kwargs = self.telegram.send_photo.call_args
        self.assertIsNone(kwargs["caption"])

    def test_warning_failure_does_not_raise(self):
        self.food_check.threshold = 1.1
        self.telegram.message.side_effect = RuntimeError("telegram down")
        self.feed()
        self.manager.feeder.feed.assert_called_once_with(2)

    def test_prunes_to_max_captures(self):
        self.food_check.max_captures = 3
        os.makedirs("captures")
        for hour in range(5):
            stamp = "2026-01-01T0%d-00-00" % hour
            for label in ["score0.100_before", "score0.100_after"]:
                open("captures/%s_%s.jpg" % (stamp, label), "w").close()
        # Unscored leftover from a failed check
        open("captures/2026-01-01T05-00-00_before.jpg", "w").close()

        self.feed()

        stamps = sorted(set(f.split("_")[0]
                            for f in os.listdir("captures")))
        self.assertEqual(len(stamps), 3)
        self.assertEqual(stamps[:2],
                         ["2026-01-01T04-00-00", "2026-01-01T05-00-00"])


if __name__ == "__main__":
    unittest.main()
