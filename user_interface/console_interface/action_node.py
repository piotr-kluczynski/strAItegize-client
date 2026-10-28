from .navigation_node import NavigationNode
from .console_ui_context import ConsoleUIContext

from .focus_area import FocusArea

class ActionNode(NavigationNode):
    def __init__(self, context: ConsoleUIContext):
         super().__init__(context)

    @property
    def focus_area(self):
        return FocusArea.ACTION

    def handle_input(self, key):
        if key == "esc":
            self.context.pop_focus()
        elif key == "enter":
            # Perform the action associated with this node
            self.context.perform_action()
     