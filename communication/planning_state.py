import importlib

from communication.session_state import SessionState

from strAItegize_common.communication.session_phases import SessionPhase
from strAItegize_common.communication.message_model import MessageModel
from strAItegize_common.communication.message_types import MessageType

class PlanningState(SessionState):
    @property
    def session_phase(self) -> SessionPhase:
        return SessionPhase.PlanningPhase

    def handle_await_round_start(self) -> dict:
        while True:
            msg = self.context.get_next_message(timeout=None)
            if msg is None:
                self.context.disconnect_from_server()
                return {}
            if msg.msg_type == MessageType.StartRound:
                return msg.payload
            else:
                print(f"[{self.name}] Unexpected message while waiting for upkeep: {msg.msg_type}")

    def handle_submit_orders(self, orders: list):
        # Sending the orders to the server
        message = MessageModel(
            phase=self.session_phase,
            round_idx=self.context.current_round,
            msg_type=MessageType.IssueOrders,
            payload={
                "orders": orders
            }
        )
        self.context.send_to_server(msg=message)

        # Changing the state
        self.context.transition_to(execution_state.ExecutionState(context=self.context))

execution_state = importlib.import_module("communication.execution_state")