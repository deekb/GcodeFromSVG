# plotter.py

import matplotlib.pyplot as plt
from .path_parser import PathParser


class PathPlotter:
    def __init__(self, character_paths):
        self.character_paths = character_paths

    def plot(self, character, paths):
        """Plot all the paths for a given character."""
        try:
            fig, ax = plt.subplots()

            for path_data in paths:
                if not path_data.strip():  # Skip empty paths
                    continue

                path_parser = PathParser(path_data)
                path = path_parser.parse()

                if path and len(path.vertices) > 0:
                    ax.plot(*path.vertices.T, color='black')
                else:
                    print(f"Empty path for character '{character}', skipping.")

            # Set up the plot for display
            ax.set_aspect('equal', 'box')
            ax.set_axis_off()
            ax.set_title(f"Character: {character}")
            plt.show()

        except Exception as e:
            print(f"Error plotting paths for character '{character}': {e}")

    def plot_all(self):
        """Plot all characters with their respective paths."""
        for character, path_data in self.character_paths.items():
            path_parser = PathParser(path_data)
            paths = path_parser.split_paths()
            self.plot(character, paths)
