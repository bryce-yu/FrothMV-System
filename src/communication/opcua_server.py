from asyncua import Server, ua


class FrothOPCUAServer:
    """
    OPC-UA interface for the FrothMV soft-sensor pipeline.

    This class contains communication logic only.
    Machine-vision processing remains inside FrothMVPipeline.
    """

    def __init__(
        self,
        endpoint="opc.tcp://0.0.0.0:4841/froth-test/",
        namespace_uri="http://froth.project/test",
    ):
        self.endpoint = endpoint
        self.namespace_uri = namespace_uri

        self.server = None
        self.namespace_index = None
        self.nodes = {}

        self.heartbeat = 0

    async def start(self):
        """Initialise and start the OPC-UA server."""

        self.server = Server()

        await self.server.init()

        self.server.set_endpoint(self.endpoint)
        self.server.set_server_name("FrothMV OPC-UA Server")

        self.namespace_index = await self.server.register_namespace(
            self.namespace_uri
        )

        print(
            f"Registered namespace '{self.namespace_uri}' "
            f"as ns={self.namespace_index}"
        )

        # The current EAE configuration expects ns=2.
        if self.namespace_index != 2:
            print(
                "WARNING: Namespace index is not 2. "
                "EAE NodeIds may need updating."
            )

        ns = self.namespace_index

        # Main FrothMetrics object.
        froth_object = await self.server.nodes.objects.add_object(
            ua.NodeId(1, ns),
            "FrothMetrics",
        )

        # ---------------------------------------------------------
        # Core soft-sensor outputs
        # ---------------------------------------------------------

        self.nodes["BubbleCount"] = await froth_object.add_variable(
            ua.NodeId(2, ns),
            "BubbleCount",
            ua.Variant(0, ua.VariantType.Int32),
        )

        self.nodes["MeanECD"] = await froth_object.add_variable(
            ua.NodeId(3, ns),
            "MeanECD",
            ua.Variant(0.0, ua.VariantType.Double),
        )

        # ---------------------------------------------------------
        # Existing Week 3 diagnostic nodes
        # ---------------------------------------------------------

        self.nodes["TestHeartbeat"] = await froth_object.add_variable(
            ua.NodeId(4, ns),
            "TestHeartbeat",
            ua.Variant(0, ua.VariantType.Int32),
        )

        self.nodes["CommandFromEAE"] = await froth_object.add_variable(
            ua.NodeId(5, ns),
            "CommandFromEAE",
            ua.Variant(False, ua.VariantType.Boolean),
        )

        # This is the one node EAE / UaExpert can write.
        await self.nodes["CommandFromEAE"].set_writable()

        # ---------------------------------------------------------
        # Remaining MV outputs / diagnostics
        # ---------------------------------------------------------

        self.nodes["MeanArea"] = await froth_object.add_variable(
            ua.NodeId(6, ns),
            "MeanArea",
            ua.Variant(0.0, ua.VariantType.Double),
        )

        self.nodes["MeanCircularity"] = await froth_object.add_variable(
            ua.NodeId(7, ns),
            "MeanCircularity",
            ua.Variant(0.0, ua.VariantType.Double),
        )

        self.nodes["ProcessingTime"] = await froth_object.add_variable(
            ua.NodeId(8, ns),
            "ProcessingTime",
            ua.Variant(0.0, ua.VariantType.Double),
        )

        self.nodes["PipelineOK"] = await froth_object.add_variable(
            ua.NodeId(9, ns),
            "PipelineOK",
            ua.Variant(False, ua.VariantType.Boolean),
        )

        self.nodes["PipelineStatus"] = await froth_object.add_variable(
            ua.NodeId(10, ns),
            "PipelineStatus",
            ua.Variant("STARTING", ua.VariantType.String),
        )

        await self.server.start()

        print()
        print("FrothMV OPC-UA server started.")
        print(f"Endpoint: {self.endpoint}")
        print(f"Namespace index: {self.namespace_index}")

    async def stop(self):
        """Stop the OPC-UA server cleanly."""

        if self.server is not None:
            await self.server.stop()
            print("OPC-UA server stopped.")

    async def update_metrics(self, metrics):
        """
        Publish one FrothMVPipeline result dictionary to OPC-UA.
        """

        await self.nodes["BubbleCount"].write_value(
            ua.Variant(
                int(metrics.get("bubble_count", 0)),
                ua.VariantType.Int32,
            )
        )

        await self.nodes["MeanECD"].write_value(
            ua.Variant(
                float(metrics.get("mean_equivalent_diameter_px", 0.0)),
                ua.VariantType.Double,
            )
        )

        await self.nodes["MeanArea"].write_value(
            ua.Variant(
                float(metrics.get("mean_area_px2", 0.0)),
                ua.VariantType.Double,
            )
        )

        await self.nodes["MeanCircularity"].write_value(
            ua.Variant(
                float(metrics.get("mean_circularity", 0.0)),
                ua.VariantType.Double,
            )
        )

        await self.nodes["ProcessingTime"].write_value(
            ua.Variant(
                float(metrics.get("processing_time_seconds", 0.0)),
                ua.VariantType.Double,
            )
        )

        status = str(metrics.get("status", "UNKNOWN"))

        # A successfully processed image with zero detections is still
        # considered a functioning pipeline.
        pipeline_ok = status in {"OK", "NO_DETECTIONS"}

        await self.nodes["PipelineOK"].write_value(
            ua.Variant(
                pipeline_ok,
                ua.VariantType.Boolean,
            )
        )

        await self.nodes["PipelineStatus"].write_value(
            ua.Variant(
                status,
                ua.VariantType.String,
            )
        )

    async def increment_heartbeat(self):
        """Increment the communication heartbeat."""

        self.heartbeat += 1

        await self.nodes["TestHeartbeat"].write_value(
            ua.Variant(
                self.heartbeat,
                ua.VariantType.Int32,
            )
        )

    async def read_command(self):
        """Read the writable command node."""

        return bool(
            await self.nodes["CommandFromEAE"].read_value()
        )

    async def update_pipeline_failure(self, status_message):
        """
        Publish a pipeline failure state without overwriting
        the last valid MV measurements.
        """

        await self.nodes["PipelineOK"].write_value(
            ua.Variant(
                False,
                ua.VariantType.Boolean,
            )
        )

        await self.nodes["PipelineStatus"].write_value(
            ua.Variant(
                str(status_message),
                ua.VariantType.String,
            )
        )