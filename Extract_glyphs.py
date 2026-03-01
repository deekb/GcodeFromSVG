import numpy as np
import xml.etree.ElementTree as ET
from svgpathtools import parse_path
import json

# Character set (as you described)
glyph_chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"

# Load SVG
svg_path = "Font.svg"
tree = ET.parse(svg_path)
root = tree.getroot()

# Get all path elements
paths = root.findall(".//{http://www.w3.org/2000/svg}path")

print(glyph_chars)
print(paths)

if len(paths) != len(glyph_chars):
    print(f"⚠️ Warning: {len(paths)} paths found, expected {len(glyph_chars)} glyphs.")


# Normalize function to scale and center points within a fixed size
def normalize_points(points, size):
    points = np.array(points)
    min_x, min_y = points.min(axis=0)
    max_x, max_y = points.max(axis=0)

    # Calculate the scale factor to fit within the target size
    scale = size / max(max_x - min_x, max_y - min_y)

    # Center the glyph in the middle of the bounding box
    offset_x = (size - (max_x - min_x) * scale) / 2 - min_x * scale
    offset_y = (size - (max_y - min_y) * scale) / 2 - min_y * scale

    # Apply scale and offset to each point
    normalized_points = [(round(p[0] * scale + offset_x, 4), round(p[1] * scale + offset_y, 4)) for p in points]

    return normalized_points


# Map glyphs to points
glyph_points = {}

for char, path_elem in zip(glyph_chars, paths):
    d = path_elem.attrib.get('d')
    if d:
        path = parse_path(d)
        points = []
        for segment in path:
            # Extract the key points (start, control, and end points) of the segment
            if segment.__class__.__name__ == 'Line':
                points.append((round(segment.start.real, 4), round(segment.start.imag, 4)))
                points.append((round(segment.end.real, 4), round(segment.end.imag, 4)))
            elif segment.__class__.__name__ == 'CubicBezier':
                points.append((round(segment.start.real, 4), round(segment.start.imag, 4)))
                points.append((round(segment.control1.real, 4), round(segment.control1.imag, 4)))
                points.append((round(segment.control2.real, 4), round(segment.control2.imag, 4)))
                points.append((round(segment.end.real, 4), round(segment.end.imag, 4)))
            elif segment.__class__.__name__ == 'QuadraticBezier':
                points.append((round(segment.start.real, 4), round(segment.start.imag, 4)))
                points.append((round(segment.control.real, 4), round(segment.control.imag, 4)))
                points.append((round(segment.end.real, 4), round(segment.end.imag, 4)))
            elif segment.__class__.__name__ == 'Arc':
                points.append((round(segment.start.real, 4), round(segment.start.imag, 4)))
                points.append((round(segment.end.real, 4), round(segment.end.imag, 4)))

        # Normalize the points for this character
        normalized_points = normalize_points(points, size=100)  # Normalize to fit within a 100x100 box
        glyph_points[char] = normalized_points

# Convert lists to numpy arrays
glyph_arrays = {char: np.array(points, dtype=np.float32) for char, points in glyph_points.items()}

print(glyph_arrays)

# Save to .npz
np.savez("glyph_points_normalized.npz", **glyph_arrays)
print("✅ Saved as glyph_points_normalized.npz")
