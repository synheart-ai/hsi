from __future__ import annotations

from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

from tests.hsi_validate import StrictValidationError
from tests.hsi_validate import load_json
from tests.hsi_validate import load_schema_basic
from tests.hsi_validate import supported_versions
from tests.hsi_validate import validate_basic
from tests.hsi_validate import validate_strict


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATHS = {
    v: REPO_ROOT / "schema" / f"hsi-{v}.schema.json" for v in supported_versions()
}


@pytest.fixture(scope="session")
def schemas_basic() -> dict[str, dict]:
    return {v: load_schema_basic(p) for v, p in SCHEMA_PATHS.items()}


def _all_json_files_under(dir_path: Path) -> list[Path]:
    if not dir_path.exists():
        return []
    return sorted(p for p in dir_path.rglob("*.json") if p.is_file())


def _valid_fixture_paths() -> list[Path]:
    valid_root = REPO_ROOT / "examples" / "valid"
    vectors = REPO_ROOT / "test-vectors"
    return sorted(_all_json_files_under(valid_root) + _all_json_files_under(vectors))


VALID_FIXTURE_PATHS = _valid_fixture_paths()
INVALID_PATHS = _all_json_files_under(REPO_ROOT / "examples" / "invalid")


def _schema_for(payload: dict, schemas_basic: dict[str, dict]) -> dict:
    version = payload.get("hsi_version")
    if version not in schemas_basic:
        raise AssertionError(
            f"fixture declares unsupported hsi_version '{version}'; "
            f"expected one of {sorted(schemas_basic)}"
        )
    return schemas_basic[version]


@pytest.mark.parametrize("path", VALID_FIXTURE_PATHS, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_valid_fixtures_pass_basic_and_strict(schemas_basic: dict[str, dict], path: Path) -> None:
    payload = load_json(path)
    validate_basic(payload, _schema_for(payload, schemas_basic))
    validate_strict(payload)


@pytest.mark.parametrize("path", INVALID_PATHS, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_invalid_fixtures_fail_basic_or_strict(schemas_basic: dict[str, dict], path: Path) -> None:
    payload = load_json(path)
    schema = _schema_for(payload, schemas_basic)

    basic_ok = True
    strict_ok = True

    try:
        validate_basic(payload, schema)
    except ValidationError:
        basic_ok = False

    try:
        validate_strict(payload)
    except StrictValidationError:
        strict_ok = False

    assert not (basic_ok and strict_ok), "fixture unexpectedly passed both BASIC and STRICT validation"


def test_missing_window_is_strict_failure(schemas_basic: dict[str, dict]) -> None:
    path = REPO_ROOT / "examples" / "invalid" / "missing_window.json"
    payload = load_json(path)

    validate_basic(payload, _schema_for(payload, schemas_basic))

    with pytest.raises(StrictValidationError):
        validate_strict(payload)


def test_dispatcher_rejects_unknown_version() -> None:
    with pytest.raises(StrictValidationError):
        validate_strict({"hsi_version": "99.9"})
