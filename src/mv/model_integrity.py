import hashlib
import hmac
import re
from pathlib import Path


class ModelIntegrityError(RuntimeError):
    """Raised when model integrity verification fails."""


def calculate_sha256(file_path: Path) -> str:
    file_path = Path(file_path)

    if not file_path.is_file():
        raise ModelIntegrityError(
            f"Model file does not exist: {file_path}"
        )

    with file_path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def load_expected_sha256(hash_path: Path) -> str:
    hash_path = Path(hash_path)

    if not hash_path.is_file():
        raise ModelIntegrityError(
            f"Trusted hash file does not exist: {hash_path}"
        )

    expected_hash = hash_path.read_text(encoding="utf-8").strip().lower()

    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise ModelIntegrityError(
            f"Trusted SHA-256 value is invalid: {hash_path}"
        )

    return expected_hash


def verify_model_integrity(
    model_path: Path,
    hash_path: Path,
) -> str:
    expected_hash = load_expected_sha256(hash_path)
    actual_hash = calculate_sha256(model_path)

    if not hmac.compare_digest(actual_hash, expected_hash):
        raise ModelIntegrityError(
            "Model SHA-256 mismatch: model may be modified or corrupted"
        )

    return actual_hash