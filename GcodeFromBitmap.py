import os
import glob
from PIL import Image
import numpy as np


# ---------------------------
# GRBL Laser Gcode Generator with Dithering
# ---------------------------

class GRBLLaserRaster:
    def __init__(self, max_power=1000, travel_speed=2000, burn_speed=1200, invert=False, dither=True):
        self.max_power = max_power
        self.travel_speed = travel_speed
        self.burn_speed = burn_speed
        self.invert = invert
        self.dither = dither

    def pixel_to_power(self, px):
        # px is 0..255 (0=black, 255=white)
        if self.invert:
            px = 255 - px
        return int((1 - (px / 255)) * self.max_power)

    def apply_dithering(self, img):
        arr = np.array(img, dtype=np.float32)
        h, w = arr.shape

        for y in range(h):
            for x in range(w):
                old_pixel = arr[y, x]
                new_pixel = 0 if old_pixel < 128 else 255
                arr[y, x] = new_pixel
                quant_error = old_pixel - new_pixel
                if x + 1 < w:
                    arr[y, x + 1] += quant_error * 7 / 16
                if y + 1 < h:
                    if x > 0:
                        arr[y + 1, x - 1] += quant_error * 3 / 16
                    arr[y + 1, x] += quant_error * 5 / 16
                    if x + 1 < w:
                        arr[y + 1, x + 1] += quant_error * 1 / 16
        arr = np.clip(arr, 0, 255)
        return Image.fromarray(arr.astype(np.uint8))

    def generate(self, img_path, output_path, mm_per_pixel=0.1):
        img = Image.open(img_path).convert("L")  # grayscale

        if self.dither:
            img = self.apply_dithering(img)

        width, height = img.size
        print(f"Loaded {img_path}: {width}×{height}")

        gcode = []
        gcode.append("G90")  # absolute coordinates
        gcode.append("G21")  # mm units
        gcode.append("M5")   # laser off

        for y in range(height):
            row = [img.getpixel((x, y)) for x in range(width)]

            # serpentine scanning
            if y % 2 == 0:
                x_range = range(width)
            else:
                x_range = range(width - 1, -1, -1)

            x_mm_start = x_range.start * mm_per_pixel
            y_mm = y * mm_per_pixel

            gcode.append(f"G0 X{x_mm_start:.3f} Y{y_mm:.3f} F{self.travel_speed}")
            gcode.append("M3 S0")
            gcode.append(f"G1 F{self.burn_speed}")

            for x in x_range:
                px = row[x]
                power = self.pixel_to_power(px)
                x_mm = x * mm_per_pixel
                gcode.append(f"G1 X{x_mm:.3f} S{power}")

            gcode.append("M5")  # laser off at end of line

        gcode.append("G0 X0 Y0")
        gcode.append("M5")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write("\n".join(gcode))

        print(f"Saved: {output_path}")


# ---------------------------
# Batch Convert Bitmaps
# ---------------------------

raster = GRBLLaserRaster(
    max_power=60,       # GRBL S-value max
    travel_speed=2000,   # G0 speed
    burn_speed=2000,     # G1 speed for engraving
    invert=True,         # for wood engraving
    dither=True          # enable dithering
)

files = glob.glob("./original/*.png") + \
        glob.glob("./original/*.jpg") + \
        glob.glob("./original/*.jpeg") + \
        glob.glob("./original/*.bmp")

for file in files:
    name = os.path.basename(file).rsplit(".", 1)[0]
    out = f"./sliced/{name}.gcode"
    raster.generate(file, out, mm_per_pixel=0.1)
