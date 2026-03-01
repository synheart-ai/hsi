from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator
from jsonschema import FormatChecker


def _parse_rfc3339(dt_str: str) -> datetime:
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"
    return datetime.fromisoformat(dt_str)


def _iter_axis_readings(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Iterate all axis readings across all domains.

    In the revised 1.1 schema, each domain is a plain array of axis_reading
    objects (no intermediate ``readings`` wrapper).
    """
    axes = payload.get("axes")
    if not isinstance(axes, dict):
        return []

    readings: list[dict[str, Any]] = []
    for domain_arr in axes.values():
        if not isinstance(domain_arr, list):
            continue
        for r in domain_arr:
            if isinstance(r, dict):
                readings.append(r)
    return readings


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_schema_basic(schema_path: Path) -> dict[str, Any]:
    """
    Loads the canonical schema but strips AJV-only `$data` constraints so that
    standard Draft 2020-12 validators can evaluate it (HSI-VALIDATE-BASIC).
    """
    schema = load_json(schema_path)

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            if "enum" in node and isinstance(node["enum"], dict) and "$data" in node["enum"]:
                node = dict(node)
                node.pop("enum", None)
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(copy.deepcopy(schema))


@dataclass(frozen=True)
class StrictValidationError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def validate_basic(payload: Any, schema_basic: dict[str, Any]) -> None:
    Draft202012Validator(schema_basic, format_checker=FormatChecker()).validate(payload)


def validate_strict(payload: dict[str, Any]) -> None:
    """
    HSI-VALIDATE-STRICT checks that cannot be fully expressed in pure JSON Schema:
    - windows keys <-> window_ids integrity
    - computed_at_utc >= observed_at_utc
    - window.end_utc >= window.start_utc (for each declared window)
    - axis_reading.window_ids entries reference declared window ids
    - embedding.window_ids entries reference declared window ids
    - embedding.dims equals len(vector) when vector is present
    - null value readings require a non-empty top-level meta
    """
    if not isinstance(payload, dict):
        raise StrictValidationError("payload must be an object for strict validation")

    window_ids = payload.get("window_ids")
    windows = payload.get("windows")
    if not isinstance(window_ids, list) or not isinstance(windows, dict):
        raise StrictValidationError("window_ids and windows must be present for strict validation")

    window_id_set = set(window_ids)
    windows_key_set = set(windows.keys())
    if window_id_set != windows_key_set:
        missing = sorted(window_id_set - windows_key_set)
        extra = sorted(windows_key_set - window_id_set)
        raise StrictValidationError(
            "windows/window_ids mismatch"
            + (f"; missing windows: {missing}" if missing else "")
            + (f"; extra windows: {extra}" if extra else "")
        )

    # time ordering: computed_at_utc >= observed_at_utc
    try:
        observed = _parse_rfc3339(payload["observed_at_utc"])
        computed = _parse_rfc3339(payload["computed_at_utc"])
    except Exception as e:  # noqa: BLE001
        raise StrictValidationError(f"invalid observed_at_utc/computed_at_utc: {e}") from e
    if computed < observed:
        raise StrictValidationError("computed_at_utc must be >= observed_at_utc")

    # window ordering: end_utc >= start_utc
    for wid, w in windows.items():
        if not isinstance(w, dict):
            raise StrictValidationError(f"window '{wid}' must be an object")
        try:
            start = _parse_rfc3339(w["start_utc"])
            end = _parse_rfc3339(w["end_utc"])
        except Exception as e:  # noqa: BLE001
            raise StrictValidationError(f"invalid window timestamps for '{wid}': {e}") from e
        if end < start:
            raise StrictValidationError(f"window '{wid}' end_utc must be >= start_utc")

    # axis readings reference checks
    for r in _iter_axis_readings(payload):
        if r.get("value") is None:
            meta = payload.get("meta")
            if not isinstance(meta, dict) or not meta:
                raise StrictValidationError(
                    "axis reading with null value requires a non-empty top-level meta explanation"
                )

        r_window_ids = r.get("window_ids")
        if isinstance(r_window_ids, list):
            for wid in r_window_ids:
                if wid not in window_id_set:
                    raise StrictValidationError(f"axis reading references unknown window_id '{wid}'")

    # embeddings reference + dims checks
    embeddings = payload.get("embeddings")
    if embeddings is not None:
        if not isinstance(embeddings, list):
            raise StrictValidationError("embeddings must be an array")
        for i, emb in enumerate(embeddings):
            if not isinstance(emb, dict):
                raise StrictValidationError(f"embeddings[{i}] must be an object")
            emb_window_ids = emb.get("window_ids")
            if isinstance(emb_window_ids, list):
                for ewid in emb_window_ids:
                    if ewid not in window_id_set:
                        raise StrictValidationError(f"embedding references unknown window_id '{ewid}'")
            vec = emb.get("vector")
            dims = emb.get("dims")
            if vec is not None:
                if not isinstance(vec, list):
                    raise StrictValidationError("embedding.vector must be an array when present")
                if isinstance(dims, int) and dims != len(vec):
                    raise StrictValidationError("embedding.dims must equal len(embedding.vector)")
