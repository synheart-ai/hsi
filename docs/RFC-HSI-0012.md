# RFC-HSI-0012

## HSI 1.4 — Reading Status, Basis and Freshness

- **Status**: Draft
- **Created**: 2026-10-19
- **Type**: Minor (pre-stable; additive on 1.3 except the tightening in §6.4)
- **Target**: HSI 1.4
- **Owner**: HSI Maintainers
- **Relates to**: RFC-HSI-0008 (1.2 canonical contract, §6.6 null and missing readings), RFC-HSI-0010 (1.3 domain set, `modalities_used`, §9 modality availability), RFC-HSI-0011 (1.3 `confidence_breakdown`, §9 revisit rule), RFC-HSI-0009 (integrity block, unaffected)
- **Canonical schema**: `schema/hsi-1.4.schema.json` (to be added once this RFC is Accepted)

## 1. Purpose

A consumer that receives an HSI 1.3 reading can tell what the producer thinks and how
confident it is. It cannot tell:

1. **Whether the producer tried.** A missing reading can mean "this producer never
   emits that member", "there was no signal", "the person's baseline is not ready yet",
   or "you are not allowed to see this". In many cases 1.3 gives all four the same wire
   shape: absence.
2. **What the score is relative to.** A `stress` score of `0.7` against this person's
   own baseline is a different statement from `0.7` against a population reference. The
   only hint 1.3 carries is `meta.provenance.baseline_status`, which is one free-form
   string for the whole payload.
3. **How long the reading stays true.** 1.3 has `observed_at_utc` and windows, but no
   statement from the producer about when a reading should stop being acted on.

These gaps matter most to consumers that **act** on state rather than display it, such
as software that adapts how it responds to a person. Acting on a stale reading, a
population-relative reading or a silently missing one turns human-aware software into
guesswork.

HSI 1.4 adds optional per-reading fields (`status`, `reason`, `basis`, `valid_until`)
and an optional `meta.context` block. Together they make every reading say whether it is
an estimate, what it is relative to, and when it expires.

## 2. Gaps in the 1.3 contract

Each gap below follows from the published RFCs and `schema/hsi-1.3.schema.json`.

### 2.1 Omission means two things

RFC-HSI-0008 §6.6 says omitted axes mean "the producer does not emit that axis at all",
and `score: null` means "the producer tried to emit but could not".

RFC-HSI-0010 §9 then says producers MUST NOT emit a reading whose required modality is
unavailable. They MAY emit a null-score placeholder instead, but for multimodal readings
1.3 gives that placeholder no legal shape. `modalities_used` is REQUIRED on
`axes.cognitive[]` and `axes.affective[]` with `minItems: 1`, and it means "channels
that contributed" (RFC-HSI-0010 §5.1). A reading that no channel contributed to cannot
be written without inventing a contributor. A producer is left to omit the reading. A
consumer then cannot tell "not supported" from "supported, but no evidence this window",
which is exactly the distinction §6.6 asks it to make.

A producer that wants to tell consumers why a reading is missing has to use a private
`meta` key that no other consumer understands. The categorical shape has the same
problem: `label` is required whenever `direction == categorical`, so a categorical
reading has no way to abstain.

### 2.2 The null-score rule always passes in 1.3

RFC-HSI-0008 §6.6 requires a null score to come with a non-empty `meta` explanation (for
example `meta.null_reading_reason`). HSI-VALIDATE-STRICT checks only that top-level
`meta` is non-empty. 1.3 made `meta.ids.hsi_id` required, so `meta` is never empty and
the check always passes. The explanation is also payload-level, so it cannot say
*which* null reading it explains when there are several. The reason vocabulary is
unspecified, apart from the single example `modality_unavailable` in RFC-HSI-0010 §9.

### 2.3 `baseline_status` cannot gate a reading

`meta.provenance.baseline_status` is an unconstrained string (examples use `"WARMING"`).
It describes one baseline for the whole payload, while a payload commonly mixes
readings normalized in different ways. A personally calibrated physiological reading
can sit beside a cognitive reading that has no personal baseline. A consumer that gates
on `baseline_status` either blocks every reading while one baseline warms up, or trusts
a population-relative reading as personal.

### 2.4 Freshness is left to each consumer

Consumers derive freshness from `observed_at_utc` and window ends with their own
constants. The producer knows the window step and signal cadence that determine how
long a reading holds. Only the producer can state it.

## 3. Non-goals

- **A fusion or calibration policy.** This RFC says what a reading's status is, not how
  a producer decides it.
- **Grants on the wire.** Which consumer may see which member, at what granularity and
  for how long is decided by whatever consent system sits in front of the producer. HSI
  carries the *outcome* (`status: withheld`), never the grant.
- **Coverage enumeration.** HSI does not list every member a producer could ever emit.
  §5.6 says when an abstaining reading is required.
- **Changing `score` semantics.** `null` still means unknown and MUST NOT be read as zero.

## 4. Relation to prior RFCs

- **RFC-HSI-0008**: 1.4 replaces the §6.6 payload-level null explanation with a
  per-reading `status` + `reason` (§6.4). 1.2 and 1.3 payloads are unaffected.
- **RFC-HSI-0010**: in 1.4, the §9 "MUST NOT emit" rule for unavailable modalities
  becomes "MUST emit with `status: insufficient_evidence`" (§5.6). The §5.1
  `modalities_used` requirement is relaxed for readings that carry no estimate (§6.5);
  the required/forbidden split is otherwise unchanged.
- **RFC-HSI-0011**: §9 asks 1.4 to decide `confidence_breakdown`'s future. §9 of this
  RFC applies that rule.
- **RFC-HSI-0009**: the integrity block hashes the whole payload, new fields included.
  No change.

## 5. Per-reading fields

All of these live on `axis_reading`.

### 5.1 `status`

```json
"status": {
  "type": "string",
  "enum": ["estimated", "insufficient_evidence", "stale", "withheld", "corrected"]
}
```

| Value | Meaning | `score` | `confidence` |
| --- | --- | --- | --- |
| `estimated` | The producer computed this reading from evidence in its windows. | non-null (null only when `direction: categorical`; `label` carries the value) | producer's confidence |
| `insufficient_evidence` | The producer is configured to emit this member and tried, but could not estimate it this window. | `null` | `0` |
| `stale` | The producer is re-publishing its most recent estimate after that estimate's `valid_until` has passed, because nothing newer exists. | prior value, or `null` | prior value |
| `withheld` | The producer could estimate this member, but the consumer is not permitted to receive it. | `null` | `0` |
| `corrected` | The person stated a value for this member and window, and it replaces the estimate. | stated value | see §5.1.2 |

#### 5.1.1 `withheld` discloses existence only

A `withheld` reading tells the consumer that the member exists and is outside its
permission, and nothing more. Producers MUST set `score: null`, `confidence: 0` and
`evidence_source_ids: []`. They MUST omit `confidence_breakdown`, `label`, `notes` and
`modalities_used`. `window_ids` MAY be kept so the consumer can line the reading up with
its others.

Producers SHOULD emit `withheld` only for members the consumer asked for. They SHOULD
NOT list every member the consumer is denied, because that publishes the producer's full
capability set to every consumer.

#### 5.1.2 `corrected`

A `corrected` reading reflects the person's own statement for the window the reading
covers, for example a self-report saying they are not stressed. Rules:

- `model_id` uses a new reserved scheme, `stated://` (for example
  `stated://self-report`). This RFC adds it to the reserved list beside `model://`,
  `rulepack://` and `provider://`.
- `inference_mode` is `external_provider`.
- `confidence` is the producer's trust in the statement. A producer that takes
  statements at face value uses `1`.
- A consumer holding both an `estimated` and a `corrected` reading for the same member
  and window MUST prefer the `corrected` one.

### 5.2 `reason`

```json
"reason": {
  "type": "string",
  "enum": ["no_signal", "low_quality", "warming", "not_trained", "not_applicable", "not_granted"]
},
"reason_detail": {
  "type": "string",
  "pattern": "^[a-z][a-z0-9_]*$"
}
```

| `reason` | Meaning | Allowed with `status` |
| --- | --- | --- |
| `no_signal` | No usable evidence arrived for the channels this member needs. | `insufficient_evidence`, `stale` |
| `low_quality` | Evidence arrived but was too sparse, noisy or short to estimate from. | `insufficient_evidence`, `stale` |
| `warming` | The personal baseline this member is relative to is not ready yet. | `insufficient_evidence` |
| `not_trained` | The model has no training evidence for this member or person. | `insufficient_evidence` |
| `not_applicable` | The member is not meaningful under the current sensing conditions, such as intermittent sampling or a device worn where the member cannot be measured. | `insufficient_evidence` |
| `not_granted` | The consumer is not permitted to receive this member. | `withheld` (always) |

Rules:

- `reason` is REQUIRED when `status` is `insufficient_evidence`, `stale` or `withheld`,
  and MUST be absent when `status` is `estimated` or `corrected`.
- `reason_detail` is an OPTIONAL producer-defined token that keeps a more specific cause
  than the `reason` enum (for example `device_off_body`). It MUST NOT appear on
  `withheld` readings. Consumers MUST NOT branch on `reason_detail` values; they are not
  part of the contract.
- `modality_unavailable` (RFC-HSI-0010 §9) corresponds to `no_signal`.

### 5.3 `basis`

```json
"basis": {
  "type": "string",
  "enum": ["personal_stratum", "personal_pooled", "population", "fixed_scale"]
}
```

| Value | The score is relative to |
| --- | --- |
| `personal_stratum` | This person's baseline under comparable conditions (for example, their own weekday-morning baseline). |
| `personal_pooled` | This person's baseline across all conditions, because no comparable-conditions baseline is ready. |
| `population` | A population reference. No personal baseline was used. |
| `fixed_scale` | A fixed formula scale that is not normalized against anyone (for example, a rule that maps an event count onto `[0, 1]`). |

Rules:

- `basis` is OPTIONAL. Absent means unspecified and MUST NOT be read as personal.
- Producers SHOULD set `basis` on every `estimated` and `stale` reading. It MUST be
  absent on `withheld` readings.
- `basis` is per reading because payloads mix readings with different bases (§2.3).
- `meta.provenance.baseline_status` is retained unchanged. Consumers SHOULD treat it as
  informative and MUST NOT use it in place of `basis` to gate a reading.

### 5.4 `valid_until`

```json
"valid_until": { "type": "string", "format": "date-time" }
```

- The producer sets it from the window step and the signal cadence: the latest instant
  at which it still stands behind the reading.
- It MUST be later than `computed_at_utc`, except on `stale` readings, where it carries
  the expired value from the original estimate (HSI-VALIDATE-STRICT).
- **Consumer rule:** a reading whose `valid_until` is in the past at the time of use MUST
  be treated as `stale`, whatever its `status` says.
- OPTIONAL. Consumers keep their own freshness defaults for readings without it.

### 5.5 Field matrix

| `status` | `score` | `confidence` | `reason` | `basis` | `evidence_source_ids` | `modalities_used` (multimodal domains) |
| --- | --- | --- | --- | --- | --- | --- |
| `estimated` | required non-null (categorical: null + `label`) | any | absent | SHOULD | any | required |
| `insufficient_evidence` | `null` | `0` | required | MAY | MAY (the sources that were tried) | MAY be absent |
| `stale` | prior or `null` | prior | required | SHOULD | prior | required if `score` non-null |
| `withheld` | `null` | `0` | `not_granted` | absent | `[]` | absent |
| `corrected` | required non-null (categorical: `label`) | any | absent | MAY | MAY | MAY be absent |

### 5.6 No silent omission

A producer that is configured to emit a member for a consumer MUST emit a reading for it
in every payload that covers a window it is configured for. When it cannot estimate, it
emits an `insufficient_evidence` reading with a `reason`. Dropping the reading is not
allowed.

The set of emitted members MAY depend on configuration (which estimators are enabled)
and on what the consumer asked for. It MUST NOT depend on whether evidence arrived. A
member whose estimator is not enabled is outside that set and is not emitted. This keeps
RFC-HSI-0008 §6.6: omission means "not emitted at all".

This rule is normative but cannot be checked by the schema. It is checked by producer
conformance tests (§11).

## 6. Schema changes

### 6.1 `hsi_version`

`"1.4"`. 1.4 payloads validate against `schema/hsi-1.4.schema.json`. Consumers continue to
validate each payload against the schema for its declared version (`versioning.md`).

### 6.2 `axis_reading`

Add `status`, `reason`, `reason_detail`, `basis` and `valid_until` (§5) as optional
properties. `additionalProperties: false` stays, so a 1.3 validator rejects these
fields. That is expected: a 1.4 payload is not a 1.3 payload.

### 6.3 Conditionals the schema enforces

Expressed as `allOf` / `if` / `then` on `axis_reading`, beside the existing categorical
discriminator:

1. `status ∈ {insufficient_evidence, withheld}` ⇒ `score: null`, `confidence: 0`, `reason` required.
2. `status == withheld` ⇒ `reason: not_granted`, `evidence_source_ids` has `maxItems: 0`,
   and `basis`, `reason_detail`, `confidence_breakdown`, `label`, `notes` and
   `modalities_used` are forbidden.
3. `status == stale` ⇒ `reason` required.
4. `status ∈ {estimated, corrected}` or absent ⇒ `reason` and `reason_detail` forbidden.
5. `status ∈ {estimated, corrected}` and `direction != categorical` ⇒ `score` non-null.
6. `reason == not_granted` ⇒ `status == withheld`. `reason ∈ {warming, not_trained, not_applicable}` ⇒ `status == insufficient_evidence`.

### 6.4 Tightening: a null score needs a status

In 1.4 a reading with `score: null` and `direction` other than `categorical` MUST carry
`status`. This replaces the payload-level rule in §2.2, which always passes. HSI is
pre-stable, so a minor may tighten (`versioning.md`). 1.3 payloads keep validating
against the 1.3 schema.

`status` stays optional on readings with a non-null score. Absent there means
`estimated`. See open question 1 for making it required everywhere.

### 6.5 Relaxing `modalities_used` for readings without an estimate

`axes_domain_multimodal` keeps `modalities_used` required, except when
`status ∈ {insufficient_evidence, withheld, corrected}`, or when `status == stale` with
`score: null`. On `insufficient_evidence` and `corrected` it MAY still be present (the
channels that were tried, or none). On `withheld` it is forbidden (§5.1.1).

The single-modality domains are unchanged: `modalities_used` and `confidence_breakdown`
stay forbidden there.

### 6.6 Categorical readings that abstain

The 1.3 categorical discriminator requires `label` whenever `direction == categorical`.
1.4 requires `label` only when `status` is `estimated`, `corrected` or absent, or is
`stale` with a prior label. On `insufficient_evidence` and `withheld`, `label` MUST be
absent. `categories` MAY stay on `insufficient_evidence` so consumers know the
vocabulary, and is forbidden on `withheld`.

### 6.7 `meta.context`

See §7.

### 6.8 HSI-VALIDATE-STRICT additions

Checks the schema cannot express:

| Code | Rule |
| --- | --- |
| `HSI-1.4-VALID-UNTIL-ORDER` | `valid_until > computed_at_utc` unless `status == stale` |
| `HSI-1.4-STALE-NOT-EXPIRED` | `status == stale` with `valid_until ≥ computed_at_utc` |
| `HSI-1.4-DUPLICATE-MEMBER` | Two readings for the same member in one domain with overlapping `window_ids`, unless exactly one is `corrected` |
| `HSI-1.4-CONTEXT-UNKNOWN-WINDOW` | A `meta.context` key that is not a key of `windows` |
| `HSI-1.4-CONTEXT-CONFIDENCE-MISSING` | A context field with `source: inferred` and no `confidence` |

The 1.3 STRICT rules carry over unchanged, except the `modalities_used`-missing check,
which follows §6.5.

## 7. `meta.context` — the context frame

### 7.1 Purpose

Readings are interpreted relative to the conditions they were observed under: still or
moving, in a meeting or working alone, inside a focus block the person set. 1.3 dissolved
the `axes.context` domain (RFC-HSI-0010 §11), so there is no canonical place for those
conditions. 1.4 adds an optional map from window id to a context frame. Each field
records **how the producer knows it**.

### 7.2 Shape

```json
"meta": {
  "context": {
    "w1": {
      "activity":     { "value": "still",         "source": "inferred", "confidence": 0.9 },
      "work_context": { "value": "meeting",       "source": "inferred", "confidence": 0.7 },
      "time_of_day":  { "value": "morning",       "source": "observed" },
      "app_category": { "value": "communication", "source": "observed" },
      "focus_window": { "value": true,            "source": "stated" }
    }
  }
}
```

```json
"context_field": {
  "type": "object",
  "additionalProperties": false,
  "required": ["value", "source"],
  "properties": {
    "value": {
      "anyOf": [
        { "type": "string", "pattern": "^[a-z][a-z0-9_]*$" },
        { "type": "boolean" }
      ]
    },
    "source": { "type": "string", "enum": ["observed", "inferred", "stated"] },
    "confidence": { "$ref": "#/$defs/score01" }
  }
}
```

- The frame is an object whose property names are field names
  (`^[a-z][a-z0-9_]*$`) and whose values are `context_field`. As with axis names,
  consumers MUST tolerate unknown field names.
- Canonical field names in 1.4: `activity`, `work_context`, `time_of_day`,
  `app_category`, `focus_window`. Their value vocabularies are listed in an appendix to
  the 1.4 schema PR, not frozen here.
- `confidence` is required when `source == inferred` and SHOULD be omitted otherwise.
- When a stated value and an inferred value exist for the same field and window, the
  producer MUST emit the stated one.

### 7.3 Privacy

Context is more identifying than a cognitive score, so these rules are normative:

- Values are coarse categorical tokens or booleans. Coordinates, place names, app or
  site names, window titles, URLs, meeting titles and participants MUST NOT appear. The
  token pattern blocks free text, and `privacy.contains_pii` stays `const: false`.
- A producer emits `meta.context` only when the consumer is permitted to receive
  context. There is no `withheld` form for context: an unpermitted frame is omitted.
- Producers SHOULD emit only the fields the consumer needs.

## 8. Producer guidance

Common reasons a producer cannot estimate a reading, and how each maps to 1.4:

| Situation | 1.4 reading |
| --- | --- |
| No sensor connected, or no samples this window | `insufficient_evidence` / `no_signal` |
| Device not on the body | `insufficient_evidence` / `no_signal`, `reason_detail: device_off_body` |
| Samples present but too few, noisy or short | `insufficient_evidence` / `low_quality` |
| Personal baseline not ready, no fallback | `insufficient_evidence` / `warming` |
| Personal baseline not ready, falls back to a broader reference | `estimated` with `basis: personal_pooled` or `population` |
| Model has no training evidence for this member or person | `insufficient_evidence` / `not_trained` |
| Member not meaningful under intermittent sampling or the current device placement | `insufficient_evidence` / `not_applicable` |
| Estimator not enabled in this deployment | not emitted (outside the configured set, §5.6) |
| Consumer not permitted to receive the member | `withheld` / `not_granted` |
| Person corrected the estimate | `corrected` with a `stated://` `model_id` |

Producers that already report omission reasons under a private `meta` key SHOULD move
them onto the readings when they emit 1.4. They MAY keep the private key on 1.3 payloads.

## 9. `confidence_breakdown`: the RFC-HSI-0011 §9 revisit

RFC-HSI-0011 §9 keeps the field only if a canonical producer populates it consistently
**and** a canonical consumer reads it for a real downstream policy. The maintainers know
of no producer that does the first, or consumer that does the second.

1.4 therefore **deprecates** `confidence_breakdown`. It stays in the 1.4 schema so
producers can still send it, and is scheduled for removal in 1.5. Reviewers who have a
producer or consumer that meets the §9 test should say so on this RFC. If one appears
before 1.5 is cut, the deprecation is reversed by a new RFC.

## 10. Consumer guidance (non-normative)

**Consumers that act on state** (for example, adapting how an assistant responds). Use a
reading to drive behaviour only when all of the following hold:

- `status ∈ {estimated, corrected}`;
- `valid_until` has not passed;
- `basis ∈ {personal_stratum, personal_pooled}`, or `fixed_scale` for members the
  consumer has decided are meaningful on a fixed scale;
- `confidence` is at or above the consumer's own floor.

Readings that fail any check are unknown, as in 1.3. Their `reason` lets the consumer
tell "no sensor" (`no_signal`) from "still calibrating" (`warming`) from "not shared with
you" (`not_granted`), and explain which one applies instead of a generic "unavailable".

**Consumers that display state.** Show `reason` in plain words, for example "Still
learning your baseline" or "Not shared with this app". Never show a number for a reading
that is not `estimated` or `corrected`. Show `basis` as "compared with your usual" versus
"compared with people in general".

**Libraries and SDKs.** Expose `status`, `reason`, `basis` and `valid_until` as typed
fields. Provide a single helper, such as `isActionable(reading, now)`, that implements
the action check above with the floor as a parameter.

**Downgrading to 1.3.** A producer that must also serve a 1.3 consumer:

- strips the five new fields and `meta.context`;
- drops `withheld` readings;
- keeps non-categorical `insufficient_evidence` readings as `score: null` where they are
  legal in 1.3, and drops them where they are not (multimodal readings with no
  `modalities_used`, and abstaining categorical readings).

## 11. Conformance and acceptance

The 1.4 schema PR ships with:

- `schema/hsi-1.4.schema.json`, `test-vectors/v1.4/`, and a `_validate_strict_14` path in
  `tests/hsi_validate.py` implementing §6.8.
- Valid examples:
  - `status_insufficient_evidence_multimodal.json` (no `modalities_used`);
  - `status_withheld.json`;
  - `status_stale.json`;
  - `status_corrected.json`;
  - `basis_mixed.json` (personal and population readings in one payload);
  - `context_frame.json`;
  - `categorical_insufficient_evidence.json`.
- Invalid examples:
  - `withheld_with_score.json`;
  - `withheld_with_evidence.json`;
  - `insufficient_evidence_nonzero_confidence.json`;
  - `estimated_with_reason.json`;
  - `estimated_null_score.json`;
  - `null_score_without_status.json`;
  - `warming_on_withheld.json`;
  - `valid_until_before_computed.json`;
  - `context_free_text_value.json`;
  - `context_unknown_window.json`.

Producer conformance, which a producer claiming 1.4 SHOULD demonstrate:

- With no sensor connected, every configured member that needs that sensor is present
  with `status: insufficient_evidence, reason: no_signal`.
- From a cold start, members relative to a personal baseline report `reason: warming`
  (or a fallback `basis`) until the baseline is ready, then carry a personal `basis`.
- No configured member is ever missing from a payload (§5.6), checked over a recorded
  multi-hour session that includes signal dropouts.
- Payloads validate at BASIC and STRICT against the 1.4 schema. The §10 downgrade output
  validates against the 1.3 schema.

## 12. Rollout

| Step | What | Gate |
| --- | --- | --- |
| 1 | This RFC reviewed and Accepted | Open questions 1–3 resolved |
| 2 | 1.4 schema, examples, test vectors, strict validator | CI green; README status table updated |
| 3 | At least one producer emits 1.4 | Producer conformance (§11) |
| 4 | At least one consumer applies §10 | The unknown-≠-zero behaviour from 1.3 is preserved |

1.4 is cut when steps 2 and 3 land.

## 13. Open questions

1. **Should `status` be required on every 1.4 reading?** This draft requires it only on
   null-score readings (§6.4), as the smallest tightening that fixes §2.2. Requiring it
   everywhere lets consumers branch on one field instead of inferring `estimated` from
   absence. The cost is one field per reading for every producer. Pre-stable rules allow
   either.
2. **Should `withheld` exist on the wire?** It tells a consumer that a member exists
   (§5.1.1). The alternative is omission, which brings back the ambiguity in §2.1. The
   draft keeps `withheld`, limited to members the consumer asked for.
3. **`corrected` confidence.** Should a statement always carry `confidence: 1`, or may a
   producer discount statements that contradict strong evidence? The draft leaves it to
   the producer (§5.1.2).
4. **Context vocabularies.** Should the five canonical context fields have closed value
   enums in the schema, or stay open tokens with an appendix as drafted?
5. **`fixed_scale` naming.** The alternative is `absolute`. `fixed_scale` was chosen
   because these scores are still normalized onto `[0, 1]`, just not against a person
   or a population.
6. **`baseline_status`.** Deprecate it in 1.5 once `basis` is populated, or keep it as a
   payload-level summary?

## Change log

- **Draft (2026-10-19)** — First draft. Per-reading `status` / `reason` / `basis` /
  `valid_until`; no silent omission; null score needs a status; `modalities_used` and
  categorical `label` relaxed for readings without an estimate; `meta.context` frame
  with observed / inferred / stated sources; `stated://` scheme; deprecation of
  `confidence_breakdown` per RFC-HSI-0011 §9.
