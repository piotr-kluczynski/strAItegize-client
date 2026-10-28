from .navigation_node import NavigationNode
from .focus_area import FocusArea

class PanelRecruitNode(NavigationNode):
    @property
    def focus_area(self):
        return FocusArea.PANEL_RECRUIT

    def handle_input(self, key):
        pass