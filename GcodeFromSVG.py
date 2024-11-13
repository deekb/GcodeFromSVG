import glob
import os.path

"""
Set speed:
M5 A0 B0 H200 W200 S<Speed 0-100>
make sure to restart the microcontroller after setting speed

"""

from svg_to_gcode.svg_parser import parse_file

from MakeBlockXYPlotter import MakeBlockXYPlotterInterface, MakeBlockXYPlotterCompiler

commands = MakeBlockXYPlotterInterface()

gcode_compiler = MakeBlockXYPlotterCompiler(MakeBlockXYPlotterInterface,
                                            movement_speed=90,
                                            cutting_speed=90,
                                            pass_depth=5,
                                            laser_power=1,
                                            dwell_time=5,
                                            custom_header=[
                                                commands.laser_off(),
                                                commands.home_axes()
                                            ],
                                            custom_footer=[
                                                commands.laser_off(),
                                                commands.home_axes()
                                            ],
                                            unit="mm")

files = glob.glob("./original/*.svg")

for file in files:
    print(f"Parsing file: {file}")
    curves = parse_file(file)  # Parse the svg file into geometric curves
    print("Done")
    gcode_compiler.clear_curves()  # Clear the existing curves
    print(f"Generating Gcode for file: {file}")
    print(curves)
    gcode_compiler.append_curves(curves)
    gcode_compiler.compile_to_file(os.path.join("./sliced", os.path.basename(file.rsplit('.', 1)[0]) + ".gcode"), passes=1)
    print("Done")



