from user_interface.console_interface.console_ui_context import ConsoleUIContext

from .navigation_node import NavigationNode
from .focus_area import FocusArea
from .panel_recruit_node import PanelRecruitNode

class PanelRegionsNode(NavigationNode):
    def __init__(self, context: ConsoleUIContext):
        super().__init__(context)

    @property
    def focus_area(self):
        return FocusArea.PANEL_REGIONS

    def handle_input(self, key):
        region_count = len(self.context.regions)
        if key == "esc":
            self.context.pop_focus()
        elif key == "enter" and region_count :
            cursor = min(self.context.user_interface.regions_cursor, region_count - 1)
            self.context.user_interface.regions_cursor = cursor
            region_data = list(self.context.regions.values())[cursor]
            q, r, s = region_data.command_center
            self.context.change_center_tile(q, r, s)

            if self.context.sim_phase == "Upkeep":
                regions = list(self.context.regions.values())
                cursor = min(self.context.user_interface.regions_cursor, region_count - 1)
                self.context.user_interface.recruit_form["region"] = regions[cursor].region_id
                self.context.add_focus(PanelRecruitNode(self.context))
        elif region_count and key in ("up", "down"):
            cursor = self.context.user_interface.regions_cursor
            offset = -1 if key == "up" else 1
            self.context.user_interface.regions_cursor = max(0, min(cursor + offset, region_count - 1))