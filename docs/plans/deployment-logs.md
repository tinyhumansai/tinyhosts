# Implement deployment-event retrieval

Linked specification: [`../specs/unified-hosting-api.md`](../specs/unified-hosting-api.md)

## Goal

Expose a provider-independent, chronological view of deployment build and
deployment events through `Host` and the JSON RPC surface.

## Non-goals

Runtime invocation logs are not deployment events and remain outside this API.
The API neither parses provider event kinds into a closed enum nor returns
secret values.

1. Add `DeploymentLog` and `Host::deployment_logs`, with JSON round-trip tests
   in `src/host/test.rs`; re-export it from `src/lib.rs`.
2. Implement the Vercel adapter in `src/providers/vercel/`. First test Vercel's
   nullable top-level event array, including ignored null entries, then decode it
   and preserve kind, timestamp, and payload text.
3. Add the `deployment_logs` RPC operation and outcome in `src/rpc/mod.rs`, with
   serialization and dispatch coverage.
4. Document the capability and Vercel endpoint in the unified specification,
   then run the repository validation and coverage contracts.
