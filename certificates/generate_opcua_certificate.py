import argparse
import ipaddress
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import (
    ExtendedKeyUsageOID,
    NameOID,
)


APPLICATION_URI = "urn:FrothMV:OPCUAServer"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "server_ip",
        help="IP address used by the EAE OPC-UA client",
    )
    args = parser.parse_args()

    output_directory = Path(__file__).resolve().parent
    certificate_path = output_directory / "frothmv_server_cert.pem"
    private_key_path = output_directory / "frothmv_server_key.pem"

    hostname = socket.gethostname()
    server_ip = ipaddress.ip_address(args.server_ip)
    now = datetime.now(timezone.utc)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=3072,
    )

    subject = x509.Name([
        x509.NameAttribute(
            NameOID.COMMON_NAME,
            "FrothMV OPC-UA Server",
        ),
        x509.NameAttribute(
            NameOID.ORGANIZATION_NAME,
            "FrothMV Prototype",
        ),
    ])

    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.UniformResourceIdentifier(APPLICATION_URI),
                x509.DNSName(hostname),
                x509.IPAddress(server_ip),
            ]),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=True,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=None,
                decipher_only=None,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([
                ExtendedKeyUsageOID.SERVER_AUTH,
                ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    certificate_path.write_bytes(
        certificate.public_bytes(serialization.Encoding.PEM)
    )

    print(f"Hostname: {hostname}")
    print(f"Application URI: {APPLICATION_URI}")
    print(f"Server IP: {server_ip}")
    print(f"Certificate: {certificate_path}")
    print(f"Private key: {private_key_path}")


if __name__ == "__main__":
    main()