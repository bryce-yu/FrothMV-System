import os
import logging
from hmac import compare_digest
from pathlib import Path

from asyncua import Server, ua
from asyncua.server.user_managers import UserManager, User, UserRole

# Class added for security
logger = logging.getLogger(__name__)


class FrothMVUserManager(UserManager):
    """Validate the dedicated EAE OPC-UA username and password."""

    def __init__(self, expected_username: str, expected_password: str):
        self.expected_username = expected_username
        self.expected_password = expected_password

    def get_user(
        self,
        iserver,
        username=None,
        password=None,
        certificate=None,
    ):
        if username is None or password is None:
            return None

        username_valid = compare_digest(
            username,
            self.expected_username,
        )
        password_valid = compare_digest(
            password,
            self.expected_password,
        )

        if username_valid and password_valid:
            logger.info(
                "Accepted OPC-UA authentication for user %r",
                username,
            )
            return User(
                role=UserRole.User,
                name=username,
            )

        logger.warning(
            "Rejected OPC-UA authentication attempt for user %r",
            username,
        )
        return None


class FrothOPCUAServer:
    """
    OPC-UA interface for the FrothMV soft-sensor pipeline.

    This class contains communication logic only.
    Machine-vision processing remains inside FrothMVPipeline.
    """

    def __init__(
        self,
        endpoint="opc.tcp://192.168.1.117:4841/froth-test/", # was originaly 0.0.0.0:4841
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

        # self.server = Server() # was just this before adding security

        username = os.environ.get("FROTH_OPCUA_USERNAME")
        password = os.environ.get("FROTH_OPCUA_PASSWORD")

        if not username or not password:
            raise RuntimeError(
                "FROTH_OPCUA_USERNAME and FROTH_OPCUA_PASSWORD "
                "must be configured before starting the OPC-UA server."
            )

        user_manager = FrothMVUserManager(
            expected_username=username,
            expected_password=password,
        )

        self.server = Server(user_manager=user_manager)

        await self.server.init()

        await self.server.set_application_uri(
            "urn:FrothMV:OPCUAServer"
        )

        # Locate the certificate files from the project root.
        project_root = Path(__file__).resolve().parents[2]
        certificate_path = (
            project_root / "certificates" / "frothmv_server_cert.pem"
        )
        private_key_path = (
            project_root / "certificates" / "frothmv_server_key.pem"
        )

        if not certificate_path.is_file():
            raise FileNotFoundError(
                f"OPC-UA server certificate not found: {certificate_path}"
            )

        if not private_key_path.is_file():
            raise FileNotFoundError(
                f"OPC-UA server private key not found: {private_key_path}"
            )

        # Load the server application certificate and private key.
        await self.server.load_certificate(str(certificate_path))
        await self.server.load_private_key(str(private_key_path))

        # Advertise only the encrypted OPC-UA endpoint.
        self.server.set_security_policy([
            ua.SecurityPolicyType.Aes256Sha256RsaPss_SignAndEncrypt,
        ])

        # Disable anonymous sessions and permit username/password only.
        self.server.set_identity_tokens([
            ua.UserNameIdentityToken,
        ])

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

        # *Node ID 5 unused as obsolete CommandFromEAE node and its monitoring from initial testing were removed. 

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

        # ---------------------------------------------------------
        # Added Week 5 MV output features
        # ---------------------------------------------------------

        self.nodes["MedianECD"] = await froth_object.add_variable(
            ua.NodeId(11, ns),
            "MedianECD",
            ua.Variant(0.0, ua.VariantType.Double),
        )

        self.nodes["ECD_P10"] = await froth_object.add_variable(
            ua.NodeId(12, ns),
            "ECD_P10",
            ua.Variant(0.0, ua.VariantType.Double),
        )

        self.nodes["ECD_P90"] = await froth_object.add_variable(
            ua.NodeId(13, ns),
            "ECD_P90",
            ua.Variant(0.0, ua.VariantType.Double),
        )

        # Explicitly ensuring all nodes cannot be written to 
        for node_name, node in self.nodes.items():
            await node.set_read_only()

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

        await self.nodes["MedianECD"].write_value(
            ua.Variant(
                float(metrics.get("median_equivalent_diameter_px", 0.0)),
                ua.VariantType.Double,
            )
        )

        await self.nodes["ECD_P10"].write_value(
            ua.Variant(
                float(metrics.get("ecd_p10_px", 0.0)),
                ua.VariantType.Double,
            )
        )

        await self.nodes["ECD_P90"].write_value(
            ua.Variant(
                float(metrics.get("ecd_p90_px", 0.0)),
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