## Security and Privacy

This repository defines a contract for exchanging human-state outputs. Producers and consumers MUST treat HSI payloads as **sensitive data**.

### Privacy-first constraints

- **No PII allowed**: Producers MUST NOT include personally identifying information in any field (including `meta`, `producer`, `sources`, or free-text `notes`).
- **Explicit assertion**: `privacy.contains_pii` MUST be `false`. If a producer cannot guarantee this, it MUST NOT emit HSI.
- **Data minimization**: Producers SHOULD emit only the fields required by consumers and SHOULD avoid free-text `notes` unless necessary.

### Embedding leakage risks

Embeddings can encode sensitive attributes implicitly (e.g., health, identity correlates, demographic proxies). If `embeddings` are used:

- Producers SHOULD treat embeddings as sensitive and restrict their distribution.
- Consumers SHOULD store embeddings only when required and SHOULD apply strict access control.
- Producers SHOULD provide `privacy.notes` describing any mitigation (e.g., differential privacy, clipping) if applicable.

### Transport and integrity

- **Confidential transport**: HSI payloads SHOULD be transmitted over authenticated, encrypted channels (e.g., TLS).
- **Signing**: Producers SHOULD sign payloads when integrity and provenance matter.
  - Signature format is out of scope for HSI; consumers MAY use JWS, SigV4-style, or equivalent mechanisms.
- **Replay protection**: Consumers SHOULD implement replay detection when payload freshness matters (e.g., using `generated_at` and consumer-side nonce tracking).

### Storage and retention

- Consumers SHOULD apply least-privilege access controls.
- Retention SHOULD be minimized according to product needs and legal constraints.
- Consumers SHOULD segregate HSI payload storage from identity systems to reduce linkage risk.

### Threat model notes (non-exhaustive)

- **Inference attacks**: Even if explicit PII is absent, human-state signals can be sensitive and linkable.
- **Cross-system correlation**: `producer.instance_id` and stable `meta` fields can become correlators. Producers SHOULD rotate identifiers when feasible.


