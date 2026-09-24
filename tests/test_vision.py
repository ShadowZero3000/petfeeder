import glob
import os
import shutil
import tempfile
import unittest

from PIL import Image, ImageDraw, ImageFilter
import numpy as np

from petfeeder.vision import change_score

# Same as the FoodCheck integration default
DEFAULT_THRESHOLD = 0.02
SIZE = (640, 480)  # Camera capture resolution
FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def bowl_scene(seed=0):
    """A lit floor with a bowl on it, as a float array"""
    rng = np.random.RandomState(seed)
    # Floor: gentle gradient plus some texture
    x = np.linspace(0, 1, SIZE[0])
    y = np.linspace(0, 1, SIZE[1])[:, None]
    floor = 110 + 30 * x + 20 * y
    texture = Image.fromarray(
        rng.uniform(0, 255, (SIZE[1], SIZE[0])).astype(np.uint8)
    ).filter(ImageFilter.GaussianBlur(3))
    floor = floor + (np.asarray(texture, dtype=np.float32) - 128) * 0.5

    img = Image.fromarray(np.clip(floor, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(img)
    # Bowl rim and inside
    draw.ellipse((170, 110, 470, 390), fill=190)
    draw.ellipse((200, 140, 440, 360), fill=160)
    return np.asarray(img, dtype=np.float32)


def add_kibble(scene, count=60, seed=1):
    """
    Scatter a cluster of dark blobs in the bowl. Sized like the kibble in
    tests/fixtures: the camera is close, so each piece is ~25-35px across
    """
    rng = np.random.RandomState(seed)
    img = Image.fromarray(scene.astype(np.uint8))
    draw = ImageDraw.Draw(img)
    for _ in range(count):
        cx = rng.normal(320, 55)
        cy = rng.normal(250, 40)
        r = rng.uniform(12, 17)
        shade = int(rng.uniform(50, 80))
        draw.ellipse((cx - r, cy - r * 0.8, cx + r, cy + r * 0.8), fill=shade)
    return np.asarray(img, dtype=np.float32)


def shift_and_noise(scene, dx=1, dy=0, sigma=3.0, seed=2):
    rng = np.random.RandomState(seed)
    shifted = np.roll(np.roll(scene, dy, axis=0), dx, axis=1)
    return shifted + rng.normal(0, sigma, scene.shape)


class ChangeScoreTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.scene = bowl_scene()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def save(self, name, arr):
        path = os.path.join(self.tmpdir, name)
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        img.save(path, format="JPEG", quality=85)
        return path

    def score(self, before, after):
        return change_score(self.save("before.jpg", before),
                            self.save("after.jpg", after))

    def test_identical_frames(self):
        score = self.score(self.scene, self.scene)
        print("\n  identical: %.4f" % score)
        self.assertLess(score, 0.001)

    def test_brightness_shift(self):
        score = self.score(self.scene, self.scene + 15)
        print("\n  brightness +15: %.4f" % score)
        self.assertLess(score, 0.001)

    def test_one_pixel_shift_with_noise(self):
        score = self.score(self.scene, shift_and_noise(self.scene))
        print("\n  1px shift + noise: %.4f" % score)
        self.assertLess(score, DEFAULT_THRESHOLD)

    def test_kibble_added(self):
        score = self.score(self.scene, add_kibble(self.scene))
        print("\n  kibble added: %.4f" % score)
        self.assertGreater(score, DEFAULT_THRESHOLD * 3)

    def test_kibble_added_with_shift_and_noise(self):
        after = shift_and_noise(add_kibble(self.scene))
        score = self.score(self.scene, after)
        print("\n  kibble + 1px shift + noise: %.4f" % score)
        self.assertGreater(score, DEFAULT_THRESHOLD * 3)


def fixture(name):
    pattern = os.path.join(FIXTURES, "*", "photo_2026-09-23_%s*" % name)
    return glob.glob(pattern)[0]


class RealPhotoTest(unittest.TestCase):
    """
    Photos from the feeder's camera. They come from different days, so they
    aren't real before/after pairs, but pairs with the same framing are
    close to what a feeding looks like
    """

    # Grouped by camera framing: (empty bowl, [bowls with food])
    FRAMINGS = [
        ("20-02-45", ["19-56-34", "19-56-48", "19-57-02"]),
        ("20-00-25", ["19-57-16", "19-57-47", "19-57-58"]),
    ]

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_food_dispensed(self):
        for empty, fulls in self.FRAMINGS:
            for full in fulls:
                score = change_score(fixture(empty), fixture(full))
                print("\n  %s -> %s: %.4f" % (empty, full, score))
                self.assertGreater(score, DEFAULT_THRESHOLD * 3)

    def test_no_change(self):
        # Each photo against a copy that is shifted, re-exposed and noisy
        rng = np.random.RandomState(0)
        for path in sorted(glob.glob(os.path.join(FIXTURES, "*", "*.jpg"))):
            arr = np.asarray(Image.open(path).convert("RGB"),
                             dtype=np.float32)
            arr = np.roll(np.roll(arr, 2, axis=0), 3, axis=1) * 0.85
            arr = arr + rng.normal(0, 3, arr.shape)
            after = os.path.join(self.tmpdir, "after.jpg")
            Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(
                after, format="JPEG", quality=85)

            score = change_score(path, after)
            print("\n  %s unchanged: %.4f" % (os.path.basename(path), score))
            self.assertLess(score, DEFAULT_THRESHOLD)


if __name__ == "__main__":
    unittest.main()
