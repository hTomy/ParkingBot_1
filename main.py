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

    # evidently_api_key = "sk_prod.019c7a6e-883c-7563-9430-8fde96ac008e.iJKzazFHr881m5FBk8bqQRFltnn3G-z4515QrLIyJop0r2WjniPzq1Vu3I22bzWl6IthijNxQ1asn98OooPx-f6_KQkP9_8n_zkMUMZSCd9A3LbIlpAjYl4wyEC26ZRa"