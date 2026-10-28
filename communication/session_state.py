from abc import ABC

from typing import Optional

from strAItegize_common.communication.message_model import MessageModel
from strAItegize_common.communication.message_types import MessageType
from strAItegize_common.communication.session_phases import SessionPhase

class SessionState(ABC):
    def __init__(self, context):
        self.context = context
    
    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def session_phase(self) -> SessionPhase:
        return self.__class__.__session_phase__

    # Actions called from the simulation
    def handle_start_simulation(self) -> dict:
        raise Exception(f"Cannot start simulation while in phase: {self.name}")

    def handle_end_simulation(self):
        raise Exception(f"Cannot end simulation while in phase: {self.name}")      

    def handle_await_round_start(self) -> dict:
        raise Exception(f"Cannot wait for round start while in phase: {self.name}")  

    def handle_submit_orders(self, orders: list):
        raise Exception(f"Cannot submit orders while in phase: {self.name}")  

    def handle_end_round(self) -> bool:
        raise Exception(f"Cannot end round while in phase: {self.name}")

    def handle_await_upkeep(self) -> dict:
        raise Exception(f"Cannot wait for upkeep start while in phase: {self.name}")  

    def handle_submit_recruitment(self, recruitment: list):
        raise Exception(f"Cannot submit recruitment while in phase: {self.name}")  

    # Actions called from the network
    def handle_message(self, msg: MessageModel) -> Optional[MessageModel]:
        msg = MessageModel.model_validate(msg)

        if msg.msg_type == MessageType.StateUpdate:
            self.context.handle_state_update(msg.payload["expected_phase"])
            return None
        else:
            return msg