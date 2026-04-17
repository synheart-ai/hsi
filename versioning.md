## Versioning and Compatibility

HSI uses `MAJOR.MINOR` version numbers (patch versions are not used for payload compatibility; schema files MAY include patch in filenames if ever needed).

### Stability status

**HSI is pre-stable.** Until the first `2.0` release, minor versions MAY introduce breaking contract changes — renamed fields, removed required fields, narrowed types, or restructured shapes. Each minor bump ships as a new canonical schema file; older schemas are retained in this repository so historical payloads remain validatable.

During the pre-stable phase:

- Producers SHOULD target the latest minor.
- Consumers SHOULD validate each payload against the schema matching its declared `hsi_version`, not a hardcoded version.
- Producers and consumers SHOULD migrate across minors together; pinning both sides to a specific `hsi_version` is expected.

The stability regime in the next section begins when `2.0` is cut. Until then, that regime does not apply.

### Stability guarantees (from 2.0 onward)

Within a major version `N.x` where `N >= 2`:

- **Existing fields MUST NOT change meaning**.
- **Required fields MUST NOT be removed**.
- **Ranges and types MUST NOT be narrowed** in a way that invalidates previously valid payloads.
- **New fields MUST be optional** unless introduced under a new MAJOR.

### Semantic versioning rules

- **MAJOR**: breaking changes.
  - Consumers that support `N.x` MUST reject payloads with `hsi_version` `(N+1).0` or higher unless explicitly updated to support that major.
- **MINOR**: during pre-stable (`1.x`), MAY include breaking changes — see "Stability status". From `2.0` onward, MINOR bumps are backward-compatible additions or clarifications only.
  - In the post-`2.0` regime, producers MAY emit new optional fields in a minor release, and consumers MUST accept payloads that conform to the schema for the supported major version.

### Deprecation policy (post-2.0)

- A field MAY be deprecated in documentation within a major version.
- Deprecation MUST NOT make previously valid payloads invalid within the same major.
- Removed fields require a MAJOR version increment.

### Unknown fields and axes

HSI consumers MUST follow these rules:

- **Top-level unknown fields**: MUST be rejected for strict validation against the published schema (`additionalProperties: false`).
- **Unknown axis names** within a known domain (e.g., a new string `name` inside `axes.physiological`): MUST be tolerated.
  - Consumers MAY ignore unknown axis names.
  - Consumers MUST NOT treat unknown axis names as schema violations.
- **Unknown axis domains** (a new top-level key under `axes` that the schema does not declare): are rejected by the schema's `additionalProperties: false` on the axes object. Adding a domain requires a schema update and a version bump.

### Producer guidance

- Producers MUST set `hsi_version` to the contract version they claim to implement.
- Producers SHOULD avoid emitting fields not defined in the schema for that version.
