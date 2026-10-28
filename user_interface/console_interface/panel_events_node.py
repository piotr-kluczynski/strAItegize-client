from .navigation_node import NavigationNode
from .focus_area import FocusArea

class PanelEventsNode(NavigationNode):
    @property
    def focus_area(self):
        return FocusArea.PANEL_EVENTS

    def handle_input(self, key):
        events_count = len(self.context.events)
        if key == "esc":
            self.context.pop_focus()
        elif events_count and key in ("up", "down"):
            cursor = self.context.user_interface.events_cursor
            offset = -1 if key == "up" else 1
            self.context.user_interface.events_cursor = max(0, min(cursor + offset, events_count - 1))