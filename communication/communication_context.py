import socket
import threading
import queue

from communication.session_state import SessionState
from communication.lobby_state import LobbyState
from communication.planning_state import PlanningState
from communication.upkeep_state import UpkeepState
from communication.execution_state import ExecutionState

from strAItegize_common.communication.models import GetTilesRequest, GetTilesResponse
from strAItegize_common.communication.models import ObserveUnitRequest, ObserveUnitResponse
from strAItegize_common.communication.models import ObserveRegionRequest, ObserveRegionResponse
from strAItegize_common.communication.models import GetUnitsRequest, GetUnitsResponse
from strAItegize_common.communication.models import GetRegionsRequest, GetRegionsResponse
from strAItegize_common.communication.models import GetUnitDetailsRequest, GetUnitDetailsResponse
from strAItegize_common.communication.models import GetRegionDetailsRequest, GetRegionDetailsResponse
from strAItegize_common.communication.models import GetPlayersRequest, GetPlayersResponse

from strAItegize_common.communication.transport import send_message, receive_message
from strAItegize_common.communication.message_model import MessageModel
from strAItegize_common.communication.message_types import MessageType
from strAItegize_common.communication.session_phases import SessionPhase

REQUEST_RESPONSE_MODELS = {
    MessageType.ObserveUnit: (ObserveUnitRequest, ObserveUnitResponse),
    MessageType.ObserveRegion: (ObserveRegionRequest, ObserveRegionResponse),
    MessageType.GetUnits: (GetUnitsRequest, GetUnitsResponse),
    MessageType.GetRegions: (GetRegionsRequest, GetRegionsResponse),
    MessageType.GetUnitDetails: (GetUnitDetailsRequest, GetUnitDetailsResponse),
    MessageType.GetRegionDetails: (GetRegionDetailsRequest, GetRegionDetailsResponse),
    MessageType.GetPlayers: (GetPlayersRequest, GetPlayersResponse),
    MessageType.GetTiles: (GetTilesRequest, GetTilesResponse)
}

class CommunicationContext:
    def __init__(self):
        self.current_round = 0
        self.simulation_port = None
        
        self.simulation_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        self.state: SessionState = LobbyState(context=self)
        self.inbox = queue.Queue()

    # Methods for the states
    def transition_to(self, new_state: SessionState):
        print(f"[PHASE] Transition: {self.state.name} -> {new_state.name}")
        self.state = new_state

    def send_to_server(self, msg: MessageModel):
        send_message(self.simulation_socket, msg.model_dump())

    def disconnect_from_server(self):
        if self.simulation_socket:
            try:
                self.simulation_socket.close()
            except Exception:
                pass
        self.simulation_socket = None

        print(f"[COMM] Disconnected from the simulation.")

    def handle_state_update(self, expected_phase: SessionPhase):
        if expected_phase == SessionPhase.LobbyPhase:
            self.state = LobbyState(context=self)
            self.state.handle_start_simulation()

        elif expected_phase == SessionPhase.PlanningPhase:
            self.state = PlanningState(context=self)
            self.state.handle_await_round_start()

        elif expected_phase == SessionPhase.UpkeepPhase:
            self.state = UpkeepState(context=self)
            self.state.handle_await_upkeep()

        elif expected_phase == SessionPhase.ExecutionPHase:
            self.state = ExecutionState(context=self)
            self.state.handle_end_round()

    # Inbox Access and Management
    def start_listening(self):
        threading.Thread(
            target=self.message_receiver,
            args=(),
            daemon=True
        ).start()

    def message_receiver(self):
        while True:
            try:
                raw_msg = receive_message(self.simulation_socket)
                if raw_msg is None:
                    break


                self.inbox.put(raw_msg)
            except (ConnectionError, ConnectionResetError, socket.error):
                print(f"[COMM] Connection lost with server.")
                break
            except Exception as e:
                print(f"[COMM] Listener error: {e}.")
                break

        try:
            self.simulation_socket.close()
        except Exception:
            pass
        self.simulation_socket = None

        self.inbox.put(None)

    def get_next_message(self, timeout: float = None) -> dict:
        while True:
            try:
                raw_message = self.inbox.get(timeout=timeout)
            except queue.Empty:
                return None

            if raw_message is None:
                return None

            message = self.state.handle_message(raw_message)
            if message is None:
                continue

            self.current_round = message.round_idx
            return message

    # High-level functions for other classes
    def start_connection(self, simulation_port: int) -> bool:
        self.simulation_port = simulation_port

        try:
            self.simulation_socket.connect(("127.0.0.1", simulation_port))
            print("[COMM] Connected to the simulation app.")

            # Once connected, activate the receiver
            self.start_listening()
            return True
        except socket.error as e:
            print(f"[COMM] Connection failed: {e}")
            return False

    def request_data(
            self, 
            request_type=MessageType, 
            request_args=None
        ):
    
        if request_type not in REQUEST_RESPONSE_MODELS:
            return {
                "error": True,
                "desc": f"Request type {request_type} is not supported.",
                "details": ""
            }

        # Selecting the request, response model based on the request_type
        request_model, response_model = REQUEST_RESPONSE_MODELS[request_type]

        # Creating the message
        message = MessageModel(
            phase=self.state.session_phase,
            round_idx=self.current_round,
            msg_type=request_type,
            payload={}
        )

        # Adding arguments to the payload
        if request_args is not None:
            request_data = request_model(**request_args)
            message.payload = request_data.model_dump()
    
        # Sending a request
        self.send_to_server(msg=message)
    
        # Receiving and parsing the response
        response_timeout = 60.0

        response = self.get_next_message(timeout=response_timeout)
    
        if not response:
            return {
                "error": True,
                "desc": f"Communication error has occurred - data could not be retrieved from the server.",
                "details": ""
            }

        if response.error or response.msg_type == MessageType.Error:
            return {
                "error": True,
                "desc": response.error or response.payload.get("desc", "Server returned an error response."),
                "details": response.payload.get("details", ""),
            }
    
        return response_model.model_validate(response.payload)

    def start_simulation(self) -> dict:
        return self.state.handle_start_simulation()

    def end_simulation(self):
        self.state.handle_end_simulation()

    def await_round_start(self):
        return self.state.handle_await_round_start()

    def submit_orders(self, orders: list) -> bool:
        return self.state.handle_submit_orders(orders=orders)

    def await_upkeep(self) -> dict:
        return self.state.handle_await_upkeep()

    def submit_recruitment(self, recruitment: list):
        self.state.handle_submit_recruitment(recruitment=recruitment)

    def end_round(self) -> bool:
        return self.state.handle_end_round()
