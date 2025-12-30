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
    # Python's fromisoformat understands offsets like +00:00, but not trailing 'Z'.
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"
    return datetime.fromisoformat(dt_str)


def _iter_axis_readings(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    axes = payload.get("axes")
    if not isinstance(axes, dict):
        return []

    readings: list[dict[str, Any]] = []
    for domain_obj in axes.values():
        if not isinstance(domain_obj, dict):
            continue
        domain_readings = domain_obj.get("readings")
        if not isinstance(domain_readings, list):
            continue
        for r in domain_readings:
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
            # AJV extension: enum: { "$data": "/window_ids" }
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
    - sources keys <-> source_ids integrity
    - computed_at_utc >= observed_at_utc
    - window.end >= window.start (for each declared window)
    - axis_reading.window_id references a declared window id
    - embedding.window_id references a declared window id
    - evidence_source_ids references declared sources (and requires sources to exist)
    - embedding.dimension equals len(vector) when vector is present
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
    except Exception as e:  # noqa: BLE001 - surfaced as strict error
        raise StrictValidationError(f"invalid observed_at_utc/computed_at_utc: {e}") from e
    if computed < observed:
        raise StrictValidationError("computed_at_utc must be >= observed_at_utc")

    # window ordering: end >= start
    for wid, w in windows.items():
        if not isinstance(w, dict):
            raise StrictValidationError(f"window '{wid}' must be an object")
        try:
            start = _parse_rfc3339(w["start"])
            end = _parse_rfc3339(w["end"])
        except Exception as e:  # noqa: BLE001
            raise StrictValidationError(f"invalid window timestamps for '{wid}': {e}") from e
        if end < start:
            raise StrictValidationError(f"window '{wid}' end must be >= start")

    # sources integrity (only if present)
    source_ids = payload.get("source_ids")
    sources = payload.get("sources")
    if (source_ids is None) ^ (sources is None):
        raise StrictValidationError("sources and source_ids must either both be present or both be absent")

    source_id_set: set[str] = set()
    if sources is not None:
        if not isinstance(source_ids, list) or not isinstance(sources, dict):
            raise StrictValidationError("source_ids must be an array and sources must be an object")
        source_id_set = set(source_ids)
        sources_key_set = set(sources.keys())
        if source_id_set != sources_key_set:
            missing = sorted(source_id_set - sources_key_set)
            extra = sorted(sources_key_set - source_id_set)
            raise StrictValidationError(
                "sources/source_ids mismatch"
                + (f"; missing sources: {missing}" if missing else "")
                + (f"; extra sources: {extra}" if extra else "")
            )

    # axis readings reference checks
    for r in _iter_axis_readings(payload):
        # null-score policy (RFC-0005 7.3): if score is null, it must not be interpreted as zero
        # and MUST be accompanied by an explanation (this repo uses top-level meta as the
        # contract-compatible place to carry that explanation).
        if r.get("score") is None:
            meta = payload.get("meta")
            if not isinstance(meta, dict) or not meta:
                raise StrictValidationError(
                    "axis reading with null score requires a non-empty top-level meta explanation"
                )

        wid = r.get("window_id")
        if wid not in window_id_set:
            raise StrictValidationError(f"axis reading references unknown window_id '{wid}'")

        evidence = r.get("evidence_source_ids")
        if evidence is not None:
            if sources is None:
                raise StrictValidationError("evidence_source_ids present but sources/source_ids are not declared")
            if not isinstance(evidence, list):
                raise StrictValidationError("evidence_source_ids must be an array")
            for sid in evidence:
                if sid not in source_id_set:
                    raise StrictValidationError(f"axis reading references unknown source_id '{sid}'")

    # embeddings reference + dimension checks
    embeddings = payload.get("embeddings")
    if embeddings is not None:
        if not isinstance(embeddings, list):
            raise StrictValidationError("embeddings must be an array")
        for i, emb in enumerate(embeddings):
            if not isinstance(emb, dict):
                raise StrictValidationError(f"embeddings[{i}] must be an object")
            ewid = emb.get("window_id")
            if ewid not in window_id_set:
                raise StrictValidationError(f"embedding references unknown window_id '{ewid}'")
            vec = emb.get("vector")
            dim = emb.get("dimension")
            if vec is not None:
                if not isinstance(vec, list):
                    raise StrictValidationError("embedding.vector must be an array when present")
                if isinstance(dim, int) and dim != len(vec):
                    raise StrictValidationError("embedding.dimension must equal len(embedding.vector)")


