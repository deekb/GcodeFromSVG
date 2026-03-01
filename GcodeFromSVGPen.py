import glob
import os.path

from svg_to_gcode.svg_parser import parse_file

from MakeBlockXYPlotter import MakeBlockXYPenPlotterCompiler, MakeBlockXYPenPlotterInterface

commands = MakeBlockXYPenPlotterInterface()

gcode_compiler = MakeBlockXYPenPlotterCompiler(MakeBlockXYPenPlotterInterface,
                                                 movement_speed=5000,
                                                 cutting_speed=4000,
                                                 pass_depth=5,
                                                 dwell_time=0,
                                                 custom_header=[
                                                     commands.pen_up(),
                                                     commands.home_axes()
                                                 ],
                                                 custom_footer=[
                                                     commands.pen_up(),
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
    gcode_compiler.append_curves(curves)
    gcode_compiler.compile_to_file(os.path.join("./sliced", os.path.basename(file.rsplit('.', 1)[0]) + ".gcode"),
                                   passes=1)
    print("Done")
