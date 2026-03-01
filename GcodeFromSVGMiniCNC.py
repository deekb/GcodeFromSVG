import glob
import os.path

from svg_to_gcode.svg_parser import parse_file
from svg_to_gcode.geometry import Vector

import typing
import warnings

from svg_to_gcode.geometry import Curve
from svg_to_gcode.geometry import LineSegmentChain
from svg_to_gcode import UNITS, TOLERANCES


class Interface:

    """
    Classes which inherit from the abstract Interface class provide a consistent interface_class for the gcode parser.

    The abstract methods below are necessary for the gcode parser to function. Some child classes may choose to also
    implement additional methods like specify_unit and home_axis to provide additional functionality to the parser.

    :param self.position stores the current tool position in 2d
    """

    # Todo convert to abc class
    # Todo add requirement self.position

    def set_movement_speed(self, speed) -> str:
        """
        Changes the speed at which the tool moves.

        :return: Appropriate command.
        """
        raise NotImplementedError("Interface class must implement the set_speed command")

    def linear_move(self, x=None, y=None, z=None) -> str:
        """
        Moves the tool in a straight line.

        :return: Appropriate command.
        """
        raise NotImplementedError("Interface class must implement the linear_move command")

    def laser_off(self) -> str:
        """
        Powers off the laser beam.

        :return: Appropriate command.
        """
        raise NotImplementedError("Interface class must implement the laser_off command")

    def set_laser_power(self, power) -> str:
        """
        If the target machine supports pwm, change the laser power. Regardless of pwm support, powers on the laser beam
        for values of power > 0.

        :param power: Defines the power level of the laser. Valid values range between 0 and 1.
        :return: Appropriate command.
        """
        raise NotImplementedError("Interface class must implement the laser_power command")

    def set_absolute_coordinates(self) -> str:
        """
        Make the coordinate space absolute. ie. move relative to origin not current position.

        return '' if the target of the interface only supports absolute space. If the target only supports
        relative coordinate space, this command should return '' and the child class must transform all future inputs from
        absolute positions to relative positions until set_relative_coordinates is called.

        :return: Appropriate command.
        """
        raise NotImplementedError("Interface class must implement the set_absolute_coordinates command")

    def set_relative_coordinates(self) -> str:
        """
        Make the coordinate space relative. ie. move relative to current position not origin.

        return '' if the target of the interface only supports relative space. If the target only supports
        absolute coordinate space, this command should return '' and the child class must transform all future inputs from
        relative positions to absolute positions until set_absolute_coordinates is called.

        :return: Appropriate command.
        """
        raise NotImplementedError("Interface class must implement the set_relative_coordinates command")

    # Optional commands #
    def dwell(self, milliseconds) -> str:
        """
        Optional method, if implemented dwells for a determined number of milliseconds before moving to the next command.

        :return: Appropriate command.
        """
        pass

    def set_origin_at_position(self) -> str:
        """
        Optional method, if implemented translates coordinate space such that the current position is the new origin.
        If the target of the interface does not implement this command, return '' and the child class must translate all
        input positions to the new coordinate space.

        :return: Appropriate command.
        """
        pass

    def set_unit(self, unit):
        """
        Optional method, if implemented Specifies the unit of measurement.

        :return: Appropriate command. If not implemented return ''.
        """
        pass

    def home_axes(self):
        """
        Optional method, if implemented homes all axes.

        :return: Appropriate command. If not implemented return ''.
        """
        pass


class Compiler:
    """
    The Compiler class handles the process of drawing geometric objects using interface commands and assembling
    the resulting numerical control code.
    """

    def __init__(self, interface_class: typing.Type[Interface], movement_speed, cutting_speed, pass_depth,
                 dwell_time=0, unit=None, custom_header=None, custom_footer=None, custom_between_pass_code=None):
        """

        :param interface_class: Specify which interface to use. The ost common is the gcode interface.
        :param movement_speed: the speed at which to move the tool when moving. (units are determined by the printer)
        :param cutting_speed: the speed at which to move the tool when cutting. (units are determined by the printer)
        :param pass_depth: . AKA, the depth your laser cuts in a pass.
        :param dwell_time: the number of ms the tool should wait before moving to another cut. Useful for pen plotters.
        :param unit: specify a unit to the machine
        :param custom_header: A list of commands to be executed before all generated commands. Default is [laser_off,]
        :param custom_footer: A list of commands to be executed after all generated commands. Default is [laser_off,]
        :param custom_between_pass_code: A list of commands to be executed after each apss except the last pass. Default is []
        """
        self.interface = interface_class()
        self.movement_speed = movement_speed
        self.cutting_speed = cutting_speed
        self.pass_depth = abs(pass_depth)
        self.dwell_time = dwell_time

        if (unit is not None) and (unit not in UNITS):
            raise ValueError(f"Unknown unit {unit}. Please specify one of the following: {UNITS}")

        self.unit = unit

        if custom_header is None:
            custom_header = [self.interface.laser_off()]

        if custom_footer is None:
            custom_footer = [self.interface.laser_off()]

        self.custom_between_pass_code = custom_between_pass_code or []

        self.header = custom_header
        self.footer = custom_footer
        self.body = []

    def compile(self, passes=1):

        """
        Assembles the code in the header, body and footer, saving it to a file.


        :param passes: the number of passes that should be made. Every pass the machine moves_down (z-axis) by
        self.pass_depth and self.body is repeated.
        :return returns the assembled code. self.header + [self.body, -self.pass_depth] * passes + self.footer
        """

        if len(self.body) == 0:
            warnings.warn("Compile with an empty body (no curves). Is this intentional?")

        gcode = []

        gcode.extend(self.header)
        gcode.append(self.interface.set_unit(self.unit))
        for i in range(passes):
            gcode.extend(self.body)

            if i < passes - 1:  # If it isn't the last pass, turn off the laser and move down
                gcode.append(self.interface.laser_off())
                gcode.append(self.interface.linear_move(z=-(self.pass_depth * i)))
                gcode.extend(self.custom_between_pass_code)

        gcode.extend(self.footer)

        gcode = filter(lambda command: command is not None and len(command) > 0, gcode)

        return '\n'.join(gcode)

    def compile_to_file(self, file_name: str, passes=1):
        """
        A wrapper for the self.compile method. Assembles the code in the header, body and footer, saving it to a file.

        :param file_name: the path to save the file.
        :param passes: the number of passes that should be made. Every pass the machine moves_down (z-axis) by
        self.pass_depth and self.body is repeated.
        """

        with open(file_name, 'w') as file:
            file.write(self.compile(passes=passes))

    def append_line_chain(self, line_chain: LineSegmentChain):
        """
        Draws a LineSegmentChain by calling interface.linear_move() for each segment. The resulting code is appended to
        self.body
        """

        if line_chain.chain_size() == 0:
            warnings.warn("Attempted to parse empty LineChain")
            return []

        code = []

        start = line_chain.get(0).start

        # Don't dwell and turn off laser if the new start is at the current position
        if self.interface.position is None or abs(self.interface.position - start) > TOLERANCES["operation"]:
            code = [self.interface.laser_off(), self.interface.set_movement_speed(self.movement_speed),
                    self.interface.linear_move(start.x, start.y), self.interface.set_movement_speed(self.cutting_speed),
                    self.interface.set_laser_power(1)]

            if self.dwell_time > 0:
                code = [self.interface.dwell(self.dwell_time)] + code

        for line in line_chain:
            code.append(self.interface.linear_move(line.end.x, line.end.y))

        self.body.extend(code)

    def append_curves(self, curves: [typing.Type[Curve]]):
        """
        Draws curves by approximating them as line segments and calling self.append_line_chain(). The resulting code is
        appended to self.body
        """

        for curve in curves:
            line_chain = LineSegmentChain()

            approximation = LineSegmentChain.line_segment_approximation(curve)

            line_chain.extend(approximation)

            self.append_line_chain(line_chain)


# --- GRBL Interface ---
class GRBLLaserInterface(Interface):
    def __init__(self, max_power=1000):
        self.position = None
        self._next_speed = None
        self._current_speed = None
        self.max_power = max_power
        self.precision = 3

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
        if z is not None:
            command += f" Z{z:.{self.precision}f}"
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

    def dwell(self, seconds):
        return f"G4 P{seconds / 1000}"

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
        return self.linear_move(0, 0, 0, "G0")

# --- GRBL Compiler ---
class GRBLLaserCompiler(Compiler):
    def __init__(self, interface_class, movement_speed, cutting_speed, pass_depth,
                 laser_power, dwell_time=0, unit=None, custom_header=None, custom_footer=None, custom_between_pass_code=None):
        super().__init__(interface_class, movement_speed, cutting_speed, pass_depth,
                         dwell_time, unit, custom_header, custom_footer, custom_between_pass_code)
        self.laser_power = laser_power

    def append_line_chain(self, line_chain: LineSegmentChain):
        if line_chain.chain_size() == 0:
            return []

        code = []
        start = line_chain.get(0).start

        if self.interface.position is None or abs(self.interface.position - start) > TOLERANCES["operation"]:
            code = [
                self.interface.laser_off(),
                self.interface.set_movement_speed(self.movement_speed),
                self.interface.non_cutting_move(start.x, start.y),
                self.interface.set_movement_speed(self.cutting_speed),
                self.interface.set_laser_power(self.laser_power)
            ]
            if self.dwell_time > 0:
                code.insert(0, self.interface.dwell(self.dwell_time))

        for line in line_chain:
            code.append(self.interface.cutting_move(line.end.x, line.end.y))

        self.body.extend(code)

    def clear_curves(self):
        self.body.clear()

# --- Main Script ---
commands = GRBLLaserInterface()
commands.set_movement_speed(2000)
gcode_compiler = GRBLLaserCompiler(
    GRBLLaserInterface,
    movement_speed=4000,
    cutting_speed=1000,
    pass_depth=(3.175 / 4),
    laser_power=0.6,  # 80% power
    dwell_time=0,
    custom_header=[commands.laser_off(), commands.home_axes(), "G90"],
    custom_footer=[commands.laser_off(), commands.home_axes()],
    unit="mm"
)

files = glob.glob("./original/*.svg")

for file in files:
    print(f"Parsing file: {file}")
    curves = parse_file(file)
    print("Done")
    gcode_compiler.clear_curves()
    print(f"Generating Gcode for file: {file}")
    gcode_compiler.append_curves(curves)
    out_path = os.path.join("./sliced", os.path.basename(file.rsplit('.', 1)[0]) + ".gcode")
    gcode_compiler.compile_to_file(out_path, passes=4)
    print("Done: ", out_path)
