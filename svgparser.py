import math
import xml.etree.ElementTree as ET
import svgpathtools
import subprocess
from io import StringIO
import matplotlib.pyplot as plt
from MakeBlockXYPlotter import MakeBlockXYPlotterInterface


# Define the common paper sizes in inches
# DO NOT USE THESE DIRECTLY, THIS PROGRAM WORKS ONLY IN MM!
# use PAPER_SIZES_MM defined below
PAPER_SIZES_IN = {
    "Letter": (8.5, 11),
    "Legal": (8.5, 14),
    "A3": (11.69, 16.54),
    "A4": (8.27, 11.69),
    "A5": (5.83, 8.27),
    "Tabloid": (11, 17)
}

# Conversion function: inches to millimeters
def inches_to_mm(size_in_inches):
    return tuple(round(dim * 25.4, 2) for dim in size_in_inches)

# Create the paper sizes in millimeters at runtime
PAPER_SIZES_MM = {key: inches_to_mm(value) for key, value in PAPER_SIZES_IN.items()}

class SVGPath:
    def __init__(self, path_data, power=1, passes=1):
        self.path_data = path_data
        self.power = float(power)
        self.passes = int(passes)

    def __repr__(self):
        return f"SVGPath(power={self.power}, passes={self.passes})"


class SVGProcessor:
    def __init__(self, input_file, paper_size=PAPER_SIZES_MM["Letter"]):
        self.input_file = input_file
        self.paper_size = paper_size
        self.paths = []
        self.header = []  # List of G-code to be placed at the start
        self.footer = []  # List of G-code to be placed at the end
        self.between_paths = []  # List of G-code to be placed between paths

    def preprocess_svg(self):
        """Preprocess the SVG file using Inkscape."""
        preprocess_command = [
            'inkscape',
            self.input_file,
            '--export-text-to-path',
            '--export-plain-svg',
            '--export-filename=-'
        ]
        result = subprocess.run(preprocess_command, capture_output=True, text=True)
        return result.stdout

    def parse_svg(self, svg_content):
        """Parse the SVG file and extract path data with power and passes attributes."""
        svg_file = StringIO(svg_content)
        tree = ET.parse(svg_file)
        root = tree.getroot()

        ns = {'svg': 'http://www.w3.org/2000/svg'}
        for element in root.findall('.//svg:*', ns):
            path_data = element.attrib.get('d')
            passes = element.attrib.get('passes', 1)
            power = element.attrib.get('power', 1)

            if path_data:
                path_obj = SVGPath(path_data, power, passes)
                self.paths.append(path_obj)

    def convert_paths_to_points(self, points_per_mm):
        """Convert the stored paths into points with specified density."""
        all_points = []
        for svg_path in self.paths:
            points = self.path_to_points(svg_path.path_data, points_per_mm)
            all_points.append((points, svg_path.power, svg_path.passes))
        return all_points

    def path_to_points(self, path_data, points_per_inch):
        """Convert SVG path data to a list of points."""
        path = svgpathtools.parse_path(path_data)
        total_length = path.length()
        num_points = int(total_length * points_per_inch)

        points = []
        for i in range(num_points + 1):
            t = i / num_points
            point = path.point(t)
            x_mm = point.real
            y_mm = self.paper_size[1] - point.imag
            points.append((x_mm, y_mm))

        return points

    def generate_gcode(self, interface, points_per_inch):
        """Generate G-code for each path and move through the points."""
        gcode = []
        points_with_attributes = self.convert_paths_to_points(points_per_inch)

        # Add header G-code via interface functions
        gcode.extend(self.header)

        for points, power, passes in points_with_attributes:
            # Add G-code between paths (if any)
            gcode.extend(self.between_paths)

            if points:
                # Move to the start of the path
                start_point = points[0]
                gcode.append(interface.non_cutting_move(start_point[0], start_point[1]))

                # Set laser power
                gcode.append(interface.set_laser_power(power))
                for _ in range(passes):
                    for x, y in points:
                        gcode.append(interface.cutting_move(x, y))

                # Turn off the laser after the path is complete
                gcode.append(interface.laser_off())

        # Add footer G-code via interface functions
        gcode.extend(self.footer)

        return "\n".join(gcode)

    def calculate_total_path_length(self):
        """Calculate the total length of all SVG paths."""
        total_length = 0
        for svg_path in self.paths:
            path = svgpathtools.parse_path(svg_path.path_data)
            total_length += path.length()
        return total_length

    def calculate_estimated_time(self, movement_speed_mm_per_sec):
        """Estimate the time to complete the plot based on the movement speed (in mm/sec)."""
        total_length = self.calculate_total_path_length()
        estimated_time_sec = total_length / movement_speed_mm_per_sec

        # Convert seconds into hours, minutes, and seconds
        hours = estimated_time_sec // 3600
        minutes = (estimated_time_sec % 3600) // 60
        seconds = estimated_time_sec % 60

        # Create a human-readable time string
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s" if hours > 0 else f"{int(minutes)}m {int(seconds)}s"

    def plot_paths(self, points_per_inch, paper_size):
        """Plot the parsed paths using matplotlib, invert the Y-axis and lock axis limits."""
        all_points = self.convert_paths_to_points(points_per_inch)

        # Create a new plot
        plt.figure(figsize=(8.5*2, 11*2))

        for points, _, _ in all_points:
            if points:
                x_vals = [point[0] for point in points]
                y_vals = [point[1] for point in points]
                plt.scatter(x_vals, y_vals, s=1)

        # Set axis limits to the size of a paper in mm (A4 paper size as default)
        plt.xlim(0, paper_size[0])
        plt.ylim(0, paper_size[1])

        # Invert the Y-axis after setting the limits
        # plt.gca().invert_yaxis()

        # Set plot title and labels
        plt.title('SVG Paths')
        plt.xlabel('X (mm)')
        plt.ylabel('Y (mm)')

        # Enable grid and set grid lines every 10mm (1cm)
        plt.grid(True)

        # Set grid interval every 10mm (1 cm)
        plt.xticks(range(0, math.ceil(paper_size[0]) + 1, 10))
        plt.yticks(range(0, math.ceil(paper_size[1]) + 1, 10))

        # Show the plot
        plt.show()


# Example usage
input_svg_file = 'original/pi.svg'
points_per_inch = 5

# Create an SVGProcessor and interface instance
svg_processor = SVGProcessor(input_svg_file)
interface = MakeBlockXYPlotterInterface()

# Set custom G-code for header, footer, and between paths using interface functions
svg_processor.header = [
    interface.set_unit('mm'),
    interface.laser_off(),
    interface.set_absolute_coordinates(),
    interface.home_axes(),
]
svg_processor.footer = [
    interface.laser_off(),
    interface.home_axes(),
]

# Preprocess the SVG
svg_content = svg_processor.preprocess_svg()

# Parse the SVG to extract paths
svg_processor.parse_svg(svg_content)

# Generate G-code from the paths
gcode = svg_processor.generate_gcode(interface, points_per_inch)

# Output the G-code
open("test.gcode", "w").write(gcode)

print(svg_processor.calculate_total_path_length())
print(svg_processor.calculate_estimated_time(7.2))

# Plot the paths with inverted Y-axis and locked axis limits
svg_processor.plot_paths(points_per_inch, PAPER_SIZES_MM["Letter"])
