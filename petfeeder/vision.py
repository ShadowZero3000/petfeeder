from PIL import Image, ImageFilter
import numpy as np

# Kept free of RPi.GPIO and picamera so it can be tested off the Pi


def _prepare(path, size, blur_radius):
    img = Image.open(path)
    # Let the JPEG decoder downscale for us, much cheaper on a Pi Zero
    img.draft("L", (size[0] * 2, size[1] * 2))
    img = img.convert("L").resize(size, Image.BILINEAR)
    img = img.filter(ImageFilter.GaussianBlur(blur_radius))
    arr = np.asarray(img, dtype=np.float32)
    # Subtracting the mean cancels out small exposure shifts
    return arr - arr.mean()


def change_score(before_path, after_path, size=(160, 120), pixel_delta=25,
                 blur_radius=2):
    """
    Fraction (0.0 - 1.0) of pixels that changed noticeably between two frames
    """
    before = _prepare(before_path, size, blur_radius)
    after = _prepare(after_path, size, blur_radius)
    diff = np.abs(before - after)
    return float((diff > pixel_delta).mean())
