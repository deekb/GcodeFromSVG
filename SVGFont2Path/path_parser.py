import re
import svgpath2mpl

class PathParser:
    def __init__(self, path_data):
        self.path_data = path_data

    def split_paths(self):
        """Split the path data into individual path segments and convert each into a Matplotlib path object."""
        segments = re.split(r'(?=M)', self.path_data.strip())  # Split by 'M' (move-to) and keep it in each segment
        path_objs = []
        for seg in segments:
            if seg.strip():  # Skip empty segments
                try:
                    path_obj = svgpath2mpl.parse_path(seg)
                    if path_obj is not None and len(path_obj.vertices) > 0:
                        path_objs.append(path_obj)
                except Exception as e:
                    print(f"Error parsing segment: {e}")
        return path_objs

    def parse(self):
        """Convert the entire SVG path data into a single Matplotlib path object."""
        try:
            path = svgpath2mpl.parse_path(self.path_data)
            return path
        except Exception as e:
            print(f"Error parsing path data: {e}")
            return None
