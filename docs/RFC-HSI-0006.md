# RFC-HSI-0006

## HSI 1.1 Context Domain Extension and Provenance Guidance

- **Status**: Accepted
- **Type**: Minor version update (non-breaking)
- **Target**: HSI 1.1
- **Owner**: HSI Maintainers

## 1. Purpose

HSI is the canonical transport contract for human state frames.

This RFC extends HSI with a first-class **context** axis domain while preserving backward compatibility.

## 2. Schema Change

Add:

- `axes.context.readings[]`

`axes.context.readings[]` uses the same `AxisReading` structure as other domains.

No other breaking changes are introduced. Existing payloads remain valid.

> **Note:** The optional **emotion** head and refined per-reading `inference_mode` vocabulary are defined in **HSI 1.2** ([RFC-HSI-0007](./RFC-HSI-0007.md)), not in 1.1.

## 3. Normative Definition: Context Axes

Context axes are numeric qualifiers describing runtime conditions used to interpret other axes.

Allowed examples (non-exhaustive):

- `activity_still_conf`, `activity_walk_conf`, `activity_run_conf`, `activity_drive_conf`
- `sleep_episode_active` (0/1)
- `context_stability`
- `baseline_ready` (0/1)
- `baseline_maturity` (0..1)

Rules:

- **Numeric only**
- **Axis names MUST be** `lower_snake_case`
- **No free-text labels** for location/app/environment
- **Readings MUST reference valid windows** via `window_ids`

## 4. Provenance Guidance (Normative for Producers)

Producers MUST place inference/baseline provenance in `meta.provenance`, for example:

```json
{
  "meta": {
    "provenance": {
      "baseline_status": "READY",
      "srm_snapshot_id": "…",
      "inference_mode": "deterministic|probabilistic|composite",
      "providers": [{ "id": "synheart-focus", "version": "x.y.z" }]
    }
  }
}
```

This avoids adding new top-level fields and keeps strict parsing stable.

## 5. Security and Privacy

Context axes can indirectly encode sensitive patterns. Producers MUST NOT:

- include location names
- include app/package names
- include user identifiers
- include free-text environment descriptors