import hashlib

import pytest

from src.mv.model_integrity import (
    ModelIntegrityError,
    calculate_sha256,
    verify_model_integrity,
)


def test_sha256_calculation(tmp_path):
    model_file = tmp_path / "model.pt"
    model_file.write_bytes(b"known model content")

    expected = hashlib.sha256(b"known model content").hexdigest()

    assert calculate_sha256(model_file) == expected


def test_model_integrity_match(tmp_path):
    model_file = tmp_path / "model.pt"
    hash_file = tmp_path / "model.pt.sha256"

    model_file.write_bytes(b"trusted model")
    expected = hashlib.sha256(b"trusted model").hexdigest()
    hash_file.write_text(expected, encoding="utf-8")

    actual = verify_model_integrity(model_file, hash_file)

    assert actual == expected


def test_model_integrity_mismatch(tmp_path):
    model_file = tmp_path / "model.pt"
    hash_file = tmp_path / "model.pt.sha256"

    model_file.write_bytes(b"modified model")
    trusted_hash = hashlib.sha256(b"original model").hexdigest()
    hash_file.write_text(trusted_hash, encoding="utf-8")

    with pytest.raises(ModelIntegrityError, match="mismatch"):
        verify_model_integrity(model_file, hash_file)


def test_missing_model_is_rejected(tmp_path):
    hash_file = tmp_path / "model.pt.sha256"
    hash_file.write_text("0" * 64, encoding="utf-8")

    with pytest.raises(ModelIntegrityError, match="does not exist"):
        verify_model_integrity(
            tmp_path / "missing.pt",
            hash_file,
        )