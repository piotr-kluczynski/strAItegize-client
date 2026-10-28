from user_interface.console_interface.console_ui_context import ConsoleUIContext

from .navigation_node import NavigationNode
from .focus_area import FocusArea

class PanelStatusNode(NavigationNode):
    def __init__(self, context: ConsoleUIContext):
        super().__init__(context)

    @property
    def focus_area(self):
        return FocusArea.PANEL_STATUS

    def handle_input(self, key):
        if key == "esc":
            self.context.pop_focus()