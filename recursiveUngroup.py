import inkex


class UngroupSVG(inkex.Effect):
    def __init__(self):
        super().__init__()

    def ungroup(self, element):
        # If the element is a group, ungroup its children
        if element.tag == inkex.addNS('g', 'svg'):
            # Collect children of the group
            children = list(element)
            # Remove the group tag and add its children to the parent
            for child in children:
                element.getparent().append(child)
            # Remove the group element itself
            element.getparent().remove(element)
        # Recursively ungroup children
        for child in list(element):
            self.ungroup(child)

    def effect(self):
        # Start with the root element
        root = self.document.getroot()
        self.ungroup(root)
        string = ""
        # Save the modified document
        # self.save_raw(string)
        # print(string)


# Run the effect
if __name__ == '__main__':
    UngroupSVG().run()
