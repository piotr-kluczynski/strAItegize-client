from .navigation_node import NavigationNode
from .focus_area import FocusArea
from .panel_order_node import PanelOrderNode

class PanelUnitsNode(NavigationNode):
    @property
    def focus_area(self):
        return FocusArea.PANEL_UNITS

    def handle_input(self, key):
        units_count = len(self.context.units)
        if key == "esc":
            self.context.pop_focus()
        elif key == "enter" and units_count:
            cursor = min(self.context.user_interface.units_cursor, units_count - 1)
            self.context.user_interface.units_cursor = cursor
            unit_data = list(self.context.units.values())[cursor]
            self.context.user_interface.center_map_on(unit_data.tile)
            
            if self.context.sim_phase == "Planning":
                units = list(self.context.units.values())
                cursor = min(self.context.user_interface.units_cursor, units_count - 1)
                self.context.user_interface.order_form["unit_id"] = units[cursor].unit_id
                self.context.add_focus(PanelOrderNode(self.context))
        elif units_count and key in ("up", "down"):
            cursor = self.context.user_interface.units_cursor
            offset = -1 if key == "up" else 1
            self.context.user_interface.units_cursor = max(0, min(cursor + offset, units_count - 1))