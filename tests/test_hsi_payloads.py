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
SCHEMA_PATH = REPO_ROOT / "schema" / "hsi-1.0.schema.json"


@pytest.fixture(scope="session")
def schema_basic() -> dict:
    return load_schema_basic(SCHEMA_PATH)


def _all_json_files_under(dir_path: Path) -> list[Path]:
    if not dir_path.exists():
        return []
    return sorted(p for p in dir_path.rglob("*.json") if p.is_file())


VALID_PATHS = (
    _all_json_files_under(REPO_ROOT / "examples" / "valid")
    + _all_json_files_under(REPO_ROOT / "test-vectors")
)
INVALID_PATHS = _all_json_files_under(REPO_ROOT / "examples" / "invalid")


@pytest.mark.parametrize("path", VALID_PATHS, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_valid_fixtures_pass_basic_and_strict(schema_basic: dict, path: Path) -> None:
    payload = load_json(path)
    validate_basic(payload, schema_basic)
    validate_strict(payload)


@pytest.mark.parametrize("path", INVALID_PATHS, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_invalid_fixtures_fail_basic_or_strict(schema_basic: dict, path: Path) -> None:
    payload = load_json(path)

    basic_ok = True
    strict_ok = True

    try:
        validate_basic(payload, schema_basic)
    except ValidationError:
        basic_ok = False

    try:
        validate_strict(payload)
    except StrictValidationError:
        strict_ok = False

    # Invalid fixtures must fail at least one layer.
    assert not (basic_ok and strict_ok), "fixture unexpectedly passed both BASIC and STRICT validation"


def test_missing_window_is_strict_failure(schema_basic: dict) -> None:
    """
    This repo includes an example that is structurally schema-valid but fails reference integrity:
    axis_reading.window_id references a missing window.
    """
    path = REPO_ROOT / "examples" / "invalid" / "missing_window.json"
    payload = load_json(path)

    # BASIC schema validation should pass (AJV `$data` constraints are stripped in BASIC mode).
    validate_basic(payload, schema_basic)

    with pytest.raises(StrictValidationError):
        validate_strict(payload)


