import importlib

from communication.session_state import SessionState

from strAItegize_common.communication.session_phases import SessionPhase
from strAItegize_common.communication.message_types import MessageType

class ExecutionState(SessionState):
    @property
    def session_phase(self) -> SessionPhase:
        return SessionPhase.ExecutionPHase

    def handle_end_round(self) -> bool:
        # Awaiting for server message containing data about the round end
        data_received = False        
        is_next_round_upkeep = None
        
        while not data_received:
            received_msg = self.context.get_next_message(timeout=None)
        
            # Server disconnected (detected by message_receiver in communication_context)
            if received_msg is None:
                print(f"[{self.session_phase}] Server disconnected while waiting for the round end data.")
                self.context.disconnect_from_server()
                break
        
            if received_msg.msg_type == MessageType.EndRound:
                try:
                    is_next_round_upkeep = received_msg.payload["is_next_round_upkeep"]
                    data_received = True
                except KeyError as e:
                    print(f"[{self.name}] Received round end message misses data.")
            elif received_msg.msg_type == MessageType.EndSimulation:
                return None
            else:
                print(f"[{self.name}] Incorrect message received from the server.")

        # Changing the state
        if is_next_round_upkeep:
            self.context.transition_to(upkeep_state.UpkeepState(context=self.context))
        else:
            self.context.transition_to(planning_state.PlanningState(context=self.context))

        # Returning whether the next round will contain upkeep phase or not
        return is_next_round_upkeep


upkeep_state = importlib.import_module("communication.upkeep_state")
planning_state = importlib.import_module("communication.planning_state")