import sys
import os
from typing import Literal, Optional, Any

from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.columns import Columns
from rich.align import Align
from rich.text import Text
from rich.table import Table

# Ensure Windows terminal handles UTF-8 (for upperscore '‾', star '★', and symbols)
if sys.platform == "win32":
    try:
        os.system("")
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from ..user_interface import UserInterface
    from .focus_area import FocusArea
    from .navigation_node import NavigationNode
    from .menu_node import MenuNode
    from .board_node import BoardNode
    from .panel_node import PanelNode
except (ImportError, ValueError):
    from user_interface.user_interface import UserInterface
    from user_interface.console_interface.focus_area import FocusArea
    from user_interface.console_interface.navigation_node import NavigationNode
    from user_interface.console_interface.menu_node import MenuNode
    from user_interface.console_interface.board_node import BoardNode
    from user_interface.console_interface.panel_node import PanelNode

try:
    from strAItegize_common.others.order import Order
    from strAItegize_common.others.recruitment_choice import RecruitmentChoice
except ImportError:
    Order = None
    RecruitmentChoice = None


# Upperscore / overline ('‾') for connecting hex tops
UPPERSCORE = "\u203e"  # '‾'


class ConsoleInterface(UserInterface):
    def __init__(self):
        super().__init__()
        
        self.focus_stack: list[NavigationNode] = [MenuNode(context=self.ui_context)]
        self.info_panel_page: Literal["Status", "Events", "Units", "Regions"] = "Status"
        self.console = Console()
        self.running = False
        self.cursor_coord: tuple[int, int, int] = (0, 0, 0)
        self.events_cursor: int = 0
        self.units_cursor: int = 0
        self.regions_cursor: int = 0
        self.center_tile: tuple[int, int, int] = (0, 0, 0)

        # Optional Extra Screen: None, 'order', or 'recruit'
        self.active_extra_screen: Optional[Literal["order", "recruit"]] = None
        self.extra_form_error: Optional[str] = None

        # Order Form state (Order: order_type, unit_id, target_id, move_q, move_r, move_s)
        self.order_fields = ["order_type", "unit_id", "target_id", "move_q", "move_r", "move_s"]
        self.order_field_idx: int = 0
        self.order_form = {
            "order_type": "move",
            "unit_id": "light_infantry_2",
            "target_id": None,
            "move_q": 1,
            "move_r": 0,
            "move_s": -1,
        }

        # Recruitment Form state (RecruitmentChoice: unit_type, region)
        self.recruit_fields = ["unit_type", "region"]
        self.recruit_field_idx: int = 0
        self.recruit_form = {
            "unit_type": "light_infantry",
            "region": "SampleLand",
        }

    @property
    def current_focus(self) -> Optional[FocusArea]:
        if self.focus_stack:
            return self.focus_stack[-1].focus_area
        return None

    @property
    def next_focus(self) -> Optional[FocusArea]:
        if not self.focus_stack:
            return None

        current_node = self.focus_stack[-1]
        options = getattr(current_node, "options", None)
        if not options:
            return None

        selected_index = current_node.selected_index % len(options)
        selected_node = options[selected_index](context=self.ui_context)
        return selected_node.focus_area

    @property
    def extra_field_idx(self) -> int:
        return self.order_field_idx if self.active_extra_screen == "order" else self.recruit_field_idx

    @extra_field_idx.setter
    def extra_field_idx(self, value: int) -> None:
        if self.active_extra_screen == "order":
            self.order_field_idx = value
        else:
            self.recruit_field_idx = value

    def handle_input(self, key: str):
        if key == "ctrl+c":
            self.running = False
            return
        if self.current_focus == FocusArea.PANEL_ORDER:
            self.active_extra_screen = "order"
            self._handle_extra_screen_input(key)
            return
        if self.current_focus == FocusArea.PANEL_RECRUIT:
            self.active_extra_screen = "recruit"
            self._handle_extra_screen_input(key)
            return
        self.active_extra_screen = None
        if self.focus_stack:
            self.focus_stack[-1].handle_input(key)

    def run(self) -> None:
        self.running = True
        try:
            while self.running:
                self.render()
                self.handle_input(self._read_key())
        except KeyboardInterrupt:
            self.running = False

    def _read_key(self) -> str:
        if os.name == "nt":
            import msvcrt

            key = msvcrt.getwch()
            if key in ("\x00", "\xe0"):
                extended_key = msvcrt.getwch()
                return {"H": "up", "P": "down", "K": "left", "M": "right"}.get(extended_key, "")
            return {"\r": "enter", "\x1b": "esc", "\x08": "backspace", "\x03": "ctrl+c"}.get(key, key)

        if not sys.stdin.isatty():
            raise RuntimeError("The console interface requires an interactive terminal.")

        import select
        import termios
        import tty

        input_fd = sys.stdin.fileno()
        previous_settings = termios.tcgetattr(input_fd)
        try:
            tty.setraw(input_fd)
            key = sys.stdin.read(1)
            if key == "\x1b":
                sequence = key
                while len(sequence) < 6 and select.select([sys.stdin], [], [], 0.05)[0]:
                    sequence += sys.stdin.read(1)
                return {"\x1b[A": "up", "\x1b[B": "down", "\x1b[D": "left", "\x1b[C": "right"}.get(sequence, "esc")
            return {"\r": "enter", "\n": "enter", "\x7f": "backspace", "\x03": "ctrl+c"}.get(key, key)
        finally:
            termios.tcsetattr(input_fd, termios.TCSADRAIN, previous_settings)

    def render(self):
        self.console.clear()

        # Check overall frame focus (yellow border if menu focused)
        frame_border_color = "white"
        if self.current_focus == FocusArea.MENU:
            frame_border_color = "yellow1"

        # ---------------------------------------------------------------------
        # Left Column: Game Map (Top) + Selected Tile Details (Bottom)
        # ---------------------------------------------------------------------
        board_panel = self.get_board(center_tile=self.center_tile)
        tile_details_panel = self.get_tile_details_panel()
        left_column = Group(
            board_panel,
            tile_details_panel
        )

        # ---------------------------------------------------------------------
        # Right Column: Information Panel + [Optional Extra Screen] + Sim Phase & End Turn
        # ---------------------------------------------------------------------
        info_panel = self.get_info_panel()
        extra_panel = self.get_extra_panel()
        btm_right_panel = Columns([
            self.get_sim_phase(),
            self.get_action()
        ])

        right_items = [info_panel]
        if extra_panel is not None:
            right_items.append(extra_panel)
        right_items.append(btm_right_panel)

        right_column = Group(*right_items)

        # ---------------------------------------------------------------------
        # Assemble Left and Right columns side-by-side using a 2-column Table Grid
        # ---------------------------------------------------------------------
        sim_screen = Table.grid(padding=(0, 1))
        sim_screen.add_column(justify="left")
        sim_screen.add_column(justify="left")
        sim_screen.add_row(left_column, right_column)
        sim_screen.width = 108

        sim_panel = Panel(
            sim_screen,
            title="[bold cyan]StrAItegize Simulation[/bold cyan]",
            border_style=frame_border_color,
            expand=False,
        )
        self.console.print(sim_panel)

    # -------------------------------------------------------------------------
    # Section 1: Simulation Board Visualization
    # -------------------------------------------------------------------------
    def get_board(self, center_tile: Optional[tuple[int, int, int]] = None) -> Panel:
        """
        Renders the hexagonal simulation map.
        Always displays a fixed screen of tiles filling the viewport,
        centered at `center_tile` (q, r, s).
        Tiles not existing in data are visualized as 'blocked tiles'.
        """
        if center_tile is None:
            center_tile = self.cursor_coord or (0, 0, 0)

        is_focused = (self.current_focus == FocusArea.BOARD)
        is_next = self.next_focus == FocusArea.BOARD
        border_style = "bright_yellow" if is_focused else ("bright_cyan" if is_next else "dim white")
        title = f"[bold yellow]● Map [{center_tile[0]},{center_tile[1]},{center_tile[2]}][/bold yellow]" if is_focused else f"Map [{center_tile[0]},{center_tile[1]},{center_tile[2]}]"
        if is_next and not is_focused:
            title = f"[bold bright_cyan]Next: {title}[/bold bright_cyan]"

        tiles_data = getattr(self.ui_context, "tiles", {}) or {}

        # Render the hex grid onto a character canvas
        board_renderable = self._render_hex_grid(
            tiles=tiles_data,
            center_coord=center_tile,
            cursor_coord=self.cursor_coord,
            is_focused=is_focused
        )

        return Panel(
            board_renderable,
            title=title,
            border_style=border_style,
            padding=(0, 0),
            width=55,
        )

    def _render_hex_grid(
        self,
        tiles: dict[Any, Any],
        center_coord: tuple[int, int, int],
        cursor_coord: tuple[int, int, int],
        is_focused: bool
    ) -> Group:
        """
        Renders a fixed-size hexagonal viewport (radius 2) centered at `center_coord`.
        - All hexagons in the fixed viewport are always rendered.
        - Tiles not present in `tiles` data are showcased as 'blocked tiles' (dim red with ' · ').
        - Left-right neighbors share a single vertical bar ('|').
        - Step_y = 3 prevents vertical collision, eliminating the squeezed appearance of middle rows.
        - Regional borders are highlighted in bold magenta across horizontal roofs/floors, slants, and vertical walls.
        - Units do not color the whole hexagon; only the letter 'U' is highlighted in bright cyan (friendly) or bright red (enemy).
        """
        cq, cr, cs = center_coord
        your_id = getattr(self.ui_context, "your_id", "")

        # Keep the board viewport fixed so the surrounding frame does not resize.
        MAX_R = 2
        MAX_COL = 7
        offsets = []
        for dr in range(-MAX_R, MAX_R + 1):
            for dq in range(-MAX_COL, MAX_COL + 1):
                col_idx = 2 * dq + dr
                if -MAX_COL <= col_idx <= MAX_COL:
                    ds = -dq - dr
                    offsets.append((dq, dr, ds))

        offsets.sort(key=lambda item: (item[1], item[0]))

        # Center the origin in the rendered canvas, independently of the visible tile count.
        span_x = MAX_COL * 3 + 3
        span_y = MAX_R * 3 + 1
        padding_x = 2
        padding_y = 1

        canvas_width = 2 * (span_x + padding_x) + 1
        canvas_height = 2 * (span_y + padding_y) + 1
        origin_x = (canvas_width - 1) // 2
        origin_y = (canvas_height - 1) // 2

        char_buf = [[" " for _ in range(canvas_width)] for _ in range(canvas_height)]
        style_buf = [[None for _ in range(canvas_width)] for _ in range(canvas_height)]

        # Precompute viewport tile information
        viewport_map = {}
        for dq, dr, ds in offsets:
            wq = cq + dq
            wr = cr + dr
            ws = cs + ds
            world_coord = (wq, wr, ws)

            tile = tiles.get(world_coord) or tiles.get((wq, wr))
            # Tile is considered blocked if it does NOT exist in data
            is_blocked = (tile is None)
            region_id = self._get_tile_region_id(tile) if not is_blocked else "__blocked__"

            viewport_map[(dq, dr)] = {
                "world_coord": world_coord,
                "tile": tile,
                "is_blocked": is_blocked,
                "region_id": region_id,
                "dq": dq,
                "dr": dr
            }

        # Draw each hexagon in the fixed viewport
        for (dq, dr), hex_info in viewport_map.items():
            world_coord = hex_info["world_coord"]
            tile = hex_info["tile"]
            is_blocked = hex_info["is_blocked"]
            region_id = hex_info["region_id"]

            cx = origin_x + (2 * dq + dr) * 3
            cy = origin_y + dr * 3

            is_cmd_center = False if is_blocked else self._is_command_center(tile, world_coord)
            unit = None if is_blocked else self._get_unit_on_tile(tile, world_coord)
            has_unit = (unit is not None)
            is_cursor = (world_coord == cursor_coord) or ((world_coord[0], world_coord[1]) == (cursor_coord[0], cursor_coord[1]))

            # Determine unit friendliness
            is_friendly = True
            if unit:
                u_owner = getattr(unit, "owner", "")
                is_friendly = (u_owner == your_id)

            # 1. Base Border Style (Note: Units do NOT highlight the whole hexagon!)
            if is_blocked:
                hex_border_style = "dim red"
            elif is_cmd_center:
                hex_border_style = "bold gold1"
            else:
                hex_border_style = "dim white"

            # 2. Check Regional Boundaries with Neighbors for Highlighted Borders
            # East neighbor (dq + 1, dr)
            east_info = viewport_map.get((dq + 1, dr))
            east_reg = east_info["region_id"] if east_info else "__outside__"
            is_east_reg_border = (not is_blocked) and (region_id != east_reg)

            # West neighbor (dq - 1, dr)
            west_info = viewport_map.get((dq - 1, dr))
            west_reg = west_info["region_id"] if west_info else "__outside__"
            is_west_reg_border = (not is_blocked) and (region_id != west_reg)

            # North neighbors (dq, dr - 1) and (dq + 1, dr - 1)
            nw_info = viewport_map.get((dq, dr - 1))
            ne_info = viewport_map.get((dq + 1, dr - 1))
            nw_reg = nw_info["region_id"] if nw_info else "__outside__"
            ne_reg = ne_info["region_id"] if ne_info else "__outside__"
            is_north_reg_border = (not is_blocked) and ((region_id != nw_reg) or (region_id != ne_reg))

            # South neighbors (dq - 1, dr + 1) and (dq, dr + 1)
            sw_info = viewport_map.get((dq - 1, dr + 1))
            se_info = viewport_map.get((dq, dr + 1))
            sw_reg = sw_info["region_id"] if sw_info else "__outside__"
            se_reg = se_info["region_id"] if se_info else "__outside__"
            is_south_reg_border = (not is_blocked) and ((region_id != sw_reg) or (region_id != se_reg))

            # 3. Determine Interior 5-character Label & Style
            inner_str, inner_style = self._get_hex_content(
                is_cmd_center=is_cmd_center,
                has_unit=has_unit,
                is_friendly=is_friendly,
                is_blocked=is_blocked,
                is_cursor=(is_cursor and is_focused)
            )

            # Top roof (cy - 1): /‾‾‾\
            # Top-left slant at cx - 2
            if 0 <= cx - 2 < canvas_width and 0 <= cy - 1 < canvas_height:
                char_buf[cy - 1][cx - 2] = "/"
                style_buf[cy - 1][cx - 2] = "bold magenta" if (not is_blocked and region_id != nw_reg) else hex_border_style

            # Top horizontal overscore ‾‾‾ at cx - 1, cx, cx + 1
            roof_style = "bold magenta" if is_north_reg_border else hex_border_style
            for x in (cx - 1, cx, cx + 1):
                if 0 <= x < canvas_width and 0 <= cy - 1 < canvas_height:
                    char_buf[cy - 1][x] = UPPERSCORE
                    style_buf[cy - 1][x] = roof_style

            # Top-right slant at cx + 2
            if 0 <= cx + 2 < canvas_width and 0 <= cy - 1 < canvas_height:
                char_buf[cy - 1][cx + 2] = "\\"
                style_buf[cy - 1][cx + 2] = "bold magenta" if (not is_blocked and region_id != ne_reg) else hex_border_style

            # Middle line (cy): | ... |
            # Left vertical wall at cx - 3
            if 0 <= cx - 3 < canvas_width and 0 <= cy < canvas_height:
                char_buf[cy][cx - 3] = "|"
                if is_west_reg_border:
                    style_buf[cy][cx - 3] = "bold magenta"
                elif style_buf[cy][cx - 3] != "bold magenta":
                    style_buf[cy][cx - 3] = hex_border_style

            # Interior 5 chars
            for i, ch in enumerate(inner_str[:5]):
                x = cx - 2 + i
                if 0 <= x < canvas_width and 0 <= cy < canvas_height:
                    char_buf[cy][x] = ch
                    style_buf[cy][x] = inner_style

            # Right vertical wall at cx + 3 (single line shared with East neighbor)
            if 0 <= cx + 3 < canvas_width and 0 <= cy < canvas_height:
                char_buf[cy][cx + 3] = "|"
                if is_east_reg_border:
                    style_buf[cy][cx + 3] = "bold magenta"
                elif style_buf[cy][cx + 3] != "bold magenta":
                    style_buf[cy][cx + 3] = hex_border_style

            # Bottom floor (cy + 1): \___/
            # Lower-left slant at cx - 2
            if 0 <= cx - 2 < canvas_width and 0 <= cy + 1 < canvas_height:
                char_buf[cy + 1][cx - 2] = "\\"
                style_buf[cy + 1][cx - 2] = "bold magenta" if (not is_blocked and region_id != sw_reg) else hex_border_style

            # Bottom horizontal floor ___ at cx - 1, cx, cx + 1
            floor_style = "bold magenta" if is_south_reg_border else hex_border_style
            for x in (cx - 1, cx, cx + 1):
                if 0 <= x < canvas_width and 0 <= cy + 1 < canvas_height:
                    char_buf[cy + 1][x] = "_"
                    style_buf[cy + 1][x] = floor_style

            # Lower-right slant at cx + 2
            if 0 <= cx + 2 < canvas_width and 0 <= cy + 1 < canvas_height:
                char_buf[cy + 1][cx + 2] = "/"
                style_buf[cy + 1][cx + 2] = "bold magenta" if (not is_blocked and region_id != se_reg) else hex_border_style

        # Convert buffer to Rich Text
        map_text = Text()
        for y in range(canvas_height):
            line_text = Text()
            for x in range(canvas_width):
                char = char_buf[y][x]
                style = style_buf[y][x]
                line_text.append(char, style=style)
            map_text.append(line_text)
            map_text.append("\n")

        # Compact Legend below the board
        legend = Text.from_markup(
            "\n[bold gold1]★[/bold gold1] HQ  "
            "[bold bright_cyan]U[/bold bright_cyan] Friendly  "
            "[bold bright_red]U[/bold bright_red] Enemy  "
            "[dim red]·[/dim red] Blocked  "
            "[bold magenta]│[/bold magenta] Border\n"
            f"[dim]Center: [white]{center_coord}[/white] | Cursor: [white]{cursor_coord}[/white][/dim]"
        )

        return Group(map_text, legend)

    def _get_hex_content(
        self,
        is_cmd_center: bool,
        has_unit: bool,
        is_friendly: bool,
        is_blocked: bool,
        is_cursor: bool
    ) -> tuple[str, str]:
        """Returns the 5-character string and Rich style for the center of a hexagon."""
        if is_blocked:
            content = "  ·  "
            style = "dim red"
        elif is_cmd_center and not has_unit:
            content = "  ★  "
            style = "bold gold1"
        elif is_cmd_center and has_unit:
            content = " ★ U "
            style = "bold bright_cyan" if is_friendly else "bold bright_red"
        elif has_unit:
            content = "  U  "
            style = "bold bright_cyan" if is_friendly else "bold bright_red"
        else:
            # Empty steppable hex
            content = "  ·  "
            style = "dim white"

        # Active Cursor Highlight
        if is_cursor:
            content = f">{content[1:4]}<"
            style = "bold black on bright_yellow"

        return content, style

    def _get_tile_region_id(self, tile: Any) -> Optional[str]:
        """Extracts the string ID of the region a tile belongs to."""
        if not tile:
            return None
        region_ref = getattr(tile, "region", None)
        if isinstance(region_ref, str):
            return region_ref
        elif region_ref is not None:
            return getattr(region_ref, "region_id", None)
        return None

    def _is_command_center(self, tile: Any, coord: tuple[int, int, int]) -> bool:
        """Checks whether the tile is a command center."""
        if getattr(tile, "is_command_center", False):
            return True
        region_obj = self._get_region_for_tile(tile)
        if region_obj:
            cc = getattr(region_obj, "command_center", None)
            if cc == coord or (hasattr(cc, "q") and (cc.q, cc.r) == (coord[0], coord[1])):
                return True
        return False

    def _get_region_for_tile(self, tile: Any) -> Optional[Any]:
        """Resolves RegionData whether tile.region is a region_id string or a RegionData object."""
        region_ref = getattr(tile, "region", None)
        if isinstance(region_ref, str):
            regions = getattr(self.ui_context, "regions", {}) or {}
            return regions.get(region_ref)
        return region_ref

    def _get_unit_on_tile(self, tile: Any, coord: tuple[int, int, int]) -> Optional[Any]:
        """Resolves UnitData whether tile has a unit_id string, an object, or via ui_context.units."""
        unit_ref = getattr(tile, "unit", None)
        units_dict = getattr(self.ui_context, "units", {}) or {}
        if isinstance(unit_ref, str):
            return units_dict.get(unit_ref)
        elif unit_ref is not None:
            return unit_ref

        # Check by coordinate in ui_context.units
        for unit in units_dict.values():
            unit_tile = getattr(unit, "tile", None)
            if unit_tile == coord or (hasattr(unit_tile, "q") and (unit_tile.q, unit_tile.r) == (coord[0], coord[1])):
                return unit
        return None

    # -------------------------------------------------------------------------
    # Section 2: Selected Tile Details (Below Simulation Board)
    # -------------------------------------------------------------------------
    def get_tile_details_panel(self) -> Panel:
        """
        Displays detailed information about the currently selected / cursor tile.
        Pulls comprehensive data from TileData, RegionData, and UnitData.
        """
        q, r, s = self.cursor_coord
        tiles = getattr(self.ui_context, "tiles", {}) or {}
        tile = tiles.get((q, r, s)) or tiles.get((q, r))

        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold white", justify="left")
        table.add_column(style="cyan", justify="left")

        if tile:
            tile_coord = (tile.q, tile.r, getattr(tile, "s", -tile.q - tile.r))
            is_cc = self._is_command_center(tile, tile_coord)
            unit = self._get_unit_on_tile(tile, tile_coord)
            region = self._get_region_for_tile(tile)

            tile_type_str = "[bold gold1]Command Center ★[/bold gold1]" if is_cc else "Standard Hexagon"
            table.add_row("Tile:", f"[white]({tile.q}, {tile.r}, {tile_coord[2]})[/white]  [dim]Type:[/] {tile_type_str}")

            if region:
                reg_id = getattr(region, "region_id", "Unknown")
                reg_owner = getattr(region, "owner", "Neutral")
                owner_label = reg_owner if reg_owner is not None else "Neutral"
                owner_style = "green" if reg_owner is not None else "dim"
                reg_upkeep = getattr(region, "upkeep", 0)
                table.add_row("Region:", f"[bold white]{reg_id}[/]  [dim](Owner:[/] [{owner_style}]{owner_label}[/{owner_style}], [dim]Upkeep:[/] [white]{reg_upkeep}g[/white][dim])[/dim]")
            else:
                table.add_row("Region:", "[dim]None (Unclaimed Territory)[/dim]")

            if unit:
                u_id = getattr(unit, "unit_id", "U-?")
                u_owner = getattr(unit, "owner", "Unknown")
                is_friendly = (u_owner == getattr(self.ui_context, "your_id", ""))
                u_color = "bright_cyan" if is_friendly else "bright_red"
                u_mov = getattr(unit, "movement", "-")
                u_str = getattr(unit, "strength", "-")
                u_upk = getattr(unit, "upkeep", "-")
                table.add_row(
                    "Unit:",
                    f"[bold {u_color}]{u_id}[/bold {u_color}] [dim](Owner:[/] [{ 'green' if is_friendly else 'red' }]{u_owner}[/][dim])[/dim]  "
                    f"Move: [bold]{u_mov}[/] │ Str: [bold]{u_str}[/] │ Upkeep: [white]{u_upk}g[/white]"
                )
            else:
                table.add_row("Unit:", "[dim italic]No unit present on this tile[/dim italic]")
        else:
            table.add_row("Tile:", f"[dim]({q}, {r}, {s})[/dim]  [dim]Type:[/] [dim red]Blocked (No Tile Data)[/dim red]")
            table.add_row("Region:", "[dim]None (Off-map Territory)[/dim]")
            table.add_row("Unit:", "[dim italic]No unit present[/dim italic]")

        is_focused = (self.current_focus == FocusArea.BOARD)
        return Panel(
            table,
            title=f"Selected Tile ({q}, {r}, {s})",
            border_style="yellow" if is_focused else "dim white",
            padding=(0, 1),
            width=55,
            height=7,
        )

    # -------------------------------------------------------------------------
    # Sections 3, 4 & 5: Right Side Panels (Info Panel, Phase, End Button)
    # -------------------------------------------------------------------------
    def get_info_panel(self) -> Panel:
        """Right Side: Information Panel with Tabs and Subpages."""
        is_focused = self.current_focus in (
            FocusArea.PANEL,
            FocusArea.PANEL_STATUS,
            FocusArea.PANEL_EVENTS,
            FocusArea.PANEL_UNITS,
            FocusArea.PANEL_REGIONS,
        )
        is_next = self.next_focus == FocusArea.PANEL
        border_style = "bright_yellow" if is_focused else ("bright_cyan" if is_next else "dim white")

        tabs = ["Status", "Events", "Units", "Regions"]
        tab_headers = []
        for tab in tabs:
            if tab == self.info_panel_page:
                if is_focused:
                    tab_headers.append(f"[bold black on yellow] {tab} [/]")
                else:
                    tab_headers.append(f"[bold white on blue] {tab} [/]")
            else:
                tab_headers.append(f"[dim]{tab}[/]")
        header_text = "│".join(tab_headers)

        # Dispatch to the active subpage
        if self.info_panel_page == "Status":
            content = self.get_status_panel()
        elif self.info_panel_page == "Events":
            content = self.get_events_panel(is_focused=is_focused)
        elif self.info_panel_page == "Units":
            content = self.get_units_panel(is_focused=is_focused)
        elif self.info_panel_page == "Regions":
            content = self.get_regions_panel(is_focused=is_focused)
        else:
            content = self.get_status_panel()

        title = f"Info [{self.info_panel_page}]"
        if is_next and not is_focused:
            title = f"[bold bright_cyan]Next: {title}[/bold bright_cyan]"

        return Panel(
            Group(
                Text.from_markup(header_text),
                Text("─" * 48, style="dim"),
                content
            ),
            title=title,
            border_style=border_style,
            width=52,
            height=14
        )

    def get_sim_phase(self) -> Panel:
        """Bottom Right Left: Simulation Phase Indicator."""
        phase_str = self.ui_context.sim_phase + " Phase"
        round_info = f"Round: {getattr(self.ui_context, 'current_round', 1)}/{getattr(self.ui_context, 'final_round', 10)}"

        content = Text.from_markup(
            f"[dim]{phase_str}[/dim]\n"
            f"[dim]{round_info}[/dim]"
        )
        return Panel(content, title="Phase", border_style="dim white", width=26, height=5)

    def get_action(self) -> Panel:
        """Bottom Right Right: End Turn / Resolution Button."""
        is_focused = self.current_focus == FocusArea.ACTION
        is_next = self.next_focus == FocusArea.ACTION

        border_style = "bright_yellow" if is_focused else ("bright_cyan" if is_next else "dim white")

        title = "Action"
        if is_next and not is_focused:
            title = f"[bold bright_cyan]Next: {title}[/bold bright_cyan]"

        is_focused = (self.current_focus == FocusArea.ACTION)
        btn_style = "bold black on yellow1" if is_focused else "white" #"bold white on dark_green"
        text = Text.from_markup(f"\n      [{btn_style}]End round[/{btn_style}]      \n")
        return Panel(text, title=title, border_style=border_style, width=26, height=5)

    def get_extra_panel(self) -> Optional[Panel]:
        if self.ui_context.sim_phase == "Planning":
            screen: Literal["order", "recruit"] = "order"
        elif self.ui_context.sim_phase == "Upkeep":
            screen = "recruit"
        else:
            return None

        is_order = screen == "order"
        form_focus = FocusArea.PANEL_ORDER if is_order else FocusArea.PANEL_RECRUIT
        is_form_focused = self.current_focus == form_focus
        if not is_form_focused:
            message = "No order" if is_order else "No recruitment"
            return Panel(
                Align(Text(message, style="dim"), vertical="middle"),
                title="Form (Assign Order)" if is_order else "Form (Recruit Unit)",
                border_style="dim white",
                width=52,
                height=9,
            )

        fields = self._visible_order_fields() if is_order else self.recruit_fields
        form = self.order_form if is_order else self.recruit_form
        field_idx = self.order_field_idx if is_order else self.recruit_field_idx
        field_idx = min(field_idx, len(fields) - 1)
        if is_order:
            self.order_field_idx = field_idx
        else:
            self.recruit_field_idx = field_idx

        table = Table.grid(padding=(0, 1))
        table.add_column(width=2)
        table.add_column(style="bold white", width=16)
        table.add_column()
        for index, field in enumerate(fields):
            marker = ">" if index == field_idx else " "
            value = form[field]
            if value is None:
                value = "None"
            table.add_row(marker, field, str(value))

        return Panel(
            Group(
                table,
                Text(self.extra_form_error, style="bold red") if self.extra_form_error else Text(""),
            ),
            title="Form (Assign Order)" if is_order else "From (Recruit Unit)",
            border_style="bright_yellow",
            width=52,
            height=9,
        )

    def _handle_extra_screen_input(self, key: str) -> None:
        normalized = key.lower()
        is_order = self.active_extra_screen == "order"
        fields = self._visible_order_fields() if is_order else self.recruit_fields
        form = self.order_form if self.active_extra_screen == "order" else self.recruit_form
        self.extra_field_idx = min(self.extra_field_idx, len(fields) - 1)
        field = fields[self.extra_field_idx]

        if normalized in ("escape", "esc"):
            self.active_extra_screen = None
            self.ui_context.pop_focus()
        elif normalized in ("up", "arrowup"):
            self.extra_field_idx = (self.extra_field_idx - 1) % len(fields)
        elif normalized in ("down", "arrowdown"):
            self.extra_field_idx = (self.extra_field_idx + 1) % len(fields)
        elif normalized in ("left", "arrowleft", "right", "arrowright"):
            self._change_extra_field(-1 if normalized in ("left", "arrowleft") else 1)
        elif normalized in ("enter", "return"):
            self._save_extra_form()

    def _visible_order_fields(self) -> list[str]:
        fields = ["order_type", "unit_id"]
        if self.order_form["order_type"] in ("attack", "support"):
            fields.append("target_id")
        elif self.order_form["order_type"] == "move":
            fields.extend(("move_q", "move_r", "move_s"))
        return fields

    def _change_extra_field(self, direction: int) -> None:
        is_order = self.active_extra_screen == "order"
        fields = self._visible_order_fields() if is_order else self.recruit_fields
        form = self.order_form if is_order else self.recruit_form
        field = fields[self.extra_field_idx]

        options = {
            "order_type": ("move", "hold", "attack", "support"),
            "unit_type": ("light_infantry", "heavy_infantry", "cavalry"),
        }.get(field)
        if options:
            current_index = options.index(form[field]) if form[field] in options else 0
            form[field] = options[(current_index + direction) % len(options)]
            if field == "order_type":
                if form[field] == "move":
                    form["move_q"], form["move_r"], form["move_s"] = 1, 0, -1
                    self._center_on_move_destination()
                else:
                    form["move_q"] = form["move_r"] = form["move_s"] = None
                form["target_id"] = None
                if form[field] != "move":
                    unit = self.ui_context.units.get(self.order_form["unit_id"])
                    if unit is not None:
                        self.center_map_on(unit.tile)
                self.order_field_idx = min(self.order_field_idx, len(self._visible_order_fields()) - 1)
        elif field == "target_id":
            target_units = sorted(
                unit_id for unit_id in self.ui_context.units
                if unit_id != self.order_form["unit_id"]
            )
            target_options = [None, *target_units]
            current_index = target_options.index(form[field]) if form[field] in target_options else 0
            form[field] = target_options[(current_index + direction) % len(target_options)]
            if form[field] is not None:
                self.center_map_on(self.ui_context.units[form[field]].tile)
            else:
                unit = self.ui_context.units.get(self.order_form["unit_id"])
                if unit is not None:
                    self.center_map_on(unit.tile)
        elif field in ("move_q", "move_r", "move_s"):
            form[field] = (form[field] or 0) + direction
            self._center_on_move_destination()
        self.extra_form_error = None

    def center_map_on(self, coord: tuple[int, int, int]) -> bool:
        if len(coord) != 3 or sum(coord) != 0:
            return False
        if coord not in self.ui_context.tiles and coord[:2] not in self.ui_context.tiles:
            return False
        self.center_tile = coord
        self.cursor_coord = coord
        return True

    def _center_on_move_destination(self) -> None:
        unit = self.ui_context.units.get(self.order_form["unit_id"])
        movement = (self.order_form["move_q"], self.order_form["move_r"], self.order_form["move_s"])
        if unit is None or any(value is None for value in movement) or sum(movement) != 0:
            return
        destination = tuple(origin + offset for origin, offset in zip(unit.tile, movement))
        self.center_map_on(destination)

    def _validate_extra_form(self) -> Optional[str]:
        if self.active_extra_screen == "order":
            if self.ui_context.sim_phase != "Planning":
                return "Orders can only be staged during Planning."
            order_type = self.order_form["order_type"]
            unit_id = self.order_form["unit_id"]
            if not unit_id or unit_id not in self.ui_context.units:
                return "Select a valid unit before staging the order."

            if order_type == "move":
                movement = tuple(self.order_form[field] for field in ("move_q", "move_r", "move_s"))
                if any(value is None for value in movement):
                    return "Move orders require q, r, and s values."
                if any(not isinstance(value, int) or isinstance(value, bool) for value in movement):
                    return "Move coordinates must be integers."
                if sum(movement) != 0:
                    return "Move coordinates must satisfy q + r + s = 0."
            elif order_type in ("attack", "support"):
                target_id = self.order_form["target_id"]
                if not target_id:
                    return f"{order_type.title()} orders require a target unit."
                if target_id not in self.ui_context.units or target_id == unit_id:
                    return "Choose a different unit as the target."
            return None

        if self.ui_context.sim_phase != "Upkeep":
            return "Recruitment can only be staged during Upkeep."
        unit_type = self.recruit_form["unit_type"]
        region_id = self.recruit_form["region"]
        if not unit_type:
            return "Choose a unit type before staging recruitment."
        if not region_id or region_id not in self.ui_context.regions:
            return "Choose a valid region before staging recruitment."
        return None

    def _save_extra_form(self) -> None:
        self.extra_form_error = self._validate_extra_form()
        if self.extra_form_error:
            return

        if self.active_extra_screen == "order" and Order is not None:
            if self.order_form["order_type"] != "move":
                self.order_form["move_q"] = self.order_form["move_r"] = self.order_form["move_s"] = None
            if self.order_form["order_type"] not in ("attack", "support"):
                self.order_form["target_id"] = None
            order = Order(**self.order_form)
            self.ui_context.orders[order.unit_id] = order
        elif self.active_extra_screen == "recruit" and RecruitmentChoice is not None:
            choice = RecruitmentChoice(**self.recruit_form)
            self.ui_context.recruitment[choice.region] = choice
        self.active_extra_screen = None
        self.ui_context.pop_focus()

    # -------------------------------------------------------------------------
    # Info Panel Subpages
    # -------------------------------------------------------------------------
    def get_status_panel(self) -> Group:
        """Subpage 1: Status (Player, Players list, Unit/Region counts, Leaderboard)."""
        your_id = getattr(self.ui_context, "your_id", "You") or "You"
        players = getattr(self.ui_context, "players", [])
        units = getattr(self.ui_context, "units", {}) or {}
        regions = getattr(self.ui_context, "regions", {}) or {}
        leaderboard = getattr(self.ui_context, "leaderboard", {}) or {}

        # Count controlled units & regions
        my_units_count = sum(1 for u in units.values() if getattr(u, "owner", None) == your_id)
        my_regions_count = sum(1 for r in regions.values() if getattr(r, "owner", None) == your_id)

        # Format players list
        players_styled = []
        for p in players:
            if p == your_id:
                players_styled.append(f"[bold green]{p}[/] [dim](You)[/dim]")
            else:
                players_styled.append(f"[bold red]{p}[/]")
        players_line = ", ".join(players_styled) if players_styled else "[dim]None[/dim]"

        lines = [
            Text.from_markup(f"[bold white]Player:[/] [bold green]{your_id}[/]"),
            Text.from_markup(f"[bold white]Supply Balance:[/] [bold cyan]{self.ui_context.supply_balance}[/]"),
            Text.from_markup(f"[bold white]Players:[/] {players_line}"),
            Text.from_markup(
                f"[bold white]Controlled Units:[/] [bold cyan]{my_units_count}[/]  │  "
                f"[bold white]Regions:[/] [bold cyan]{my_regions_count}[/]"
            ),
            Text("─" * 42, style="dim")
        ]

        # Leaderboard table
        if leaderboard:
            lb_header = Text("Leaderboard:", style="bold white")
            lines.append(lb_header)

            lb_table = Table.grid(padding=(0, 2))
            lb_table.add_column(style="dim", justify="right")
            lb_table.add_column(justify="left")
            lb_table.add_column(style="cyan", justify="right")

            sorted_lb = sorted(leaderboard.items(), key=lambda item: item[1], reverse=True)
            for rank, (player, score) in enumerate(sorted_lb, start=1):
                p_text = f"[bold green]{player}[/] (You)" if player == your_id else f"[white]{player}[/]"
                lb_table.add_row(f"#{rank}", p_text, f"{score} pts")

            lines.append(lb_table)
        else:
            lines.append(Text("Leaderboard: [dim]No scores recorded[/dim]"))

        return Group(*lines)

    def get_events_panel(self, is_focused: bool = False) -> Group:
        """Subpage 2: Events (List of events, navigable with cursor)."""
        events = getattr(self.ui_context, "events", []) or []
        if not events:
            return Group(Text("No events recorded.", style="dim italic"))

        # Clamp events cursor
        self.events_cursor = max(0, min(self.events_cursor, len(events) - 1))

        # Show up to 5 events centered around cursor
        max_visible = 5
        start_idx = max(0, min(self.events_cursor - 1, max(0, len(events) - max_visible)))
        end_idx = min(len(events), start_idx + max_visible)

        lines = []
        for i in range(start_idx, end_idx):
            event_text = events[i]
            is_active = (i == self.events_cursor)

            if is_active:
                cursor_mark = "[bold yellow]▶[/] " if is_focused else "[bold cyan]▶[/] "
                line_style = "bold white"
            else:
                cursor_mark = "  "
                line_style = "dim white"

            lines.append(
                Text.from_markup(f"{cursor_mark}[dim]{i + 1}.[/] [{line_style}]{event_text}[/{line_style}]")
            )

        if len(events) > max_visible:
            lines.append(Text(f"[dim]({len(events)} total events)[/dim]"))

        return Group(*lines)

    def get_units_panel(self, is_focused: bool = False) -> RenderableType:
        """Subpage 3: Units (List of units with all relevant details: ID, Owner, Tile, Move, Str, Upkeep)."""
        units = getattr(self.ui_context, "units", {}) or {}
        if not units:
            return Group(Text("No units registered.", style="dim italic"))

        your_id = getattr(self.ui_context, "your_id", "")
        unit_items = list(units.values())
        self.units_cursor = max(0, min(self.units_cursor, len(unit_items) - 1))

        lines = []
        for idx, unit in enumerate(unit_items):
            # Skipping unowned units
            if unit.owner != your_id:
                continue

            is_active = (idx == self.units_cursor)
            cursor_mark = "[bold yellow]▶[/] " if (is_active and is_focused) else ("[cyan]▶[/] " if is_active else "  ")

            u_id = getattr(unit, "unit_id", "U")
            u_owner = getattr(unit, "owner", "-")
            owner_styled = f"[green]{u_owner}[/]" if u_owner == your_id else f"[red]{u_owner}[/]"
            coord = getattr(unit, "tile", (0, 0, 0))
            coord_str = f"({coord[0]},{coord[1]},{coord[2]})" if isinstance(coord, tuple) and len(coord) == 3 else str(coord)
            mov = getattr(unit, "movement", "-")
            strength = getattr(unit, "strength", "-")
            upkeep = getattr(unit, "upkeep", "-")
            order = self.ui_context.orders.get(u_id)
            order_summary = ""
            if order is not None:
                order_details = order.order_type
                if order.order_type == "move":
                    order_details += f" to ({order.move_q}, {order.move_r}, {order.move_s})"
                elif order.target_id:
                    order_details += f" {order.target_id}"
                order_summary = f" [bold yellow]Order: {order_details}[/bold yellow]"

            lines.append(
                Text.from_markup(
                    f"{cursor_mark}[bold cyan]{u_id}[/] [{owner_styled}] "
                    f"[dim]{coord_str}[/] M:{mov} S:{strength} U:{upkeep}{order_summary}"
                )
            )

        return Group(*lines)

    def get_regions_panel(self, is_focused: bool = False) -> RenderableType:
        """Subpage 4: Regions (List of regions with all relevant details: ID, Owner, HQ Tile, Upkeep)."""
        regions = getattr(self.ui_context, "regions", {}) or {}
        if not regions:
            return Group(Text("No regions registered.", style="dim italic"))

        your_id = getattr(self.ui_context, "your_id", "")
        region_items = list(regions.values())
        self.regions_cursor = max(0, min(self.regions_cursor, len(region_items) - 1))

        lines = []
        for idx, region in enumerate(region_items):
            # Skipping unowned regions
            if region.owner != your_id:
                continue

            is_active = (idx == self.regions_cursor)
            cursor_mark = "[bold yellow]▶[/] " if (is_active and is_focused) else ("[cyan]▶[/] " if is_active else "  ")

            reg_id = getattr(region, "region_id", "Region")
            reg_owner = getattr(region, "owner", "-")
            owner_styled = f"[green]{reg_owner}[/]" if reg_owner == your_id else f"[red]{reg_owner}[/]"
            cc = getattr(region, "command_center", (0, 0, 0))
            cc_str = f"({cc[0]},{cc[1]},{cc[2]})" if isinstance(cc, tuple) and len(cc) == 3 else str(cc)
            upkeep = getattr(region, "upkeep", 0)
            recruitment = self.ui_context.recruitment.get(reg_id)
            recruitment_summary = ""
            if recruitment is not None:
                recruitment_summary = (
                    f" [bold yellow]Recruitment: {recruitment.unit_type}[/bold yellow]"
                )

            lines.append(
                Text.from_markup(
                    f"{cursor_mark}[bold white]{reg_id}[/] [{owner_styled}] "
                    f"HQ:[bold gold1]{cc_str}[/] Upkeep:{upkeep}{recruitment_summary}"
                )
            )

        return Group(*lines)

