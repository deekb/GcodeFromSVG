import os
import glob
from PIL import Image
import numpy as np
import math


# ---------------------------
# GRBL Laser Gcode Generator (Sinusoidal Path Engraving)
# ---------------------------

class GRBLLaserRaster:
    def __init__(
            self,
            max_power=1000,
            travel_speed=2000,
            burn_speed=1200,
            invert=False,
            dither=False,
            max_amplitude=0.5,      # mm of wave height
            frequency=15,           # wave cycles per mm
            steps_per_pixel=3,      # micro-segments for smooth waves
            constant_power=120      # S value for the whole burn
    ):
        self.max_power = max_power
        self.travel_speed = travel_speed
        self.burn_speed = burn_speed
        self.invert = invert
        self.dither = dither
        self.max_amplitude = max_amplitude
        self.frequency = frequency
        self.steps_per_pixel = steps_per_pixel
        self.constant_power = constant_power

    # Floyd–Steinberg dithering (optional)
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

    # Convert pixel brightness → amplitude
    def brightness_to_amplitude(self, px):
        if self.invert:
            px = 255 - px
        # dark = max amplitude / bright = small amplitude
        return self.max_amplitude * (1 - px / 255)

    # Sinusoidal G-code generator
    def generate(self, img_path, output_path, mm_per_pixel=0.1):
        img = Image.open(img_path).convert("L")

        if self.dither:
            img = self.apply_dithering(img)

        width, height = img.size
        print(f"Loaded {img_path}: {width}×{height}")

        g = []
        g.append("G90")
        g.append("G21")
        g.append("M5")

        for y in range(height):
            # serpentine scanning
            if y % 2 == 0:
                x_pixels = range(width)
            else:
                x_pixels = range(width - 1, -1, -1)

            y_base = y * mm_per_pixel

            start_x_mm = x_pixels.start * mm_per_pixel
            g.append(f"G0 X{start_x_mm:.3f} Y{y_base:.3f} F{self.travel_speed}")
            g.append(f"M3 S{self.constant_power}")
            g.append(f"G1 F{self.burn_speed}")

            for x in x_pixels:
                px = img.getpixel((x, y))
                amplitude = self.brightness_to_amplitude(px)

                # Break each pixel into micro-moves with sine displacement
                for s in range(self.steps_per_pixel):
                    t = s / self.steps_per_pixel
                    x_mm = (x + t) * mm_per_pixel

                    # Sine wave vertical displacement
                    y_mm = y_base + amplitude * math.sin(
                        2 * math.pi * self.frequency * x_mm
                    )

                    g.append(f"G1 X{x_mm:.4f} Y{y_mm:.4f}")

            g.append("M5")  # end of row

        g.append("G0 X0 Y0")
        g.append("M5")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write("\n".join(g))

        print(f"Saved: {output_path}")


# ---------------------------
# Batch Convert Bitmaps
# ---------------------------

raster = GRBLLaserRaster(
    constant_power=200,     # GRBL S-value constant
    travel_speed=2000,
    burn_speed=2000,
    invert=True,
    dither=False,          # dithering optional
    max_amplitude=0.5,     # bigger waves = darker burn
    frequency=15,          # wave frequency
    steps_per_pixel=3
)

files = glob.glob("./original/*.png") + \
        glob.glob("./original/*.jpg") + \
        glob.glob("./original/*.jpeg") + \
        glob.glob("./original/*.bmp")

for file in files:
    name = os.path.basename(file).rsplit(".", 1)[0]
    out = f"./sliced/{name}.gcode"
    raster.generate(file, out, mm_per_pixel=0.3)
