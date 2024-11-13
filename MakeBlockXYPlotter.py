import math
import typing
import warnings

from svg_to_gcode import TOLERANCES
from svg_to_gcode import formulas
from svg_to_gcode.compiler import Compiler
from svg_to_gcode.compiler.interfaces import Interface
from svg_to_gcode.geometry import LineSegmentChain
from svg_to_gcode.geometry import Vector


class MakeBlockXYPlotterCompiler(Compiler):
    """
    The Compiler class handles the process of drawing geometric objects using interface commands and assembling
    the resulting numerical control code.
    """

    def __init__(self, interface_class: typing.Type[Interface], movement_speed, cutting_speed, pass_depth, laser_power,
                 dwell_time=0, unit=None, custom_header=None, custom_footer=None):
        """

        :param interface_class: Specify which interface to use. The most common is the gcode interface.
        :param movement_speed: the speed at which to move the tool when moving. units are determined by the printer.
        :param cutting_speed: the speed at which to move the tool when cutting. units are determined by the printer.
        :param pass_depth: AKA, the depth your laser cuts in a pass.
        :param laser_power: the power of the laser; 0 is off, and 1 is full power.
        :param dwell_time: the number of ms the tool should wait before moving to another cut. Useful for pen plotters.
        :param unit: specify a unit to the machine
        :param custom_header: A list of commands to be executed before all generated commands. Default is [laser_off]
        :param custom_footer: A list of commands to be executed after all generated commands. Default is [laser_off]
        """
        super().__init__(interface_class, movement_speed, cutting_speed, pass_depth, dwell_time, unit, custom_header,
                         custom_footer)
        self.laser_power = laser_power

    def append_line_chain(self, line_chain: LineSegmentChain):
        """
        Draws a LineSegmentChain by calling interface.linear_move() for each segment. The resulting code is appended to "self.body"
        """

        if line_chain.chain_size() == 0:
            warnings.warn("Attempted to parse empty LineChain")
            return []

        code = []

        start = line_chain.get(0).start

        # Don't dwell and turn off the laser if the new start is at the current position
        if self.interface.position is None or abs(self.interface.position - start) > TOLERANCES["operation"]:

            code = [self.interface.laser_off(), self.interface.set_movement_speed(self.movement_speed),
                    self.interface.non_cutting_move(start.x, start.y),
                    self.interface.set_movement_speed(self.cutting_speed),
                    self.interface.set_laser_power(self.laser_power)]

            if self.dwell_time > 0:
                code = [self.interface.dwell(self.dwell_time)] + code

        for line in line_chain:
            code.append(self.interface.cutting_move(line.end.x, line.end.y))

        self.body.extend(code)

    def clear_curves(self):
        self.body.clear()


class MakeBlockXYPlotterInterface(Interface):

    def __init__(self):
        self.position = None
        self._next_speed = None
        self._current_speed = None

        # Round outputs to the same number of significant figures as the operational tolerance.
        self.precision = abs(round(math.log(TOLERANCES["operation"], 10)))

    def set_movement_speed(self, speed):
        self._next_speed = speed
        # return "M5 A%d B%d H%d W%d S%d\n" % (0, 0, 200, 200, speed)
        return ""

    def cutting_move(self, x, y):
        return self.linear_move(x, y, command="G1")

    def non_cutting_move(self, x, y):
        return self.linear_move(x, y, command="G0")

    def linear_move(self, x=None, y=None, z=None, command="G1"):
        # Don't do anything if the linear move command was called without passing a value.
        if x is None and y is None and z is None:
            warnings.warn("linear_move command invoked without arguments.")
            return ""


        # Move if not 0 and not None
        command += f" X{x:.{self.precision}f}" if x is not None else ""
        command += f" Y{y:.{self.precision}f}" if y is not None else ""

        if self.position is not None or (x is not None and y is not None):
            if x is None:
                x = self.position.x

            if y is None:
                y = self.position.y

            self.position = Vector(x, y)

        return command

    def laser_off(self):
        return self.set_laser_power(0)

    def set_laser_power(self, power):
        if power < 0 or power > 1:
            raise ValueError(f"{power} is out of bounds. Laser power must be given between 0 and 1. "
                             f"The interface will scale it correctly.")

        return f"M4 {formulas.linear_map(0, 100, power)}"

    def set_absolute_coordinates(self):
        return "G90"

    def set_relative_coordinates(self):
        return "G91"

    def dwell(self, milliseconds):
        return f"G4 P{milliseconds}"

    def set_origin_at_position(self):
        self.position = Vector(0, 0)
        return "G92 X0 Y0 Z0"

    def set_unit(self, unit):
        unit = unit.lower()
        if unit == "mm":
            return "G21"

        if unit == "in":
            return "G20"

        return ""

    def home_axes(self):
        return "G28"
