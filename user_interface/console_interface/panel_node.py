from typing import Literal

from .navigation_node import NavigationNode
from .focus_area import FocusArea

from .panel_status_node import PanelStatusNode
from .panel_events_node import PanelEventsNode
from .panel_units_node import PanelUnitsNode
from .panel_regions_node import PanelRegionsNode

from .console_ui_context import ConsoleUIContext

class PanelNode(NavigationNode):
    def __init__(self, context: ConsoleUIContext):
        super().__init__(context)

        self.options: list[type[NavigationNode]] = [PanelStatusNode, PanelEventsNode, PanelUnitsNode, PanelRegionsNode]
        self.pages: tuple[Literal["Status", "Events", "Units", "Regions"], ...] = (
            "Status", "Events", "Units", "Regions"
        )
        self.selected_index = self.pages.index(context.user_interface.info_panel_page)

    @property
    def focus_area(self):
        return FocusArea.PANEL

    def handle_input(self, key):
        if key == "esc":
            self.context.pop_focus()
        elif key == "enter":
            selected_node_class = self.options[self.selected_index]
            selected_node = selected_node_class(context=self.context)
           
            self.context.add_focus(selected_node)
        elif key == "left":
            if self.selected_index > 0:
                self.selected_index -= 1
        elif key == "right":
            if self.selected_index < len(self.options) - 1:
                self.selected_index += 1

        if key in ("left", "right"):
            self.context.user_interface.info_panel_page = self.pages[self.selected_index]
