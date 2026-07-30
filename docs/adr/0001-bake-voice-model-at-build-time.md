# ADR-0001: Bake the voice model into the image at build time

- **Date:** 2026-07-29 (written retroactively — this was the original design from this repo's
  first commit; recorded now as part of a broader documentation pass across the homelab repos)
- **Status:** Accepted

## Context

`piper-tts` needs a voice model file (`fr_FR-siwis-medium.onnx` and its config) to synthesize
anything. That file has to come from somewhere before `PiperVoice.load()` can run — either
downloaded at container startup, mounted from a persistent volume populated some other way, or
baked directly into the Docker image.

## Decision

The `Dockerfile` uses a multi-stage build: a `voices` stage installs `piper-tts` just to run
`python -m piper.download_voices fr_FR-siwis-medium --data-dir /voices`, and the final stage
`COPY --from=voices /voices /models` — the model file is already sitting in the image by the
time the container ever starts. `app/main.py` loads it from a hardcoded path
(`MODEL_PATH = "/models/fr_FR-siwis-medium.onnx"`), with `use_cuda=False`.

No PVC, no init container, no runtime `download_voices` call, no volume mount anywhere in
`k8s/deployment.yaml`.

## Alternatives Considered

### Download the voice on pod startup
Rejected: adds a runtime network dependency (this server would fail to start if the voice
download host is unreachable, which has nothing to do with whether the cluster or this app is
actually healthy), and adds startup latency to every pod restart/rollout for no benefit — the
voice never changes at runtime.

### Mount the voice from a PVC, populated once out-of-band
Rejected: this is the pattern Ollama uses for its (much larger, frequently-changing) model
weights, and it's the right trade-off there — but a single Piper voice is a few tens of MB and
never changes independently of the code that uses it. A PVC would add a stateful volume, a
population step, and a "what if the PVC is empty/lost" failure mode to a service that has zero
other state, for a file that's small enough to just ship with the image.

### Support multiple voices, selectable per request
Not implemented: `TTSRequest` only carries `text`, and the model path is a single hardcoded
constant. Out of scope for the one caller this server has today (`ollama-chat`'s French-only
vocal mode) — revisit if a second language/voice is ever actually needed.

## Consequences

**Good:**
- Zero runtime network dependency and zero additional Kubernetes resources (no PVC, no init
  container) — the entire deployment is a single stateless `Deployment` + `Service`.
- A pod restart or rollout never re-downloads anything; cold start is exactly "process boot +
  `PiperVoice.load()` from local disk."

**Neutral:**
- Changing the voice means changing the `Dockerfile` and rebuilding the image, not a config
  change — appropriate here since there's only ever been one voice and no runtime selection
  mechanism.

**Negative:**
- ⚠️ The image is larger than it would be without a bundled model (the voice file ships in
  every image, every tag, forever, since there's no shared/cached layer for it across
  versions unless the base layers are otherwise unchanged).
- ⚠️ Adding a second voice/language means a Dockerfile change and a full rebuild, not a
  runtime config flip — acceptable today given there's exactly one caller and one language in
  use, but worth revisiting if that changes.
