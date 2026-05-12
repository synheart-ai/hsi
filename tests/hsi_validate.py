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


# -------- HSI 1.3 --------


_INFERENCE_MODES_13 = _INFERENCE_MODES_12  # 1.3 deliberately inherits the 1.2 vocabulary unchanged — no new inference modes in this minor version. RFC-HSI-0010 §5.3 keeps `inference_mode` orthogonal to modality.
_DIRECTIONS_13 = frozenset({"higher_is_more", "lower_is_more", "bidirectional", "categorical"})
_OBSERVABLE_MODALITIES_13 = frozenset({"physiological", "kinematic", "digital"})
_SINGLE_MODALITY_DOMAINS_13 = frozenset({"physiological", "kinematic", "digital"})
_MULTIMODAL_DOMAINS_13 = frozenset({"cognitive", "affective"})
_AXIS_DOMAINS_13 = _SINGLE_MODALITY_DOMAINS_13 | _MULTIMODAL_DOMAINS_13


def _iter_readings_with_domain_13(axes: Any) -> Iterable[tuple[str, dict[str, Any]]]:
    """Yield (domain_key, reading) pairs across all 1.3 axes domains."""
    if not isinstance(axes, dict):
        return
    for domain_key, domain in axes.items():
        if not isinstance(domain, list):
            continue
        for r in domain:
            if isinstance(r, dict):
                yield domain_key, r


def _validate_strict_13(payload: dict[str, Any]) -> None:
    """
    HSI 1.3 strict checks (RFC-HSI-0010 §12, RFC-HSI-0011 §9):

    Carryover from 1.2:
    - computed_at_utc >= observed_at_utc
    - window.end_utc >= window.start_utc
    - axis_reading.window_ids reference declared /windows keys
    - embedding.window_id references a declared window key
    - axis_reading.evidence_source_ids reference meta.provenance.sources keys when non-empty
    - embedding.evidence_source_ids reference meta.provenance.sources keys when non-empty
    - null score readings require non-empty top-level meta (explanation)
    - inference_mode vocabulary when present
    - embedding.dimension equals len(vector) when vector is present

    1.3 additions:
    - direction vocabulary (rejects 1.2 'higher_is_less'; accepts 'lower_is_more', 'categorical')
    - axes is closed to {physiological, kinematic, digital, cognitive, affective}
    - HSI-1.3-MODALITIES-USED-MISSING: every reading in cognitive/affective MUST set modalities_used
    - HSI-1.3-MODALITIES-USED-FORBIDDEN: readings in physiological/kinematic/digital MUST NOT
    - HSI-1.3-CATEGORICAL-LABEL-IN-CATEGORIES: when direction == categorical, label MUST appear
      in categories

    The RFC-HSI-0010 §9 affective-availability rule is intentionally NOT enforced here.
    It is a producer-policy SHOULD pending calibration; promote to STRICT in a future RFC
    once supporting evidence exists.
    - HSI-1.3-CONFIDENCE-BREAKDOWN-FORBIDDEN: readings in single-modality domains MUST NOT
      include confidence_breakdown (RFC-HSI-0011 §4.2; defense-in-depth, primary at BASIC)
    - HSI-1.3-CONFIDENCE-BREAKDOWN-MISMATCH: when modalities_used and confidence_breakdown are
      both present, every key of confidence_breakdown MUST appear in modalities_used
      (RFC-HSI-0011 §4.3)
    - 1.3 sources MUST NOT include the per-modality `tiers` object (rejected design); the 1.2
      `source.source_tier` integer is carried over unchanged
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

    axes = payload.get("axes")
    if axes is not None:
        if not isinstance(axes, dict):
            raise StrictValidationError("axes must be an object")
        unknown_domains = set(axes.keys()) - _AXIS_DOMAINS_13
        if unknown_domains:
            raise StrictValidationError(
                f"axes contains domains outside the canonical 1.3 set: {sorted(unknown_domains)}; "
                f"expected subset of {sorted(_AXIS_DOMAINS_13)}"
            )

    prov_sources = _provenance_sources(payload)

    for domain_key, r in _iter_readings_with_domain_13(payload.get("axes")):
        if r.get("score") is None and r.get("direction") != "categorical" and "name" in r:
            _require_non_empty_meta(
                payload,
                "axis reading with null score requires a non-empty top-level meta explanation",
            )

        direction = r.get("direction")
        if direction is not None and direction not in _DIRECTIONS_13:
            raise StrictValidationError(
                f"axis reading has invalid direction '{direction}'; "
                f"expected one of {sorted(_DIRECTIONS_13)}"
            )

        wids = r.get("window_ids")
        if isinstance(wids, list):
            for wid in wids:
                if wid not in window_id_set:
                    raise StrictValidationError(f"axis reading references unknown window id '{wid}'")

        imode = r.get("inference_mode")
        if imode is not None and imode not in _INFERENCE_MODES_13:
            raise StrictValidationError(
                f"axis reading has invalid inference_mode '{imode}'; "
                f"expected one of {sorted(_INFERENCE_MODES_13)}"
            )

        modalities_used = r.get("modalities_used")
        if domain_key in _MULTIMODAL_DOMAINS_13:
            if not modalities_used:
                raise StrictValidationError(
                    f"HSI-1.3-MODALITIES-USED-MISSING: axes.{domain_key}[] reading "
                    f"'{r.get('name')}' must include a non-empty modalities_used"
                )
            if not isinstance(modalities_used, list):
                raise StrictValidationError("modalities_used must be an array")
            unknown = [m for m in modalities_used if m not in _OBSERVABLE_MODALITIES_13]
            if unknown:
                raise StrictValidationError(
                    f"modalities_used entries must be in {sorted(_OBSERVABLE_MODALITIES_13)}; "
                    f"got {unknown}"
                )
        elif domain_key in _SINGLE_MODALITY_DOMAINS_13:
            if modalities_used is not None:
                raise StrictValidationError(
                    f"HSI-1.3-MODALITIES-USED-FORBIDDEN: axes.{domain_key}[] reading "
                    f"'{r.get('name')}' must not include modalities_used "
                    "(modality is encoded by the axis-domain key)"
                )

        if direction == "categorical":
            label = r.get("label")
            categories = r.get("categories")
            if not isinstance(label, str) or not isinstance(categories, list):
                raise StrictValidationError(
                    "categorical axis_reading must include `label` (string) and "
                    "`categories` (array)"
                )
            if label not in categories:
                raise StrictValidationError(
                    f"HSI-1.3-CATEGORICAL-LABEL-IN-CATEGORIES: axes.{domain_key}[] reading "
                    f"'{r.get('name')}' label '{label}' must appear in categories {categories}"
                )

        confidence_breakdown = r.get("confidence_breakdown")
        if confidence_breakdown is not None:
            if domain_key in _SINGLE_MODALITY_DOMAINS_13:
                raise StrictValidationError(
                    f"HSI-1.3-CONFIDENCE-BREAKDOWN-FORBIDDEN: axes.{domain_key}[] reading "
                    f"'{r.get('name')}' must not include confidence_breakdown "
                    "(single-modality readings have no per-channel attribution to make)"
                )
            if not isinstance(confidence_breakdown, dict) or not confidence_breakdown:
                raise StrictValidationError(
                    "confidence_breakdown must be a non-empty object"
                )
            unknown_keys = [
                k for k in confidence_breakdown if k not in _OBSERVABLE_MODALITIES_13
            ]
            if unknown_keys:
                raise StrictValidationError(
                    f"confidence_breakdown keys must be in {sorted(_OBSERVABLE_MODALITIES_13)}; "
                    f"got {unknown_keys}"
                )
            if isinstance(modalities_used, list):
                used = set(modalities_used)
                missing = [k for k in confidence_breakdown if k not in used]
                if missing:
                    raise StrictValidationError(
                        f"HSI-1.3-CONFIDENCE-BREAKDOWN-MISMATCH: axes.{domain_key}[] reading "
                        f"'{r.get('name')}' confidence_breakdown keys {missing} are not in "
                        f"modalities_used {sorted(used)}"
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

    if prov_sources is not None:
        for sid, src in prov_sources.items():
            if not isinstance(src, dict):
                continue
            if "tiers" in src:
                raise StrictValidationError(
                    f"meta.provenance.sources['{sid}'] includes 'tiers'; the per-modality "
                    "tiers object was rejected during 1.3 review (RFC-HSI-0011 §1). "
                    "Use `source.source_tier` (integer 1..=4) for architectural fidelity "
                    "and `axis_reading.confidence_breakdown` for per-channel attribution "
                    "on multimodal readings."
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
    "1.3": _validate_strict_13,
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
