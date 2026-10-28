import importlib

from communication.session_state import SessionState

from strAItegize_common.communication.session_phases import SessionPhase
from strAItegize_common.communication.message_model import MessageModel
from strAItegize_common.communication.message_types import MessageType

class UpkeepState(SessionState):
    @property
    def session_phase(self) -> SessionPhase:
        return SessionPhase.UpkeepPhase

    def handle_await_upkeep(self) -> dict:
        while True:
            msg = self.context.get_next_message(timeout=None)
            if msg is None:
                self.context.disconnect_from_server()
                return {}
            if msg.msg_type == MessageType.Upkeep:
                return msg.payload
            else:
                print(f"[{self.name}] Unexpected message while waiting for upkeep: {msg.msg_type}")
    
    def handle_submit_recruitment(self, recruitment: list) -> None:
        # Sending the recruitment choice to the server
        message = MessageModel(
            phase=self.session_phase,
            round_idx=self.context.current_round,
            msg_type=MessageType.RecruitUnits,
            payload={
                "recruitment": recruitment
            }
        )
        
        self.context.send_to_server(msg=message)
        
        # Changing the state
        self.context.transition_to(planning_state.PlanningState(context=self.context))

planning_state = importlib.import_module("communication.planning_state")
