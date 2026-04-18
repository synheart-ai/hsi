# RFC-HSI-0009

## HSI 1.3 — Optional payload integrity block

- **Status**: Draft
- **Type**: Minor (additive on 1.2)
- **Target**: HSI 1.3
- **Owner**: HSI Maintainers
- **Relates to**: RFC-HSI-0008 (HSI 1.2 canonical contract)

## 1. Purpose

Research-grade HSI deployments need reproducible, verifiable payload integrity:

- Consumers want to verify a payload has not been tampered with in transit or storage.
- Auditors want to pin a specific payload to a specific producer run without re-executing the pipeline.
- Cross-producer comparison requires a stable content identifier independent of JSON key ordering or whitespace.

HSI 1.2 (RFC-HSI-0008 §8, §13) already references RFC 8785 (JSON Canonicalization Scheme) for canonicalizing embedding content before hashing `vector_hash`. This RFC extends that pattern to the payload as a whole.

HSI 1.3 adds an OPTIONAL top-level `integrity` object for payload-level content hashing and (optionally) signing. The field is fully backward-compatible: consumers that ignore it continue to work, and producers that do not need integrity never set it.

## 2. Non-goals

- **Transport-layer security**: use TLS. Out of scope here.
- **Consent and authorization**: live in `privacy` and producer-side policy.
- **Key lifecycle** (issuance, rotation, revocation): outside HSI's contract surface.
- **Replay protection**: see `SECURITY.md` — use `computed_at_utc` plus consumer-side nonce tracking.
- **Encryption of payload content**: HSI payloads are privacy-bounded but not encrypted; end-to-end encryption is a separate concern.

## 3. Schema additions

Add an OPTIONAL top-level `integrity` object:

```json
"integrity": {
  "canonicalization": "jcs/rfc8785-v1",
  "content_hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "signature": {
    "algorithm": "ed25519",
    "key_id": "did:example:producer#key-1",
    "value": "base64url:MEUCIQD..."
  }
}
```

### 3.1 Required fields (when `integrity` is present)

- `canonicalization` (string, enum): the canonicalization method used before hashing. Reserved values:
  - `jcs/rfc8785-v1` — RFC 8785 JSON Canonicalization Scheme, applied to the payload with the `integrity` block removed.
- `content_hash` (string, pattern `^sha256:[0-9a-f]{64}$`): hash of the canonicalized payload (excluding the `integrity` block itself), lowercase hex.

### 3.2 Optional fields

- `signature` (object): detached signature over the UTF-8 bytes of `content_hash`.
  - `algorithm` (string, enum): `ed25519`, `ecdsa-p256-sha256`, `rsa-pss-sha256`.
  - `key_id` (string): URI or DID identifying the signing key. SHOULD be resolvable out-of-band or pinned in a producer trust policy.
  - `value` (string): prefixed signature bytes, e.g. `base64url:<...>`.

The schema MUST apply `additionalProperties: false` to `integrity` and to `signature`.

## 4. Hashing rules

To produce `integrity.content_hash`:

1. Take the full HSI payload object.
2. Remove the `integrity` field (if present) from the object.
3. Canonicalize the remaining object per the declared `canonicalization` method (`jcs/rfc8785-v1` = RFC 8785).
4. Compute SHA-256 over the canonicalized UTF-8 bytes.
5. Format as `sha256:` followed by 64 lowercase hex characters.

To verify:

1. Read `integrity` from the payload.
2. Remove the `integrity` field from the object.
3. Canonicalize and hash as above.
4. Compare the recomputed hash to `content_hash`. It MUST match byte-for-byte.

Producers MUST NOT include the `integrity` block in the canonicalized input. A self-referential hash is not computable.

## 5. Signature rules

If `signature` is present, `signature.value` MUST be a detached signature over the ASCII/UTF-8 bytes of `content_hash` (the full `sha256:<hex>` string, not the decoded hash bytes) using `signature.algorithm` and the key identified by `signature.key_id`.

Consumers verifying `signature`:

1. Verify `content_hash` matches the payload (§4).
2. Resolve `signature.key_id` to a public key via out-of-band trust (DID resolution, pinned producer registry, JWKS endpoint, etc.).
3. Verify the signature over `content_hash`.

The signed artifact is deliberately `content_hash` and not the canonicalized payload directly: consumers can hash once and reuse the result for both tamper-detection and signature verification, and the signer never needs to re-canonicalize.

## 6. Privacy considerations

- The `integrity` block reveals that the producer emitted *some* payload with a specific content hash. Consumers retaining hashes can detect replay and duplication without access to payload bodies. Generally desirable, but worth noting for threat-model documentation.
- `signature.key_id` is an identifier. It is not PII but MAY be producer-correlating if chosen carelessly. Producers SHOULD rotate signing keys on a cadence consistent with `producer.instance_id` rotation (see `SECURITY.md`).
- Integrity does not protect against a compromised producer; it only binds a payload to whoever holds the signing key. Trust in that key is out-of-band.

## 7. Compliance

- **HSI-VALIDATE-BASIC**: schema-level only; does not verify hashes or signatures.
- **HSI-VALIDATE-STRICT**: MAY add an optional check — if `integrity.content_hash` is present, strict validation SHOULD recompute and compare. Gated behind a strict-mode flag since it requires a canonicalization library.
- **HSI-VALIDATE-INTEGRITY** (new tier): verifies `content_hash` (and `signature`, if present) with a working canonicalizer and trust policy. Consumers requiring tamper-evidence SHOULD target this tier.

## 8. Migration

- HSI 1.2 producers: no change required.
- HSI 1.3 producers that want verifiable integrity: set `hsi_version: "1.3"` and populate `integrity`.
- Consumers: accept both 1.2 and 1.3 payloads; fall back to BASIC/STRICT without integrity when the block is absent.

## 9. Open questions

Before promoting this RFC to Accepted:

- **Canonicalization set**: reserve only `jcs/rfc8785-v1` for now, or leave the enum open for future methods (e.g., CBOR-based)? JCS is the front-runner.
- **Multi-signature**: should `signature` accept an array of objects to support co-signed payloads (producer + aggregator)?
- **Hash agility**: `sha256` only, or reserve `sha512` / `blake3` now via algorithm-prefixed hash values?
- **Inline key material**: should `signature` permit a `kty`/JWK-inline form for self-contained payloads, or strictly require out-of-band resolution of `key_id`?
- **Strict mode default**: should `HSI-VALIDATE-STRICT` recompute `content_hash` by default when present, or only when explicitly enabled?

## 10. Canonical schema

When this RFC is accepted, the `integrity` block will be added to `schema/hsi-1.3.schema.json`. No changes to `schema/hsi-1.2.schema.json` are required; 1.2 payloads remain valid and MAY continue to be emitted in parallel.
