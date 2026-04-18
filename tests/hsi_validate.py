from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator
from jsonschema import FormatChecker


_INFERENCE_MODES_12 = frozenset(
    {
        "probabilistic_model",
        "deterministic_rule",
        "external_provider",
        "composite",
    }
)


class StrictValidationError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _parse_rfc3339(dt_str: str) -> datetime:
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"
    return datetime.fromisoformat(dt_str)


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


def validate_basic(payload: Any, schema_basic: dict[str, Any]) -> None:
    Draft202012Validator(schema_basic, format_checker=FormatChecker()).validate(payload)


# -------- shared helpers --------


def _check_observed_computed(payload: dict[str, Any]) -> None:
    try:
        observed = _parse_rfc3339(payload["observed_at_utc"])
        computed = _parse_rfc3339(payload["computed_at_utc"])
    except Exception as e:  # noqa: BLE001
        raise StrictValidationError(f"invalid observed_at_utc/computed_at_utc: {e}") from e
    if computed < observed:
        raise StrictValidationError("computed_at_utc must be >= observed_at_utc")


def _require_non_empty_meta(payload: dict[str, Any], msg: str) -> None:
    meta = payload.get("meta")
    if not isinstance(meta, dict) or not meta:
        raise StrictValidationError(msg)


def _iter_readings_wrapped(axes: Any) -> Iterable[dict[str, Any]]:
    """1.0 shape: axes.<domain>.readings[]"""
    if not isinstance(axes, dict):
        return
    for domain in axes.values():
        if not isinstance(domain, dict):
            continue
        readings = domain.get("readings")
        if isinstance(readings, list):
            for r in readings:
                if isinstance(r, dict):
                    yield r


def _iter_readings_flat(axes: Any) -> Iterable[dict[str, Any]]:
    """1.1 / 1.2 shape: axes.<domain> is an array of readings."""
    if not isinstance(axes, dict):
        return
    for domain in axes.values():
        if isinstance(domain, list):
            for r in domain:
                if isinstance(r, dict):
                    yield r


def _provenance_sources(payload: dict[str, Any]) -> dict[str, Any] | None:
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return None
    prov = meta.get("provenance")
    if not isinstance(prov, dict):
        return None
    sources = prov.get("sources")
    return sources if isinstance(sources, dict) else None


# -------- HSI 1.0 --------


def _validate_strict_10(payload: dict[str, Any]) -> None:
    """
    HSI 1.0 strict checks:
    - window_ids array matches windows object keys
    - window.end >= window.start
    - computed_at_utc >= observed_at_utc
    - sources and source_ids paired; keys match
    - axis_reading.window_id references a declared window
    - axis_reading.evidence_source_ids reference declared sources
    - null-score readings require non-empty top-level meta
    - embedding.window_id references a declared window
    - embedding.dimension equals len(vector) when vector is present
    """
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

    _check_observed_computed(payload)

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

    source_ids = payload.get("source_ids")
    sources = payload.get("sources")
    if (source_ids is None) ^ (sources is None):
        raise StrictValidationError(
            "sources and source_ids must either both be present or both be absent"
        )

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

    for r in _iter_readings_wrapped(payload.get("axes")):
        if r.get("score") is None and "axis" in r:
            _require_non_empty_meta(
                payload,
                "axis reading with null score requires a non-empty top-level meta explanation",
            )
        wid = r.get("window_id")
        if wid is not None and wid not in window_id_set:
            raise StrictValidationError(f"axis reading references unknown window_id '{wid}'")
        evidence = r.get("evidence_source_ids")
        if evidence:
            if sources is None:
                raise StrictValidationError(
                    "evidence_source_ids present but sources/source_ids are not declared"
                )
            if not isinstance(evidence, list):
                raise StrictValidationError("evidence_source_ids must be an array")
            for sid in evidence:
                if sid not in source_id_set:
                    raise StrictValidationError(f"axis reading references unknown source_id '{sid}'")

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


# -------- HSI 1.1 --------


def _validate_strict_11(payload: dict[str, Any]) -> None:
    """
    HSI 1.1 strict checks:
    - windows map non-empty; window.end_utc >= window.start_utc
    - computed_at_utc >= observed_at_utc
    - axis_reading.window_ids reference declared /windows keys
    - axis_reading.evidence_source_ids reference meta.provenance.sources keys
    - null-value readings require non-empty top-level meta
    - embedding.window_ids reference declared windows
    - embedding.dims equals len(vector) when vector is present
    """
    windows = payload.get("windows")
    if not isinstance(windows, dict) or not windows:
        raise StrictValidationError("windows must be a non-empty object for strict validation")
    window_id_set = set(windows.keys())

    _check_observed_computed(payload)

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

    prov_sources = _provenance_sources(payload)

    for r in _iter_readings_flat(payload.get("axes")):
        if r.get("value") is None and "name" in r:
            _require_non_empty_meta(
                payload,
                "axis reading with null value requires a non-empty top-level meta explanation",
            )
        wids = r.get("window_ids")
        if isinstance(wids, list):
            for wid in wids:
                if wid not in window_id_set:
                    raise StrictValidationError(f"axis reading references unknown window id '{wid}'")
        evidence = r.get("evidence_source_ids")
        if evidence:
            if prov_sources is None or not prov_sources:
                raise StrictValidationError(
                    "evidence_source_ids present but meta.provenance.sources is missing or empty"
                )
            if not isinstance(evidence, list):
                raise StrictValidationError("evidence_source_ids must be an array")
            source_keys = set(prov_sources.keys())
            for sid in evidence:
                if sid not in source_keys:
                    raise StrictValidationError(
                        f"axis reading references unknown provenance source id '{sid}'"
                    )

    embeddings = payload.get("embeddings")
    if embeddings is not None:
        if not isinstance(embeddings, list):
            raise StrictValidationError("embeddings must be an array")
        for i, emb in enumerate(embeddings):
            if not isinstance(emb, dict):
                raise StrictValidationError(f"embeddings[{i}] must be an object")
            ewids = emb.get("window_ids")
            if isinstance(ewids, list):
                for ewid in ewids:
                    if ewid not in window_id_set:
                        raise StrictValidationError(
                            f"embedding references unknown window id '{ewid}'"
                        )
            vec = emb.get("vector")
            dims = emb.get("dims")
            if vec is not None:
                if not isinstance(vec, list):
                    raise StrictValidationError("embedding.vector must be an array when present")
                if isinstance(dims, int) and dims != len(vec):
                    raise StrictValidationError("embedding.dims must equal len(embedding.vector)")


# -------- HSI 1.2 --------


def _validate_strict_12(payload: dict[str, Any]) -> None:
    """
    HSI 1.2 strict checks:
    - computed_at_utc >= observed_at_utc
    - window.end_utc >= window.start_utc
    - axis_reading.window_ids reference declared /windows keys
    - embedding.window_id references a declared window key
    - axis_reading.evidence_source_ids reference meta.provenance.sources keys when non-empty
    - embedding.evidence_source_ids reference meta.provenance.sources keys when non-empty
    - null score readings require non-empty top-level meta (explanation)
    - inference_mode vocabulary when present
    - embedding.dimension equals len(vector) when vector is present
    """
    windows = payload.get("windows")
    if not isinstance(windows, dict) or not windows:
        raise StrictValidationError("windows must be a non-empty object for strict validation")
    window_id_set = set(windows.keys())

    _check_observed_computed(payload)

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

    prov_sources = _provenance_sources(payload)

    for r in _iter_readings_flat(payload.get("axes")):
        if r.get("score") is None and "name" in r:
            _require_non_empty_meta(
                payload,
                "axis reading with null score requires a non-empty top-level meta explanation",
            )
        wids = r.get("window_ids")
        if isinstance(wids, list):
            for wid in wids:
                if wid not in window_id_set:
                    raise StrictValidationError(f"axis reading references unknown window id '{wid}'")
        imode = r.get("inference_mode")
        if imode is not None and imode not in _INFERENCE_MODES_12:
            raise StrictValidationError(
                f"axis reading has invalid inference_mode '{imode}'; "
                f"expected one of {sorted(_INFERENCE_MODES_12)}"
            )
        evidence = r.get("evidence_source_ids")
        if evidence:
            if prov_sources is None or not prov_sources:
                raise StrictValidationError(
                    "evidence_source_ids present but meta.provenance.sources is missing or empty"
                )
            if not isinstance(evidence, list):
                raise StrictValidationError("evidence_source_ids must be an array")
            source_keys = set(prov_sources.keys())
            for sid in evidence:
                if sid not in source_keys:
                    raise StrictValidationError(
                        f"axis reading references unknown provenance source id '{sid}'"
                    )

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
            evidence = emb.get("evidence_source_ids")
            if evidence:
                if prov_sources is None or not prov_sources:
                    raise StrictValidationError(
                        "embedding.evidence_source_ids present but meta.provenance.sources is missing or empty"
                    )
                if not isinstance(evidence, list):
                    raise StrictValidationError("embedding.evidence_source_ids must be an array")
                source_keys = set(prov_sources.keys())
                for sid in evidence:
                    if sid not in source_keys:
                        raise StrictValidationError(
                            f"embedding references unknown provenance source id '{sid}'"
                        )


# -------- dispatcher --------


_STRICT_BY_VERSION = {
    "1.0": _validate_strict_10,
    "1.1": _validate_strict_11,
    "1.2": _validate_strict_12,
}


def supported_versions() -> tuple[str, ...]:
    return tuple(sorted(_STRICT_BY_VERSION))


def validate_strict(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise StrictValidationError("payload must be an object for strict validation")
    version = payload.get("hsi_version")
    fn = _STRICT_BY_VERSION.get(version) if isinstance(version, str) else None
    if fn is None:
        raise StrictValidationError(
            f"unsupported hsi_version '{version}'; expected one of {list(supported_versions())}"
        )
    fn(payload)
