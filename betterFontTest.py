import time

from svgpathtools import Path

from SVGFont2Path.font_parser import SVGFontParser
from SVGFont2Path.path_parser import PathParser
from Send import SerialCommunicator

# === Plotter Setup ===
PLOTTER_HEIGHT_MM = 200
PLOTTER_WIDTH_MM = 200

current_x = 0
current_y = PLOTTER_HEIGHT_MM

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

def move_to(x, y):
    cmd = f"G1 X{str(x):3} Y{str(y):3}"
    print(cmd)
    serial_comm.send(cmd)
    serial_comm.wait_for_ok()

def scale_and_offset_glyph(x, y):
    return x * 0.01 + current_x, y * 0.01 + current_y

def next_character():
    global current_x, current_y
    current_x += 5
    if current_x >= PLOTTER_WIDTH_MM:
        current_x = 0
        current_y -= 5

def main():
    global current_x, current_y
    svg_font_path = 'EMSReadability.svg'  # Path to your SVG font file

    home()
    move_to(current_x, current_y)

    # Step 1: Parse the SVG font to extract character paths
    font_parser = SVGFontParser(svg_font_path)
    font_parser.parse()
    character_paths = font_parser.get_character_paths()

    while True:
        text = input("Enter text to write: ").strip()

        for character in text:
            if character == " ":
                print("Space")
            else:
                for path in PathParser(character_paths[character]).split_paths():
                    move_to(*scale_and_offset_glyph(*path.vertices[0]))
                    pen_down()
                    for x, y in path.vertices[1:]:
                        move_to(*scale_and_offset_glyph(x, y))
                    pen_up()
            next_character()
        move_to(current_x, current_y)


if __name__ == "__main__":
    main()
