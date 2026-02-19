from agents.parking_agent import ParkingAgent

agent = ParkingAgent()

def run_parking_agent():
    for msg in agent.invoke("Hello"):
        print(msg, end="")

    while True:
        print("\n-------------------------")
        user_input = input("Chat (q to quit): ").strip()
        if user_input == "q":
            break
        for msg in agent.invoke(user_input):
            print(msg, end="")

if __name__ == "__main__":
    run_parking_agent()