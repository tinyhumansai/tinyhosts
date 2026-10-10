# tinyhosts-bus

The minimal vocabulary for callers of the compiled TinyHosts module. Dependencies
are restricted to serde, JSON serialization, and error derives; no feature links
a provider, TinyBus transport, HTTP client, filesystem collector, or runtime.

`Execute(String) -> String` accepts the existing JSON request and returns the
existing tagged result envelope. `Providers() -> String` returns provider slugs.
Request and Operation have generic input slots so the library retains its
validated Bundle and LaunchPlan APIs while hosts use `DeploymentInput` and
`LaunchInput` DTOs. File contents remain standard-base64 strings on the wire;
encoding, path validation, collection, and execution remain implementation work.
Requests and credential inputs are deserialize-only, with redacted Debug output.

Shared hosting records, errors, schemas, result envelopes, and recorded tool
declarations are re-exported by the implementation for compatibility. Host
approval, authorized workspace selection, credential custody, and lifecycle
policy stay with OpenHuman. The module validates inputs and talks to providers.
The package version follows the module release version; the release workflow
bumps both manifests together. Hosts pin published artifacts and verify digests.
