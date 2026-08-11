import asyncio

from src.communication import FrothOPCUAServer


async def main():
    server = FrothOPCUAServer()

    await server.start()

    try:
        print()
        print("Server running.")
        print("Connect UaExpert and press Ctrl+C when finished.")

        while True:
            await server.increment_heartbeat()
            await asyncio.sleep(1)

    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())