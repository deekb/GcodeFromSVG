import glob
import os
import os.path
import typing
import warnings

from svg_to_gcode.svg_parser import parse_file
from svg_to_gcode.geometry import Vector, Curve, LineSegmentChain
from svg_to_gcode import UNITS, TOLERANCES


# ============================================================
# Base Interface
# ============================================================

class Interface:

    def set_movement_speed(self, speed) -> str:
        raise NotImplementedError

    def linear_move(self, x=None, y=None, z=None) -> str:
        raise NotImplementedError

    def laser_off(self) -> str:
        raise NotImplementedError

    def set_laser_power(self, power) -> str:
        raise NotImplementedError

    def set_absolute_coordinates(self) -> str:
        raise NotImplementedError

    def set_relative_coordinates(self) -> str:
        raise NotImplementedError

    # Optional

    def dwell(self, milliseconds) -> str:
        pass

    def set_origin_at_position(self) -> str:
        pass

    def set_unit(self, unit):
        pass

    def home_axes(self):
        pass


# ============================================================
# Base Compiler
# ============================================================

class Compiler:

    def __init__(
        self,
        interface_class: typing.Type[Interface],
        movement_speed,
        cutting_speed,
        pass_depth,
        dwell_time=0,
        unit=None,
        custom_header=None,
        custom_footer=None,
        custom_between_pass_code=None,
    ):
        self.interface = interface_class()
        self.movement_speed = movement_speed
        self.cutting_speed = cutting_speed
        self.pass_depth = abs(pass_depth)
        self.dwell_time = dwell_time

        if (unit is not None) and (unit not in UNITS):
            raise ValueError(f"Unknown unit {unit}. Valid units: {UNITS}")

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

        if len(self.body) == 0:
            warnings.warn("Compile called with empty body")

        gcode = []
        gcode.extend(self.header)
        gcode.append(self.interface.set_unit(self.unit))

        for i in range(passes):
            gcode.extend(self.body)

            if i < passes - 1:
                gcode.append(self.interface.laser_off())
                gcode.append(self.interface.linear_move(z=-(self.pass_depth * (i + 1))))
                gcode.extend(self.custom_between_pass_code)

        gcode.extend(self.footer)

        gcode = filter(lambda cmd: cmd and len(cmd) > 0, gcode)

        return "\n".join(gcode)

    def compile_to_file(self, file_name: str, passes=1):
        with open(file_name, "w") as f:
            f.write(self.compile(passes=passes))

    def append_line_chain(self, line_chain: LineSegmentChain):

        if line_chain.chain_size() == 0:
            return

        code = []
        start = line_chain.get(0).start

        if (
            self.interface.position is None
            or abs(self.interface.position - start) > TOLERANCES["operation"]
        ):
            code = [
                self.interface.laser_off(),
                self.interface.set_movement_speed(self.movement_speed),
                self.interface.linear_move(start.x, start.y),
                self.interface.set_movement_speed(self.cutting_speed),
                self.interface.set_laser_power(1),
            ]

            if self.dwell_time > 0:
                code.insert(0, self.interface.dwell(self.dwell_time))

        for line in line_chain:
            code.append(self.interface.linear_move(line.end.x, line.end.y))

        self.body.extend(code)

    def append_curves(self, curves: typing.List[Curve]):

        for curve in curves:
            line_chain = LineSegmentChain()
            approximation = LineSegmentChain.line_segment_approximation(curve)
            line_chain.extend(approximation)
            self.append_line_chain(line_chain)

    def _reverse_chain(self, chain: LineSegmentChain) -> LineSegmentChain:
        reversed_chain = LineSegmentChain()

        segments = list(chain)
        segments.reverse()

        for segment in segments:
            # swap start and end
            reversed_chain.append(
                type(segment)(
                    segment.end,
                    segment.start
                )
            )

        return reversed_chain

    def _optimize_chain_order(self, chains: typing.List[LineSegmentChain]):

        if not chains:
            return []

        remaining = chains[:]
        ordered = []

        # Start with first chain
        current = remaining.pop(0)
        ordered.append(current)

        current_pos = current.get(-1).end

        while remaining:
            best_index = None
            best_distance = float("inf")
            reverse_chain = False

            for i, chain in enumerate(remaining):
                start = chain.get(0).start
                end = chain.get(-1).end

                dist_to_start = abs(current_pos - start)
                dist_to_end = abs(current_pos - end)

                if dist_to_start < best_distance:
                    best_distance = dist_to_start
                    best_index = i
                    reverse_chain = False

                if dist_to_end < best_distance:
                    best_distance = dist_to_end
                    best_index = i
                    reverse_chain = True

            next_chain = remaining.pop(best_index)

            if reverse_chain:
                next_chain = self._reverse_chain(next_chain)

            ordered.append(next_chain)
            current_pos = next_chain.get(-1).end

        return ordered

    def append_curves_optimized(self, curves: typing.List[Curve]):

        # Convert all curves to line chains
        chains = []
        for curve in curves:
            line_chain = LineSegmentChain()
            approximation = LineSegmentChain.line_segment_approximation(curve)
            line_chain.extend(approximation)
            if line_chain.chain_size() > 0:
                chains.append(line_chain)

        # Reorder chains
        ordered = self._optimize_chain_order(chains)

        visualize_chains(ordered)

        # Append in optimized order
        for chain in ordered:
            self.append_line_chain(chain)


# ============================================================
# GRBL Interface
# ============================================================

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

    def linear_move(self, x=None, y=None, z=None, command="G1"):
        if self._next_speed is None:
            raise ValueError("Call set_movement_speed before moving")

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

    def cutting_move(self, x, y):
        return self.linear_move(x, y, command="G1")

    def non_cutting_move(self, x, y):
        return self.linear_move(x, y, command="G0")

    def laser_off(self):
        return "M5"

    def set_laser_power(self, power):
        if not 0 <= power <= 1:
            raise ValueError("Power must be between 0 and 1")
        return f"M3 S{int(power * self.max_power)}"

    def set_absolute_coordinates(self):
        return "G90"

    def set_relative_coordinates(self):
        return "G91"

    def dwell(self, milliseconds):
        return f"G4 P{milliseconds / 1000}"

    def set_origin_at_position(self):
        return "G92 X0 Y0"

    def set_unit(self, unit):
        if unit is None:
            return ""
        if unit.lower() == "mm":
            return "G21"
        if unit.lower() == "in":
            return "G20"
        return ""

    def home_axes(self):
        return "G0 X0 Y0 Z0"


# ============================================================
# GRBL Compiler
# ============================================================

class GRBLLaserCompiler(Compiler):

    def __init__(
        self,
        interface_class,
        movement_speed,
        cutting_speed,
        pass_depth,
        laser_power,
        dwell_time=0,
        unit=None,
        custom_header=None,
        custom_footer=None,
        custom_between_pass_code=None,
    ):
        super().__init__(
            interface_class,
            movement_speed,
            cutting_speed,
            pass_depth,
            dwell_time,
            unit,
            custom_header,
            custom_footer,
            custom_between_pass_code,
        )
        self.laser_power = laser_power

    def append_line_chain(self, line_chain: LineSegmentChain):

        if line_chain.chain_size() == 0:
            return

        code = []
        start = line_chain.get(0).start

        if (
            self.interface.position is None
            or abs(self.interface.position - start) > TOLERANCES["operation"]
        ):
            code = [
                self.interface.laser_off(),
                self.interface.set_movement_speed(self.movement_speed),
                self.interface.non_cutting_move(start.x, start.y),
                self.interface.set_movement_speed(self.cutting_speed),
                self.interface.set_laser_power(self.laser_power),
            ]

            if self.dwell_time > 0:
                code.insert(0, self.interface.dwell(self.dwell_time))

        for line in line_chain:
            code.append(self.interface.cutting_move(line.end.x, line.end.y))

        self.body.extend(code)

    def clear_curves(self):
        self.body.clear()


# ============================================================
# Configurations
# ============================================================

BEAM_WIDTH_MM = 3.175

CONFIG_CUT = {
    "movement_speed": 3000,
    "cutting_speed": 1000,
    "passes": 8,
    "pass_depth": BEAM_WIDTH_MM / 8,
    "laser_power": 0.6,
    "dwell_time": 0,
}

CONFIG_ENGRAVE = {
    "movement_speed": 1500,
    "cutting_speed": 800,
    "passes": 1,
    "pass_depth": 0,
    "laser_power": 0.4,
    "dwell_time": 0,
}

SUFFIX_CONFIG_MAP = {
    ".CUT.svg": CONFIG_CUT,
    ".ENGRAVE.svg": CONFIG_ENGRAVE,
}


# ============================================================
# Processing Logic
# ============================================================

INPUT_DIR = "./original"
OUTPUT_DIR = "./sliced"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def build_compiler(config):
    interface = GRBLLaserInterface()
    interface.set_movement_speed(config["movement_speed"])

    return GRBLLaserCompiler(
        GRBLLaserInterface,
        movement_speed=config["movement_speed"],
        cutting_speed=config["cutting_speed"],
        pass_depth=config["pass_depth"],
        laser_power=config["laser_power"],
        dwell_time=config["dwell_time"],
        custom_header=[
            interface.laser_off(),
            interface.home_axes(),
            "G90",
        ],
        custom_footer=[
            interface.laser_off(),
            interface.home_axes(),
        ],
        unit="mm",
    )


def process_file(file_path, config):

    print(f"\nParsing: {file_path}")
    curves = parse_file(file_path)

    compiler = build_compiler(config)
    compiler.clear_curves()
    compiler.append_curves_optimized(curves)

    base = os.path.basename(file_path)
    base = base.rsplit(".", 1)[0]
    base = base.rsplit(".", 1)[0]

    out_path = os.path.join(OUTPUT_DIR, base + ".gcode")

    compiler.compile_to_file(out_path, passes=config["passes"])

    print("Wrote:", out_path)


import matplotlib.pyplot as plt


def visualize_chains(chains):

    plt.figure()
    ax = plt.gca()

    current_pos = None
    chain_number = 1

    for chain in chains:

        segments = list(chain)

        if not segments:
            continue

        start = segments[0].start

        # Draw travel move (red dashed)
        if current_pos is not None:
            plt.plot(
                [current_pos.x, start.x],
                [current_pos.y, start.y],
                linestyle="--"
            )

        # Draw cut segments (solid)
        for segment in segments:
            plt.plot(
                [segment.start.x, segment.end.x],
                [segment.start.y, segment.end.y]
            )

        # Label chain start
        plt.text(start.x, start.y, str(chain_number))

        current_pos = segments[-1].end
        chain_number += 1

    plt.title("Toolpath Visualization")
    plt.xlabel("X (mm)")
    plt.ylabel("Y (mm)")
    plt.axis("equal")
    plt.show()

# ============================================================
# Main
# ============================================================

for suffix, config in SUFFIX_CONFIG_MAP.items():
    pattern = os.path.join(INPUT_DIR, f"*{suffix}")
    for file in glob.glob(pattern):
        process_file(file, config)

print("\nAll files processed.")