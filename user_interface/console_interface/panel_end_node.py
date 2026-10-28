from .navigation_node import NavigationNode
from .focus_area import FocusArea

class PanelEndNode(NavigationNode):
    @property
    def focus_area(self):
        return FocusArea.PANEL_END

    def handle_input(self, key):
        pass