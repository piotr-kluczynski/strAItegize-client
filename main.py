import argparse

from game_controller import GameController

available_scenarios = ["console"]

# Setting up app console line parameters
parser = argparse.ArgumentParser(prog="StrAItegize - Centralized Multi-Agent System")

parser.add_argument("-p", "--port", help="Client port shared by the simulation program to connect to.", type=int, required=True)
parser.add_argument("-u", "--user_interface", help="User interface to use.", choices=available_scenarios, type=str, default=available_scenarios[0], required=False)

def main() -> None:
    args = parser.parse_args()
    print("Welcome to the Client!")
    game_controller = GameController(simulation_port=args.port, user_interface=args.user_interface)

    game_controller.initialize_simulation()
    game_controller.start_simulation()


if __name__ == '__main__':
    main()
