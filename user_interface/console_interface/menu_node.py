from user_interface.console_interface.console_ui_context import ConsoleUIContext

from .navigation_node import NavigationNode
from .focus_area import FocusArea

from .board_node import BoardNode
from .panel_node import PanelNode
from .action_node import ActionNode

class MenuNode(NavigationNode):
    def __init__(self, context: ConsoleUIContext):
        super().__init__(context)

        self.options: list[type[NavigationNode]] = [BoardNode, PanelNode, ActionNode]
        self.selected_index: int = 0

    @property
    def focus_area(self):
        return FocusArea.MENU

    def handle_input(self, key):
        if key == "enter":
            selected_node_class = self.options[self.selected_index]
            selected_node = selected_node_class(context=self.context)
            self.context.add_focus(selected_node)
        elif key == "left":
            if self.selected_index > 0:
                self.selected_index -= 1

        elif key == "right":
            if self.selected_index < len(self.options) - 1:
                self.selected_index += 1
