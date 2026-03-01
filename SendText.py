import xml.etree.ElementTree as ET
from svgpathtools import parse_path
import numpy as np
import time
from Send import SerialCommunicator

# === Plotter Setup ===
PLOTTER_HEIGHT_MM = 200
PLOTTER_WIDTH_MM = 200

serial_comm = SerialCommunicator("/dev/ttyUSB0")
time.sleep(3)  # Allow connection to settle

def home():
    serial_comm.send("G28")
    serial_comm.wait_for_ok()

def pen_up():
    serial_comm.send("M5")
    serial_comm.wait_for_ok()

def pen_down():
    serial_comm.send("M3")
    serial_comm.wait_for_ok()

def move_to(x, y, rapid=True):
    cmd = f"{'G0' if rapid else 'G1'} X{round(x,3)} Y{round(y,3)}"
    serial_comm.send(cmd)
    serial_comm.wait_for_ok()

# === SVG Font Handling ===
svg_font_path = 'ReliefSingleLineSVG-Regular.svg'
tree = ET.parse(svg_font_path)
root = tree.getroot()

ns = {'svg': 'http://www.w3.org/2000/svg'}

glyphs = {}
for glyph in root.findall('.//svg:glyph', ns):
    unicode_char = glyph.attrib.get('unicode')
    path_data = glyph.attrib.get('d')
    if unicode_char and path_data:
        try:
            glyphs[unicode_char] = parse_path(path_data)
        except Exception as e:
            print(f"Error parsing glyph for {unicode_char}: {e}")

def scale_and_align_glyph(glyph_path, desired_height=5.0):
    xmin, xmax, ymin, ymax = glyph_path.bbox()
    current_height = ymax - ymin
    scale_factor = desired_height / current_height if current_height != 0 else 1
    scaled = glyph_path.scaled(scale_factor)
    _, _, new_ymin, _ = scaled.bbox()
    aligned = scaled.translated(complex(0, -new_ymin))
    return aligned

def text_to_paths(text, glyphs, additional_spacing=0.5):
    x_offset = 0
    paths = []
    for char in text:
        glyph_path = glyphs.get(char)
        if glyph_path:
            scaled_glyph = scale_and_align_glyph(glyph_path, desired_height=5.0)
            translated = scaled_glyph.translated(complex(x_offset, 0))
            paths.append(translated)
            xmin, xmax, _, _ = scaled_glyph.bbox()
            glyph_width = xmax - xmin
            x_offset += glyph_width + additional_spacing
        else:
            x_offset += additional_spacing
    return paths

def sample_path(path, num_points=50):
    return [path.point(t) for t in np.linspace(0, 1, num_points)]


def plot_text(text):
    pen_up()

    start_x = 10
    start_y = PLOTTER_HEIGHT_MM - 10

    paths = text_to_paths(text, glyphs)
    current_pos = None

    for path in paths:
        for subpath in path:
            points = sample_path(subpath)
            if not points:
                continue
            # Offset all points to desired start position
            offset_points = [complex(pt.real + start_x, pt.imag + start_y) for pt in points]
            start = offset_points[0]

            # Only pen up if move required
            if current_pos is None or abs(current_pos - start) > 0.01:
                pen_up()
                move_to(start.real, start.imag)
                pen_down()

            for pt in offset_points[1:]:
                move_to(pt.real, pt.imag, rapid=False)
            current_pos = offset_points[-1]

    pen_up()
    print("✅ Plotting complete.")


# === Main interactive loop ===
if __name__ == "__main__":
    home()
    while True:
        user_input = input("Enter text to plot (or type 'exit'): ").strip()
        if user_input.lower() == 'exit':
            break
        plot_text(user_input)
