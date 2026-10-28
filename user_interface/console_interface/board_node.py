from .navigation_node import NavigationNode
from .console_ui_context import ConsoleUIContext
from .focus_area import FocusArea

class BoardNode(NavigationNode):
    def __init__(self, context: ConsoleUIContext):
        super().__init__(context)
        
    @property
    def focus_area(self):
        return FocusArea.BOARD

    def handle_input(self, key):
        directions = {
            "up": (0, -1, 1),
            "down": (0, 1, -1),
            "left": (-1, 0, 1),
            "right": (1, 0, -1),
        }

        if key == "esc":
            self.context.pop_focus()
        elif key in directions:
            q, r, s = self.context.user_interface.center_tile
            dq, dr, ds = directions[key]
            
            self.context.change_center_tile(q + dq, r + dr, s + ds)