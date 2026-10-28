from .navigation_node import NavigationNode
from .focus_area import FocusArea

class PanelOrderNode(NavigationNode):
    @property
    def focus_area(self):
        return FocusArea.PANEL_ORDER

    def handle_input(self, key):
        pass