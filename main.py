from agents.parking_agent import ParkingAgent
import asyncio

agent = ParkingAgent()

async def run_parking_agent():
    res = await agent.ainvoke("Hello")
    print(res)

    while True:
        print("\n-------------------------")
        user_input = input("Chat (q to quit): ").strip()
        if user_input == "q":
            break

        async for content, meta in agent.astream(user_input):
            print(content)


if __name__ == "__main__":
    asyncio.run(run_parking_agent())

