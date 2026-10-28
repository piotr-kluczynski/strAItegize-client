from communication.session_state import SessionState
from communication.planning_state import PlanningState
from communication.upkeep_state import UpkeepState

from strAItegize_common.communication.message_model import MessageModel
from strAItegize_common.communication.message_types import MessageType
from strAItegize_common.communication.session_phases import SessionPhase

class LobbyState(SessionState):
    @property
    def session_phase(self) -> SessionPhase:
        return SessionPhase.LobbyPhase

    def handle_start_simulation(self):
        # Awaiting for server message containing data about the simulation session
        data_received = False
        session_data_timeout = None

        your_id = None
        players = None
        regions = None
        neighbouring_regions = None
        final_round = None
        is_start_upkeep = None

        while not data_received:
            received_msg = self.context.get_next_message(timeout=session_data_timeout)

            # Server disconnected (detected by message_receiver in communication_context)
            if received_msg is None:
                print(f"[{self.session_phase}] Server disconnected while waiting for the session data.")
                self.context.disconnect_from_server()
                break

            if received_msg.msg_type == MessageType.StartSimulation:
                try:
                    your_id = received_msg.payload["your_id"]
                    players = received_msg.payload["players"]
                    regions = received_msg.payload["regions"]
                    neighbouring_regions = received_msg.payload["neighbouring_regions"]
                    final_round = received_msg.payload["final_round"]
                    is_start_upkeep = received_msg.payload["is_start_upkeep"]

                    data_received = True
                except KeyError as e:
                    print(f"[{self.name}] Received session start message misses data.")
            else:
                print(f"[{self.name}] Incorrect message received from the server.")

        if not data_received:
            return {}

        # Sending the acknowledgment back to the server
        message = MessageModel(
            phase=self.session_phase,
            round_idx=self.context.current_round,
            msg_type=MessageType.Acknowledge,
            payload={}
        )

        self.context.send_to_server(msg=message)

        # Changing the state
        if is_start_upkeep:
            self.context.transition_to(UpkeepState(context=self.context))
        else:
            self.context.transition_to(PlanningState(context=self.context))

        # Returning data drawn from the server
        return {
            "your_id": your_id,
            "is_start_upkeep": is_start_upkeep,
            "players": players,
            "regions": regions,
            "neighbouring_regions": neighbouring_regions,
            "final_round": final_round
        }