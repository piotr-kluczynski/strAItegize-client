from strAItegize_common.communication.message_types import MessageType

from communication.communication_context import CommunicationContext
from user_interface.user_interface import UserInterface, ui_mapping

class GameController:
    def __init__(self, simulation_port, user_interface: str = "console"):
        interface_factory = ui_mapping.get(user_interface)
        if interface_factory is None:
            raise ValueError(f"Unknown user interface: {user_interface}")

        self.user_interface: UserInterface = interface_factory()
        self.communication: CommunicationContext = CommunicationContext()
        if not self.communication.start_connection(simulation_port=int(simulation_port)):
            raise ConnectionError(f"Could not connect to simulation on port {simulation_port}.")
        self.is_next_round_upkeep: bool = False
        self.player_id: str = ""

    def initialize_simulation(self):
        # Waiting for the simulation to start 
        session_data = self.communication.start_simulation()
        if not session_data or not session_data.get("your_id"):
            raise ConnectionError("Simulation ended before session data was received.")

        # Updating user interface context with the session data
        self.user_interface.ui_context.set_session_data(session_data=session_data)

        # Generating simulation start prompt message
        self.your_id = session_data["your_id"]
        self.player_id = self.your_id

        # Checking if next round is an upkeep one
        self.is_next_round_upkeep = session_data["is_start_upkeep"]

    def _request_data(self, request_type: MessageType, request_args: dict | None = None) -> dict:
        response = self.communication.request_data(request_type=request_type, request_args=request_args)
        if isinstance(response, dict) and response.get("error"):
            message = response.get("desc", "Simulation data request failed.")
            details = response.get("details")
            if details:
                message = f"{message}: {details}"
            raise RuntimeError(message)
        return response.model_dump() if hasattr(response, "model_dump") else response

    def _collect_additional_data(self, sim_phase: str) -> dict:
        context = self.user_interface.ui_context
        additional_data = {"regions": {}, "units": {}, "sim_phase": sim_phase}

        for region_key in context.regions.keys():
            region_id = str(region_key)
            additional_data["regions"][region_id] = self._request_data(
                MessageType.GetRegionDetails,
                {"region_id": region_id},
            )

        unit_list = self._request_data(MessageType.GetUnits).get("units_list", [])
        known_units = {}
        for unit_id in unit_list:
            unit_data = self._request_data(MessageType.GetUnitDetails, {"unit_id": unit_id})
            known_units[unit_id] = unit_data

        visible_unit_ids = {
            unit_id for unit_id, unit_data in known_units.items()
            if unit_data.get("owner") == self.player_id
        }

        for unit_id in tuple(visible_unit_ids):
            observations = self._request_data(
                MessageType.ObserveUnit,
                {"unit_id": unit_id},
            ).get("observations", {})
            visible_unit_ids.update(
                observation["unit"] for observation in observations.values()
                if observation.get("unit") not in (None, "", "Empty")
            )

        for region_id, region_data in additional_data["regions"].items():
            if region_data.get("owner") != self.player_id:
                continue
            observations = self._request_data(
                MessageType.ObserveRegion,
                {"region_id": region_id},
            ).get("observations", {})
            visible_unit_ids.update(
                observation["unit"] for observation in observations.values()
                if observation.get("unit") not in (None, "", "Empty")
            )

        for unit_id in visible_unit_ids:
            if unit_id not in known_units:
                known_units[unit_id] = self._request_data(
                    MessageType.GetUnitDetails,
                    {"unit_id": unit_id},
                )
        additional_data["units"] = known_units
        return additional_data

    def start_simulation(self) -> None:
        requested_tiles = False

        while True:
            if self.is_next_round_upkeep:
                upkeep_data = self.communication.await_upkeep()
                if not upkeep_data:
                    break

                # Requesting additional tiles data if first round
                if not requested_tiles:
                    tile_data = self._request_data(
                        request_type=MessageType.GetTiles,
                        request_args={}
                    )

                    self.user_interface.ui_context.set_tiles_data(tile_data=tile_data["tiles_list"])
                    requested_tiles = True

                additional_data = self._collect_additional_data("Upkeep")
                self.user_interface.ui_context.set_upkeep_data(upkeep_data, additional_data)
                self.user_interface.run()

                recruitment = [
                    choice.model_dump()
                    for choice in self.user_interface.ui_context.recruitment.values()
                ]
                self.communication.submit_recruitment(recruitment=recruitment)

            self.user_interface.ui_context.reset_temp_data()
            round_data = self.communication.await_round_start()
            if not round_data:
                break

            # Requesting additional tiles data if first round
            if not requested_tiles:
                tile_data = self._request_data(
                    request_type=MessageType.GetTiles,
                    request_args={}
                )

                self.user_interface.ui_context.set_tiles_data(tiles_data=tile_data["tiles_list"])
                requested_tiles = True

            additional_data = self._collect_additional_data("Planning")
            self.user_interface.ui_context.set_round_data(round_data, additional_data)
            self.user_interface.run()

            orders = [order.model_dump() for order in self.user_interface.ui_context.orders.values()]
            self.communication.submit_orders(orders=orders)
            self.is_next_round_upkeep = self.communication.end_round()
            if self.is_next_round_upkeep is None:
                break