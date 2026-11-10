# RFC-HSI-0012

## HSI 1.4 — Reading Status, Basis and Freshness

- **Status**: Draft 5 — adds `resolution` for coarsened scores (§5.4.2); pending review
- **Created**: 2026-10-19
- **Type**: Minor (pre-stable; additive on 1.3 except the tightening in §6.4, which makes `status` required)
- **Target**: HSI 1.4
- **Owner**: HSI Maintainers
- **Relates to**: RFC-HSI-0008 (1.2 canonical contract, §6.6 null and missing readings), RFC-HSI-0010 (1.3 domain set, `modalities_used`, §9 modality availability), RFC-HSI-0011 (1.3 `confidence_breakdown`, §9 revisit rule), RFC-HSI-0009 (integrity block, unaffected)
- **Canonical schema**: `schema/hsi-1.4.schema.json` (draft, tracks this RFC)

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
- **A work-state domain.** Deferred to its own RFC targeting 1.5 (§13).

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
  "enum": ["estimated", "stated", "insufficient_evidence", "withheld"]
}
```

| Value | Meaning | Shape |
| --- | --- | --- |
| `estimated` | The producer computed this reading from evidence in its windows. | value-bearing |
| `stated` | The person stated a value for this member and window, either correcting an estimate or reporting one where none exists. | value-bearing |
| `insufficient_evidence` | The producer is configured to emit this member and tried, but could not estimate it this window. | abstention |
| `withheld` | The producer could estimate this member, but the consumer is not permitted to receive it. | abstention |

`status` is REQUIRED on every 1.4 reading (§13 Q1). Consumers branch on one field
instead of inferring `estimated` from absence.

`status` selects one of two shapes:

- **Value-bearing** (`estimated`, `stated`): the 1.3 reading plus `status`. `score`,
  `confidence`, `direction`, `inference_mode`, `model_id` and `evidence_source_ids` are
  required, as in 1.3.
- **Abstention** (`insufficient_evidence`, `withheld`): `name`, `status`, `reason` and
  `window_ids`. `score`, `confidence`, `direction`, `basis`, `baseline_version`,
  `valid_until`, `modalities_used` and `confidence_breakdown` MUST be absent. An
  abstention carries nothing that could be read as a value, so a consumer cannot misread
  a placeholder as zero, and the producer never invents a confidence for an estimate that
  does not exist:

  ```json
  { "name": "cognitive_load", "status": "insufficient_evidence", "reason": "no_signal", "window_ids": ["w_0900"] }
  ```

  An `insufficient_evidence` reading MAY also carry `reason_detail`, `notes`,
  `evidence_source_ids` (the sources that were tried) and `model_id` / `inference_mode`
  (the estimator that abstained).

Freshness is not a status. A producer that republishes its last estimate because nothing
newer exists keeps it `estimated` with its original `valid_until`; the expired
`valid_until` tells the consumer it must not act on it (§5.4).

#### 5.1.1 `withheld` discloses existence only

A `withheld` reading tells the consumer that the member exists and is outside its
permission, and nothing more. It is the abstention shape with `reason: not_granted`, and
nothing else: `evidence_source_ids`, `model_id`, `inference_mode`, `reason_detail` and
`notes` MUST also be absent. `window_ids` stays so the consumer can line the reading up
with its others.

Producers SHOULD emit `withheld` only for members the consumer asked for. They SHOULD
NOT list every member the consumer is denied, because that publishes the producer's full
capability set to every consumer.

A `withheld` reading also tells the consumer that the person declined. Where the consumer
holds power over the person, such as an employer, that disclosure can itself become
pressure. Whether a denial is shown as `withheld` or as omission is therefore decided by
the consent system on the person's behalf, not by the consumer. Producers SHOULD default
to omission for consumers acting for an organization rather than for the person.

#### 5.1.2 `stated`

A `stated` reading carries the person's own statement for the window the reading covers.
It covers two cases: a correction of an estimate (for example, "I am not stressed") and a
standalone report where no estimate exists (for example, a questionnaire rating). 1.3 has
no legal shape for the second case: self-report is a source type but not a modality, so a
multimodal reading backed only by self-report must name a channel it did not use. Rules:

- `status: stated` is the only signal that a reading is stated. Consumers MUST NOT infer
  it from `model_id` or `inference_mode`.
- This RFC adds a reserved `model_id` scheme, `stated://` (for example
  `stated://self-report`), beside `model://`, `rulepack://` and `provider://`. Producers
  SHOULD use it for stated readings and SHOULD NOT use it for others. `inference_mode`
  SHOULD be `external_provider`. Neither is enforced: they describe where the value came
  from, and repeating `status` in them would give three fields that could disagree.
- `confidence` is the producer's trust in the statement. It defaults to `1`. A producer
  MAY discount a statement that contradicts strong evidence, and SHOULD document how
  (§13 Q3). Consumers still prefer the `stated` reading.
- `modalities_used` MAY be absent, because a statement is not observed through a channel.
  Its source SHOULD be a `meta.provenance.sources` entry with `type: self_report`.
- A consumer holding both an `estimated` and a `stated` reading for the same member
  and window MUST prefer the `stated` one.

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
| `no_signal` | No usable evidence arrived for the channels this member needs. | `insufficient_evidence` |
| `low_quality` | Evidence arrived but was too sparse, noisy or short to estimate from. | `insufficient_evidence` |
| `warming` | The personal baseline this member is relative to is not ready yet. | `insufficient_evidence` |
| `not_trained` | The model has no training evidence for this member or person. | `insufficient_evidence` |
| `not_applicable` | The member is not meaningful under the current sensing conditions, such as intermittent sampling or a device worn where the member cannot be measured. | `insufficient_evidence` |
| `not_granted` | The consumer is not permitted to receive this member. | `withheld` (always) |

Rules:

- `reason` is REQUIRED on abstentions and MUST be absent on value-bearing readings.
  `not_granted` is used with `withheld` and nothing else; every other reason implies
  `insufficient_evidence`.
- `reason_detail` is an OPTIONAL producer-defined token on `insufficient_evidence`
  readings that keeps a more specific cause than the `reason` enum (for example
  `device_off_body`). Consumers MUST NOT branch on `reason_detail` values; they are not
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
- Producers SHOULD set `basis` on every `estimated` reading. It MUST be absent on
  abstentions.
- `basis` is per reading because payloads mix readings with different bases (§2.3).
- `meta.provenance.baseline_status` is retained unchanged in 1.4 and is scheduled for
  deprecation in 1.5 (§13 Q6). Consumers SHOULD treat it as informative and MUST NOT use
  it in place of `basis` to gate a reading.

#### 5.3.1 `baseline_version`

```json
"baseline_version": { "type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$" }
```

`basis` says what a score is relative to, but not which version of that reference. When a
person's baseline is re-estimated, readings before and after share a `basis` yet are not
comparable (§13 Q8). `baseline_version` is an OPTIONAL opaque identifier of the reference
version, such as a hash or counter of the baseline parameters.

- It requires `basis` and MUST be absent on abstentions.
- Consumers comparing readings over time SHOULD treat readings with different
  `baseline_version` values as not directly comparable.
- Its value carries no meaning beyond equality; consumers MUST NOT parse it.

### 5.4 `valid_until`

```json
"valid_until": { "type": "string", "format": "date-time" }
```

- The producer sets it from the window step and the signal cadence: the latest instant
  at which it still stands behind the value. Value-bearing readings only.
- A republished estimate keeps the `valid_until` it was first emitted with. It is not
  ordered against `computed_at_utc`.
- **Consumer rule:** a consumer MUST NOT act on a reading whose `valid_until` is in the
  past at the time of use. This one rule is the whole freshness mechanism; there is no
  separate status for an expired reading, so the producer's label and the consumer's
  clock cannot disagree.
- OPTIONAL. Consumers keep their own freshness defaults for readings without it.

### 5.4.1 Provider readings without confidence

Many platform scores relayed with `inference_mode: external_provider` carry no
uncertainty. 1.3 requires `confidence`, so producers invent one. In 1.4 `confidence` MAY
be `null`, but only when `inference_mode` is `external_provider` (§13 Q7). Producers MUST
NOT assign an arbitrary value to such a reading. A consumer with a confidence floor treats
a `null` confidence as failing it unless the consumer has decided to trust that provider.

### 5.4.2 `resolution`

```json
"resolution": {
  "type": "object",
  "additionalProperties": false,
  "required": ["kind", "lower", "upper"],
  "properties": {
    "kind":  { "const": "band" },
    "lower": { "$ref": "#/$defs/score01" },
    "upper": { "$ref": "#/$defs/score01" },
    "label": { "$ref": "#/$defs/token" }
  }
}
```

A consent system may let a consumer receive a member only coarsely (§3). The producer
then reports a value that stands for a band, not its estimate. Without a marker, a
consumer reads that value as a point estimate: it charts a trend across readings that
only changed band, or compares a threshold that falls inside the band. `resolution`
says that a score is coarse and how coarse:

```json
{ "name": "focus", "status": "estimated", "score": 0.83,
  "resolution": { "kind": "band", "lower": 0.66, "upper": 1.0, "label": "high" }, ... }
```

Rules:

- A producer that reports a score coarser than its estimate MUST set `resolution`.
  Absent means `score` is the producer's estimate at full resolution.
- `kind: band`: the estimate lies in `[lower, upper]`, and `score` is the value the
  producer reports for that band. `lower` MUST be below `upper` and `score` MUST lie
  within the band (HSI-VALIDATE-STRICT, §6.8). Producers SHOULD report the band's
  midpoint.
- `label` is an OPTIONAL producer-defined name for the band. Consumers MUST NOT branch on
  it; the bounds are the contract. Band edges are producer policy and SHOULD be
  documented by the producer.
- Value-bearing numeric readings only. `resolution` MUST be absent on abstentions, and on
  categorical readings, whose label is already coarse.
- `confidence`, `basis`, `baseline_version` and `valid_until` keep their meaning: they
  describe the estimate the band was taken from.
- Consumers MUST NOT treat a reading with `resolution` as more precise than its band.
  Two readings in the same band are equal; a threshold inside `(lower, upper)` cannot be
  decided from the reading, so the consumer treats that comparison as unknown.

Which consumers receive which members coarsely stays with the consent system, as for
`withheld` (§3). HSI carries the outcome, never the grant.

### 5.5 Field matrix

| `status` | `score` | `confidence` | `reason` | `basis`, `valid_until` | `resolution` | `evidence_source_ids` | `modalities_used` (multimodal domains) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `estimated` | required non-null (categorical: null + `label`) | required (`null` only on `external_provider`, §5.4.1) | absent | SHOULD | required when coarsened; absent on categorical | required | required |
| `stated` | required non-null (categorical: null + `label`) | required | absent | MAY | required when coarsened; absent on categorical | required | MAY |
| `insufficient_evidence` | absent | absent | required | absent | absent | MAY (the sources that were tried) | absent |
| `withheld` | absent | absent | `not_granted` | absent | absent | absent | absent |

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

Add `status` (required, §6.4) and `reason`, `reason_detail`, `basis`, `baseline_version`,
`resolution` and `valid_until` (optional) (§5). The base `required` list becomes `name`, `status`,
`window_ids`; the remaining 1.3 required fields move under the value-bearing branch.
`confidence` becomes nullable under §5.4.1.
`additionalProperties: false` stays, so a 1.3 validator rejects these fields. That is
expected: a 1.4 payload is not a 1.3 payload.

### 6.3 Conditionals the schema enforces

Expressed as `allOf` / `if` / `then` on `axis_reading`, beside the existing categorical
discriminator:

1. `status ∈ {estimated, stated}` ⇒ `score`, `confidence`, `direction`,
   `evidence_source_ids`, `inference_mode` and `model_id` required; `reason` and
   `reason_detail` forbidden.
2. `status ∈ {insufficient_evidence, withheld}` ⇒ `reason` required; `score`,
   `confidence`, `direction`, `basis`, `baseline_version`, `valid_until`,
   `modalities_used`, `confidence_breakdown` and `resolution` forbidden.
3. `status == withheld` ⇒ `reason: not_granted`; `evidence_source_ids`, `model_id`,
   `inference_mode`, `reason_detail` and `notes` forbidden. Any other status ⇒ `reason`
   is not `not_granted`.
4. `direction == categorical` ⇒ `score: null`, `label` and `categories` required,
   `resolution` forbidden (§5.4.2). Any
   other present direction, or none ⇒ `score` (if present) non-null, `label` and
   `categories` forbidden (the 1.3 discriminator, unchanged in form).
5. `confidence: null` ⇒ `inference_mode == external_provider` (§5.4.1).
6. `baseline_version` present ⇒ `basis` required (§5.3.1).

### 6.4 Tightening: every reading carries a status

In 1.4 every reading MUST carry `status` (§13 Q1). This replaces the payload-level null
explanation in §2.2, which always passes, and removes the need to infer `estimated` from
absence. HSI is pre-stable, so a minor may tighten (`versioning.md`). 1.3 payloads keep
validating against the 1.3 schema.

### 6.5 Relaxing `modalities_used` for readings without an estimate

`axes_domain_multimodal` requires `modalities_used` on `estimated` readings only. It MAY
be present on `stated` readings and is forbidden on abstentions (§5.1).

The single-modality domains are unchanged: `modalities_used` and `confidence_breakdown`
stay forbidden there.

### 6.6 Categorical readings that abstain

The 1.3 categorical discriminator is unchanged: `direction == categorical` requires
`label` and `categories`. An abstention carries no `direction`, so a categorical member
abstains with the same four-field shape as any other member, and the discriminator does
not apply. The member's vocabulary is a property of the member, carried on its
value-bearing readings.

### 6.7 `meta.context`

See §7.

### 6.8 HSI-VALIDATE-STRICT additions

Checks the schema cannot express:

| Code | Rule |
| --- | --- |
| `HSI-1.4-DUPLICATE-MEMBER` | Two readings for the same member in one domain with overlapping `window_ids`, unless exactly one is `stated` |
| `HSI-1.4-CONTEXT-UNKNOWN-WINDOW` | A `meta.context` key that is not a key of `windows` |
| `HSI-1.4-CONTEXT-CONFIDENCE-MISSING` | A context field with `source: inferred` and no `confidence` (also enforced at BASIC) |
| `HSI-1.4-RESOLUTION-RANGE` | A `resolution` band whose `lower` is not below its `upper`, or a `score` outside `[lower, upper]` (§5.4.2) |

The 1.3 STRICT rules carry over unchanged, except:

- the `modalities_used`-missing check applies to `estimated` readings only (§6.5);
- checks on `direction`, `inference_mode` and evidence references skip abstentions that
  omit those fields;
- the payload-level null-score meta rule is dropped, because §6.4 replaces it.

## 7. `meta.context` — the context frame

### 7.1 Purpose

Readings are interpreted relative to the conditions they were observed under: still or
moving, in a meeting or working alone, inside a focus block the person set, in a loud or
hot room. The surroundings that shape state are read beside it, not mistaken for it.
1.3 dissolved
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
      "focus_window": { "value": true,            "source": "stated" },
      "place_type":   { "value": "workplace",     "source": "inferred", "confidence": 0.8 },
      "noise_band":   { "value": "loud",          "source": "observed" }
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
- Canonical field names in 1.4 are the five activity and work fields `activity`,
  `work_context`, `time_of_day`, `app_category`, `focus_window`, and the five environment
  fields `place_type`, `air_quality_band`, `noise_band`, `light_band`,
  `temperature_band`. Each has a closed value vocabulary, listed in Appendix A and
  enforced by the schema (§13 Q4). Extensions use non-canonical field names with the same
  `context_field` shape.
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
| Person corrected the estimate, or reported a value with no estimate | `stated` (conventionally with a `stated://` `model_id`) |
| Nothing newer than the last estimate, and the producer republishes it | `estimated`, keeping its original (now past) `valid_until` |

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

- `status ∈ {estimated, stated}`;
- `valid_until` has not passed;
- `basis ∈ {personal_stratum, personal_pooled}`, or `fixed_scale` for members the
  consumer has decided are meaningful on a fixed scale;
- `confidence` is at or above the consumer's own floor;
- for a reading with `resolution`, the decision depends only on its band: a threshold
  inside `(lower, upper)` is unknown, not met or missed.

Readings that fail any check are unknown, as in 1.3. Their `reason` lets the consumer
tell "no sensor" (`no_signal`) from "still calibrating" (`warming`) from "not shared with
you" (`not_granted`), and explain which one applies instead of a generic "unavailable".

**Consumers that display state.** Show `reason` in plain words, for example "Still
learning your baseline" or "Not shared with this app". Never show a number for a reading
that is not `estimated` or `stated`. Show `basis` as "compared with your usual" versus
"compared with people in general".

**Libraries and SDKs.** Expose `status`, `reason`, `basis`, `resolution` and `valid_until` as typed
fields. Provide a single helper, such as `isActionable(reading, now)`, that implements
the action check above with the floor as a parameter.

**Downgrading to 1.3.** A producer that must also serve a 1.3 consumer:

- strips `status`, `reason`, `reason_detail`, `basis`, `baseline_version`,
  `valid_until` and `meta.context`;
- drops `withheld` and `stated` readings, readings with `confidence: null`, and readings
  with `resolution`, none of which 1.3 can represent faithfully (a 1.3 consumer would
  read a coarsened score as a point estimate);
- drops `insufficient_evidence` readings. 1.3 has a `score: null` placeholder, but
  rebuilding one needs a `direction`, `model_id` and a confidence the abstention does not
  carry, and the 1.3 null-score explanation is payload-level (§2.2). Omission is the
  honest 1.3 rendering.

## 11. Conformance and acceptance

The 1.4 schema PR ships with:

- `schema/hsi-1.4.schema.json`, `test-vectors/v1.4/`, and a `_validate_strict_14` path in
  `tests/hsi_validate.py` implementing §6.8.
- Valid examples:
  - `status_insufficient_evidence_multimodal.json` (lean abstentions in a multimodal domain);
  - `status_withheld.json`;
  - `estimated_republished_expired.json` (republished estimates with a past `valid_until`);
  - `status_stated.json` (standalone self-report);
  - `status_stated_correction.json` (an estimate and a statement for the same window);
  - `basis_mixed.json` (personal, population and fixed-scale readings, with a `baseline_version`);
  - `context_frame.json` (all ten canonical fields plus an extension field);
  - `categorical_estimated_and_abstention.json`;
  - `provider_null_confidence.json` (§5.4.1);
  - `resolution_band.json` (a coarsened score beside full-resolution ones, §5.4.2).
- Invalid examples:
  - `withheld_with_score.json`, `withheld_with_evidence.json`, `withheld_with_basis.json`;
  - `abstention_with_confidence.json`, `abstention_with_null_score.json`,
    `abstention_with_direction.json`, `abstention_without_reason.json`;
  - `estimated_with_reason.json`, `estimated_null_score.json`, `stated_without_value.json`;
  - `status_missing.json` (§6.4), `status_stale.json` (not a 1.4 status);
  - `warming_on_withheld.json`, `not_granted_on_insufficient_evidence.json`;
  - `multimodal_estimated_without_modalities.json`;
  - `null_confidence_non_provider.json`,
    `baseline_version_without_basis.json`, `duplicate_member.json`;
  - `context_free_text_value.json`, `context_unknown_vocab_value.json`,
    `context_unknown_window.json`, `context_inferred_without_confidence.json`;
  - `resolution_on_abstention.json`, `resolution_on_categorical.json`,
    `resolution_score_outside_band.json`, `resolution_inverted_bounds.json`,
    `resolution_unknown_kind.json`.

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
| 1 | This RFC reviewed and Accepted | Open questions resolved (done in draft 3, §13); design review applied (draft 4) |
| 2 | 1.4 schema, examples, test vectors, strict validator | CI green; README status table updated |
| 3 | At least one producer emits 1.4 | Producer conformance (§11) |
| 4 | At least one consumer applies §10 | The unknown-≠-zero behaviour from 1.3 is preserved |

1.4 is cut when steps 2 and 3 land.

## 13. Resolved questions

Draft 3 resolves every open question from drafts 1 and 2.

1. **Is `status` required on every 1.4 reading?** Yes (§6.4). Consumers branch on one
   field instead of inferring `estimated` from absence, at the cost of one field per
   reading.
2. **Does `withheld` exist on the wire?** Yes. It applies only to members the consumer
   asked for, and the consent system decides on the person's behalf whether a denial is
   shown as `withheld` or as omission (§5.1.1).
3. **`stated` confidence.** Defaults to `1`. A producer MAY discount a statement that
   contradicts strong evidence and SHOULD document how. Consumers still prefer `stated`
   readings (§5.1.2).
4. **Context vocabularies.** Closed enums for every canonical field, enforced by the
   schema (Appendix A). Context is the most identifying part of a payload, and the token
   pattern alone still admits values such as product names. Extensions use non-canonical
   field names.
5. **`fixed_scale` naming.** Kept. These scores are still normalized onto `[0, 1]`, just
   not against a person or a population, so `absolute` would mislead.
6. **`baseline_status`.** Retained in 1.4 as an informative payload-level summary and
   scheduled for deprecation in 1.5, once producers populate `basis`.
7. **Provider readings without confidence.** `confidence` MAY be `null`, only on
   `external_provider` readings (§5.4.1). Producers no longer invent a value.
8. **Baseline versions.** An optional per-reading `baseline_version` (§5.3.1).

Design decisions recorded with draft 4, from a review of wire size and rule count:

9. **Abstentions are lean.** An abstention is `name`, `status`, `reason`, `window_ids`
   (§5.1). Draft 3 required the full value shape with `score: null` and `confidence: 0`,
   which made a producer invent a confidence for an estimate that did not exist and
   cost nearly three times the bytes per abstention.
10. **No `stale` status.** Freshness is decided by the consumer's clock against
    `valid_until` (§5.4). A `stale` status was a second, producer-side encoding of the
    same fact that could disagree with the first, and needed its own reason rule, two
    STRICT checks and special cases in the categorical and modality rules.
11. **`stated` is encoded once.** `status: stated` is authoritative; `stated://` and
    `external_provider` are conventions, not cross-field rules (§5.1.2).

Design decision recorded with draft 5:

12. **Coarsened scores are marked.** When a consumer receives a member only coarsely,
    the reading carries `resolution` with the band's bounds (§5.4.2). HSI already carries
    the outcome of a denial (`withheld`); a coarsened score is the outcome of a partial
    grant and needs the same visibility, or consumers read a band's representative value
    as a point estimate. The bounds, not a label vocabulary, are the contract, so
    producers keep their own band edges.

Scope decision recorded with draft 3: **environment** context lands in 1.4 as five
coarse `meta.context` fields (§7.2). A **work-state** domain (operational signals such as
corrections, ambiguity, context fragmentation and decision conflict) is deferred to a
separate RFC targeting 1.5. It needs member definitions and modality rules in the style
of RFC-HSI-0010, and adding a domain to the closed `axes` set requires its own schema
bump.

## Appendix A. Context field vocabularies

Closed vocabularies for the canonical `meta.context` fields. Producers MUST use these
values. A value that does not fit MUST NOT be forced into the nearest token; the field is
omitted instead.

| Field | Group | Values |
| --- | --- | --- |
| `activity` | activity | `still`, `walking`, `running`, `cycling`, `in_vehicle`, `exercising` |
| `work_context` | work | `focused_work`, `collaborative_work`, `meeting`, `communication`, `break`, `off_work` |
| `time_of_day` | time | `night`, `early_morning`, `morning`, `afternoon`, `evening` |
| `app_category` | work | `communication`, `productivity`, `development`, `browsing`, `media`, `social`, `gaming`, `other` |
| `focus_window` | work | boolean: inside a focus block the person set |
| `place_type` | environment | `home`, `workplace`, `transit`, `outdoors`, `public_indoor`, `other` |
| `air_quality_band` | environment | `good`, `moderate`, `poor`, `very_poor` |
| `noise_band` | environment | `quiet`, `moderate`, `loud` |
| `light_band` | environment | `dark`, `dim`, `normal`, `bright` |
| `temperature_band` | environment | `cold`, `cool`, `comfortable`, `warm`, `hot` |

Band thresholds (for example which particulate level counts as `poor`) are producer
policy in 1.4 and SHOULD be documented by the producer. `place_type` is a category only:
the producer MUST NOT emit it at a granularity that, combined with time, identifies a
specific place.

## Change log

- **Draft 5 (2026-11-09)** — Optional per-reading `resolution` (§5.4.2, §13 Q12): a
  score reported coarser than the producer's estimate names its band (`kind: band`,
  `lower`, `upper`, optional `label`). Forbidden on abstentions and categorical
  readings; `HSI-1.4-RESOLUTION-RANGE` added to STRICT; the 1.3 downgrade drops
  coarsened readings. One valid and five invalid examples.

- **Draft 4 (2026-10-20)** — Design review (§13 Q9–Q11): abstentions reduced to `name`,
  `status`, `reason`, `window_ids`, with no `score` or `confidence`; `stale` status
  removed in favour of the `valid_until` consumer rule; `stated://` and
  `external_provider` on stated readings made conventions rather than schema rules.
  `HSI-1.4-VALID-UNTIL-ORDER` and `HSI-1.4-STALE-NOT-EXPIRED` dropped. Schema
  conditionals reduced from nine to six; downgrade drops abstentions.

- **Draft 3 (2026-10-20)** — Open questions resolved (§13): `status` required on every
  reading; `confidence: null` allowed on `external_provider` readings; optional
  `baseline_version`; closed context vocabularies (Appendix A) with five new environment
  fields; `stated` readings enforced to use `stated://` and `external_provider`;
  `baseline_status` deprecation scheduled for 1.5; work-state domain deferred to 1.5.
  Schema, strict validator and examples added.
- **Draft 2** — `corrected` renamed `stated` and extended to standalone self-report;
  consent-controlled visibility of `withheld`; proposed resolutions for questions 1–4
  and 6; new questions 7 (provider confidence) and 8 (baseline versions).
- **Draft (2026-10-19)** — First draft. Per-reading `status` / `reason` / `basis` /
  `valid_until`; no silent omission; null score needs a status; `modalities_used` and
  categorical `label` relaxed for readings without an estimate; `meta.context` frame
  with observed / inferred / stated sources; `stated://` scheme; deprecation of
  `confidence_breakdown` per RFC-HSI-0011 §9.
