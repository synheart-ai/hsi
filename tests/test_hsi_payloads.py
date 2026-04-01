from __future__ import annotations

from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

from tests.hsi_validate import StrictValidationError
from tests.hsi_validate import load_json
from tests.hsi_validate import load_schema_basic
from tests.hsi_validate import validate_basic
from tests.hsi_validate import validate_strict


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_11_PATH = REPO_ROOT / "schema" / "hsi-1.1.schema.json"
SCHEMA_12_PATH = REPO_ROOT / "schema" / "hsi-1.2.schema.json"
VALID_12_DIR = REPO_ROOT / "examples" / "valid" / "1.2"


@pytest.fixture(scope="session")
def schema_11_basic() -> dict:
    return load_schema_basic(SCHEMA_11_PATH)


@pytest.fixture(scope="session")
def schema_12_basic() -> dict:
    return load_schema_basic(SCHEMA_12_PATH)


def _all_json_files_under(dir_path: Path) -> list[Path]:
    if not dir_path.exists():
        return []
    return sorted(p for p in dir_path.rglob("*.json") if p.is_file())


def _valid_11_paths() -> list[Path]:
    valid_root = REPO_ROOT / "examples" / "valid"
    out: list[Path] = []
    for p in _all_json_files_under(valid_root):
        try:
            p.relative_to(VALID_12_DIR)
        except ValueError:
            out.append(p)
    out.extend(_all_json_files_under(REPO_ROOT / "test-vectors"))
    return sorted(out)


VALID_11_PATHS = _valid_11_paths()
VALID_12_PATHS = _all_json_files_under(VALID_12_DIR)
INVALID_PATHS = _all_json_files_under(REPO_ROOT / "examples" / "invalid")


@pytest.mark.parametrize("path", VALID_11_PATHS, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_valid_11_fixtures_pass_basic_and_strict(schema_11_basic: dict, path: Path) -> None:
    payload = load_json(path)
    validate_basic(payload, schema_11_basic)
    validate_strict(payload)


@pytest.mark.parametrize("path", VALID_12_PATHS, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_valid_12_fixtures_pass_basic_and_strict(schema_12_basic: dict, path: Path) -> None:
    payload = load_json(path)
    validate_basic(payload, schema_12_basic)
    validate_strict(payload)


@pytest.mark.parametrize("path", INVALID_PATHS, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_invalid_fixtures_fail_basic_or_strict(schema_11_basic: dict, path: Path) -> None:
    payload = load_json(path)

    basic_ok = True
    strict_ok = True

    try:
        validate_basic(payload, schema_11_basic)
    except ValidationError:
        basic_ok = False

    try:
        validate_strict(payload)
    except StrictValidationError:
        strict_ok = False

    assert not (basic_ok and strict_ok), "fixture unexpectedly passed both BASIC and STRICT validation"


def test_missing_window_is_strict_failure(schema_11_basic: dict) -> None:
    path = REPO_ROOT / "examples" / "invalid" / "missing_window.json"
    payload = load_json(path)

    validate_basic(payload, schema_11_basic)

    with pytest.raises(StrictValidationError):
        validate_strict(payload)
