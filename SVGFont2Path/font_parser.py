# font_parser.py

import xml.etree.ElementTree as ET

class SVGFontParser:
    def __init__(self, svg_font_path):
        self.svg_font_path = svg_font_path
        self.character_paths = {}

    def parse(self):
        """Parse the SVG font and extract character paths."""
        try:
            # Parse the SVG file
            tree = ET.parse(self.svg_font_path)
            root = tree.getroot()

            # Find all 'glyph' elements
            glyphs = root.findall('.//{http://www.w3.org/2000/svg}glyph')

            if not glyphs:
                print("No 'glyph' elements found. Checking root structure...")
                for elem in root.iter():
                    print(f"Element: {elem.tag} - Attributes: {elem.attrib}")

            # Extract character paths and store in a dictionary
            for glyph in glyphs:
                unicode = glyph.get('unicode')
                d = glyph.get('d')

                if unicode and d:
                    # Save the path data for the corresponding unicode character
                    self.character_paths[unicode] = d
        except Exception as e:
            print(f"Error processing SVG font: {e}")

    def get_character_paths(self):
        """Return the extracted character paths."""
        return self.character_paths
