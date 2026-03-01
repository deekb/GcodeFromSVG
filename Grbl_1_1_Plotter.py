import math
import typing
import warnings

from svg_to_gcode import TOLERANCES
from svg_to_gcode import formulas
from svg_to_gcode.compiler import Compiler
from svg_to_gcode.compiler.interfaces import Interface
from svg_to_gcode.geometry import LineSegmentChain
from svg_to_gcode.geometry import Vector


class GRBLLaserInterface(Interface):

    def __init__(self, max_power=1000):
        self.position = None
        self._next_speed = None
        self._current_speed = None
        self.max_power = max_power
        self.precision = 3  # Good for GRBL

    def set_movement_speed(self, speed):
        self._next_speed = speed
        return ""

    def cutting_move(self, x, y):
        return self.linear_move(x, y, command="G1")

    def non_cutting_move(self, x, y):
        return self.linear_move(x, y, command="G0")

    def linear_move(self, x=None, y=None, z=None, command="G1"):
        if self._next_speed is None:
            raise ValueError("Undefined movement speed. Call set_movement_speed before moving.")

        if x is None and y is None and z is None:
            return ""

        if self._current_speed != self._next_speed:
            self._current_speed = self._next_speed
            command += f" F{self._current_speed}"

        if x is not None:
            command += f" X{x:.{self.precision}f}"
        if y is not None:
            command += f" Y{y:.{self.precision}f}"

        # Track current position
        if x is not None and y is not None:
            self.position = Vector(x, y)

        return command

    def laser_off(self):
        return "M5"

    def set_laser_power(self, power):
        if power < 0 or power > 1:
            raise ValueError("Power must be between 0 and 1")

        grbl_power = int(power * self.max_power)
        return f"M3 S{grbl_power}"

    def set_absolute_coordinates(self):
        return "G90"

    def set_relative_coordinates(self):
        return "G91"

    def dwell(self, milliseconds):
        return f"G4 P{milliseconds}"

    def set_origin_at_position(self):
        return "G92 X0 Y0"

    def set_unit(self, unit):
        unit = unit.lower()
        if unit == "mm":
            return "G21"
        if unit == "in":
            return "G20"
        return ""

    def home_axes(self):
        return "$H"


class GRBLLaserCompiler(Compiler):
    def __init__(self, interface_class, movement_speed, cutting_speed, pass_depth, laser_power, dwell_time=0, unit=None,
                 custom_header=None, custom_footer=None):
        super().__init__(interface_class, movement_speed, cutting_speed, pass_depth, dwell_time, unit, custom_header,
                         custom_footer)
        self.laser_power = laser_power

    def append_line_chain(self, line_chain: LineSegmentChain):
        if line_chain.chain_size() == 0:
            return []

        code = []
        start = line_chain.get(0).start

        # Move if not already there
        if self.interface.position is None or abs(self.interface.position - start) > TOLERANCES["operation"]:
            code = [self.interface.laser_off(), self.interface.set_movement_speed(self.movement_speed),
                self.interface.non_cutting_move(start.x, start.y),
                self.interface.set_movement_speed(self.cutting_speed), self.interface.set_laser_power(self.laser_power)]

            if self.dwell_time > 0:
                code.insert(0, self.interface.dwell(self.dwell_time))

        # Cut lines
        for line in line_chain:
            code.append(self.interface.cutting_move(line.end.x, line.end.y))

        self.body.extend(code)

    def clear_curves(self):
        self.body.clear()
