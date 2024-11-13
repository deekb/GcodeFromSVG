import glob
import os.path
from PIL import Image
from svg_to_gcode.svg_parser import parse_file
from MakeBlockXYPlotter import MakeBlockXYPlotterInterface, MakeBlockXYPlotterCompiler

commands = MakeBlockXYPlotterInterface()


# Dithered image doesn't need scaling of laser power since it's binary (black and white).
def pixel_brightness_to_laser_power(brightness, min_power=0.0, max_power=1.0):
    """Convert dithered pixel brightness to laser power. Black pixels -> max_power, White pixels -> min_power."""
    return max_power if brightness == 0 else min_power  # Black (0) -> max_power, White (255) -> min_power


def downscale_image(image_path, max_size=(200, 200)):
    """Downscale the image to fit within the specified max_size."""
    img = Image.open(image_path)
    img.thumbnail(max_size)  # Resize the image, maintaining aspect ratio
    return img


def dither_image(image):
    """Apply dithering to the image to convert it to a black-and-white binary image."""
    return image.convert("1")  # Convert image to black and white using dithering


def png_to_gcode(image_path, output_file, plotter_interface, laser_min_power=0.0, laser_max_power=1.0, resolution=1.0):
    """Convert PNG image to G-code for a laser plotter using the plotter interface."""
    img = downscale_image(image_path, max_size=(75, 75))  # Downscale the image first
    img = dither_image(img)  # Apply dithering to convert the image to black and white

    # Display the processed image before converting to G-code
    img.show()  # This will open the processed image in your default image viewer

    width, height = img.size
    pixels = img.load()  # Get pixel data

    with open(output_file, 'w') as gcode_file:
        gcode_file.write(plotter_interface.set_unit("mm") + "\n")
        gcode_file.write(plotter_interface.set_absolute_coordinates() + "\n")
        plotter_interface.set_movement_speed(90)  # Set initial speed

        for y in range(height):
            gcode_file.write(f"\n; Row {y + 1}\n")  # Add a comment for each row

            # Zigzag pattern: Even rows (left to right), odd rows (right to left)
            if y % 2 == 0:
                # Even row: left to right
                for x in range(width):
                    brightness = pixels[x, y]
                    laser_power = pixel_brightness_to_laser_power(brightness, min_power=laser_min_power,
                                                                  max_power=laser_max_power)

                    # Cutting move to the next pixel
                    gcode_file.write(plotter_interface.cutting_move(x * resolution, y * resolution) + "\n")

                    # Turn laser on or off based on pixel brightness
                    gcode_file.write(plotter_interface.set_laser_power(laser_power) + "\n")
            else:
                # Odd row: right to left (reverse)
                for x in reversed(range(width)):
                    brightness = pixels[x, y]
                    laser_power = pixel_brightness_to_laser_power(brightness, min_power=laser_min_power,
                                                                  max_power=laser_max_power)

                    # Cutting move to the next pixel
                    gcode_file.write(plotter_interface.cutting_move(x * resolution, y * resolution) + "\n")

                    # Turn laser on or off based on pixel brightness
                    gcode_file.write(plotter_interface.set_laser_power(laser_power) + "\n")

            # Turn off the laser at the end of the row
            gcode_file.write(plotter_interface.laser_off() + "\n")

        # Return to home and turn off the laser
        gcode_file.write(plotter_interface.laser_off() + "\n")
        gcode_file.write(plotter_interface.home_axes() + "\n")


if __name__ == "__main__":
    # Create a plotter interface
    plotter = MakeBlockXYPlotterInterface()

    # Input/output files
    png_file = "Cat.jpg"
    gcode_file = "sliced/output.gcode"

    # Convert the PNG image to G-code with custom laser power scaling
    png_to_gcode(png_file, gcode_file, plotter, laser_min_power=0.0, laser_max_power=1, resolution=0.5)
    print(f"G-code saved to {gcode_file}")
