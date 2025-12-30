## Versioning and Compatibility

HSI uses **Semantic Versioning**: `MAJOR.MINOR` (patch versions are not used for payload compatibility; schema files MAY include patch in filenames if ever needed).

### Semantic versioning rules

- **MAJOR**: breaking changes.
  - Consumers that support `1.x` MUST reject payloads with `hsi_version` `2.0` or higher unless explicitly updated to support that major.
- **MINOR**: backward-compatible additions or clarifications.
  - Producers MAY emit new optional fields in a minor release.
  - Consumers MUST accept payloads that conform to the schema for the supported major version.

### Backward compatibility guarantees (within a major)

Within `1.x`:

- **Existing fields MUST NOT change meaning**.
- **Required fields MUST NOT be removed**.
- **Ranges and types MUST NOT be narrowed** in a way that invalidates previously valid payloads.
- **New fields MUST be optional** unless introduced under a new MAJOR.

### Deprecation policy

- A field MAY be deprecated in documentation within a major version.
- Deprecation MUST NOT make previously valid payloads invalid within the same major.
- Removed fields require a MAJOR version increment.

### Unknown fields

HSI consumers MUST follow these rules:

- **Top-level unknown fields**: MUST be rejected for strict validation against the published schema (`additionalProperties: false`).
- **Unknown axes** (`axis` values): MUST be tolerated.
  - Consumers MAY ignore unknown axes.
  - Consumers MUST NOT treat unknown axes as schema violations.

### Producer guidance

- Producers MUST set `hsi_version` to the contract version they claim to implement.
- Producers SHOULD avoid emitting fields not defined in the schema for that version.


