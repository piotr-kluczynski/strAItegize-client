from __future__ import annotations

from typing import TYPE_CHECKING

from ..unit_data import UnitData
from ..region_data import RegionData
from ..tile_data import TileData

if TYPE_CHECKING:
    from ..user_interface import UserInterface
    from .navigation_node import NavigationNode

from strAItegize_common.others.order import Order
from strAItegize_common.others.recruitment_choice import RecruitmentChoice

class ConsoleUIContext():
    # Containing simulation information to display, communicating with the the server if needed
    def __init__(self, user_interface: UserInterface):
        self.user_interface = user_interface

        self.your_id: str = ""
        self.final_round: int = 0
        self.upkeep_phase: int = 0

        self.players: list[str] = []
        self.leaderboard: dict[str, int] = {}
        self.current_round: int = 0
        self.supply_balance: int = 0

        self.events: list[str] = []
        self.units: dict[str, UnitData] = {}
        self.regions: dict[str, RegionData] = {}
        self.tiles: dict[(int, int, int), TileData] = {}

        self.orders: dict[str, Order] = {}
        self.recruitment: dict[str, RecruitmentChoice] = {}

        self.sim_phase: str = ""

    def reset_temp_data(self):
        # Clearing tiles from units
        for tile in self.tiles.values():
            tile.unit = None

        self.events = []
        self.units = {}
        self.regions = {region_id: None for region_id in self.regions}
        self.leaderboard = {}
        self.supply_balance = 0
        self.current_round = 0
        self.sim_phase = ""
        self.orders = {}
        self.recruitment = {}

    def set_tiles_data(self, tiles_data: dict):
        for tile_coord, tile in tiles_data.items():
            coords = self._parse_coord(tile_coord)

            self.tiles[coords] = TileData(
                q=coords[0],
                r=coords[1],
                s=coords[2],
                unit=tile["unit"],
                region=tile["region"]
            )

    def set_session_data(self, session_data: dict):
        # Setting up all the data from the simulation start message
        self.your_id = session_data["your_id"]
        self.players = session_data["players"]
        self.final_round = session_data["final_round"]

        # Setting up information about region ids to draw more data after session starts
        for region_id in session_data["regions"]:
            self.regions[region_id] = None

    def set_upkeep_data(self, upkeep_data: dict, additional_data: dict):
        # Setting up all the data from the upkeep message
        self.supply_balance = upkeep_data["supply_surplus"]

        # Setting up all the data from additional requests
        for region_data in self._iter_records(additional_data["regions"]):
            coords = self._parse_coord(region_data["command_center_coord"])

            self.regions[region_data["region_id"]] = RegionData(
                region_id=region_data["region_id"],
                owner=region_data["owner"],
                command_center=coords,
                upkeep=region_data.get("region_upkeep", region_data.get("upkeep", 0)),
            )

        for unit_data in self._iter_records(additional_data["units"]):
            coords = self._parse_coord(unit_data["coord"])

            self.units[unit_data["unit_id"]] = UnitData(
                unit_id=unit_data["unit_id"],
                owner=unit_data["owner"],
                tile=coords,
                movement=unit_data["movement"],
                upkeep=unit_data["upkeep"],
                strength=unit_data["strength"]
            )

        self.sim_phase = additional_data["sim_phase"]

        # Calculating unit placement
        for unit_data in self.units.values():
            tile = self.tiles.get(unit_data.tile)
            if tile is not None:
                tile.unit = unit_data.unit_id

    def set_round_data(self, round_data: dict, additional_data: dict):
        # Setting up all the data from the round start message
        self.current_round = round_data["current_round"]
        self.final_round = round_data["final_round"]
        self.players = round_data["players"]
        self.leaderboard = round_data["leaderboard"]
        self.events = round_data["events"]

        # Setting up all the data from additional requests
        for region_data in self._iter_records(additional_data["regions"]):
            coords = self._parse_coord(region_data["command_center_coord"])

            self.regions[region_data["region_id"]] = RegionData(
                region_id=region_data["region_id"],
                owner=region_data["owner"],
                command_center=coords,
                upkeep=region_data.get("region_upkeep", region_data.get("upkeep", 0)),
            )

        for unit_data in self._iter_records(additional_data["units"]):
            coords = self._parse_coord(unit_data["coord"])

            self.units[unit_data["unit_id"]] = UnitData(
                unit_id=unit_data["unit_id"],
                owner=unit_data["owner"],
                tile=coords,
                movement=unit_data["movement"],
                upkeep=unit_data["upkeep"],
                strength=unit_data["strength"]
            )

        self.sim_phase = additional_data["sim_phase"]

        # Calculating unit placement
        for unit in self.units.values():
            tile = self.tiles.get(unit.tile)
            if tile is not None:
                tile.unit = unit.unit_id

        # Calculating supply balance
        for region in self.regions.values():
            if region.owner == self.your_id:
                self.supply_balance += region.upkeep

        for unit in self.units.values():
            if unit.owner == self.your_id:
                self.supply_balance -= unit.upkeep

    @staticmethod
    def _iter_records(records):
        values = records.values() if isinstance(records, dict) else records
        for record in values:
            yield record.model_dump() if hasattr(record, "model_dump") else record

    @staticmethod
    def _parse_coord(coord) -> tuple[int, int, int]:
        parts = coord.split(",") if isinstance(coord, str) else coord
        parsed = tuple(int(part) for part in parts)
        if len(parsed) != 3 or sum(parsed) != 0:
            raise ValueError(f"Invalid cube coordinate: {coord!r}")
        return parsed

    def add_focus(self, node: NavigationNode) -> None:
        self.user_interface.focus_stack.append(node)

    def pop_focus(self) -> None:
        if len(self.user_interface.focus_stack) > 1:
            self.user_interface.focus_stack.pop()

    def change_center_tile(self, q: int, r: int, s: int) -> None:
        new_center_tile = (q, r, s)
        if new_center_tile in self.tiles:
            self.user_interface.center_tile = new_center_tile
            self.user_interface.cursor_coord = new_center_tile

    def reload_view(self):
        self.user_interface.render()

    def perform_action(self):
        self.exit_simulation()     

    def exit_simulation(self):
        self.user_interface.running = False