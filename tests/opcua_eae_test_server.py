import asyncio
from asyncua import Server, ua


async def main() -> None:
    server = Server()

    await server.init()

    # Use 0.0.0.0 so clients on other machines or runtime environments
    # can reach the server through this computer's network address.
    server.set_endpoint("opc.tcp://0.0.0.0:4841/froth-test/")

    server.set_server_name("FrothMV EAE Test Server")

    namespace_uri = "http://froth.project/test"
    namespace_index = await server.register_namespace(namespace_uri)

    objects = server.nodes.objects
    test_object = await objects.add_object(
        namespace_index,
        "FrothMetrics"
    )

    bubble_count = await test_object.add_variable(
        namespace_index,
        "BubbleCount",
        ua.Variant(0, ua.VariantType.Int32)
    )

    mean_ecd = await test_object.add_variable(
        namespace_index,
        "MeanECD",
        ua.Variant(0.0, ua.VariantType.Double)
    )

    heartbeat = await test_object.add_variable(
        namespace_index,
        "TestHeartbeat",
        ua.Variant(0, ua.VariantType.Int32)
    )

    command_from_eae = await test_object.add_variable(
        namespace_index,
        "CommandFromEAE",
        ua.Variant(False, ua.VariantType.Boolean)
    )

    # Allow OPC UA clients such as EAE to write this variable.
    await command_from_eae.set_writable()

    print("OPC UA test server running")
    print("Local endpoint: opc.tcp://localhost:4841/froth-test/")
    print("Network endpoint: opc.tcp://<PYTHON-PC-IP>:4841/froth-test/")

    counter = 0

    async with server:
        while True:
            counter += 1

            simulated_count = 100 + counter
            simulated_ecd = 12.5 + counter * 0.1

            await bubble_count.write_value(
                ua.Variant(simulated_count, ua.VariantType.Int32)
            )

            await mean_ecd.write_value(
                ua.Variant(simulated_ecd, ua.VariantType.Double)
            )

            await heartbeat.write_value(
                ua.Variant(counter, ua.VariantType.Int32)
            )

            command_value = await command_from_eae.read_value()

            print(
                f"Heartbeat={counter}, "
                f"BubbleCount={simulated_count}, "
                f"MeanECD={simulated_ecd:.2f}, "
                f"CommandFromEAE={command_value}"
            )

            await asyncio.sleep(1.0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped.")