# Architecture

`piper-tts-server` is as small as it looks: one FastAPI process, one endpoint, one voice model
baked into the image. There's no state, no database, no config beyond the port — the only
non-obvious decision is *how* the voice model gets into the container, covered in
[ADR-0001](./adr/0001-bake-voice-model-at-build-time.md).

## Components

| Component | Role | Source |
|---|---|---|
| FastAPI app | `POST /tts`, `GET /healthz` | `app/main.py` |
| `piper-tts` (Python library) | Actual speech synthesis, CPU-only | `requirements.txt`, called via `PiperVoice.load()` |
| `fr_FR-siwis-medium` voice | The one voice this server can speak | baked into the image at build time, see ADR-0001 |
| ArgoCD + GHCR | Builds, publishes, and deploys this app on every push to `main` | `.github/workflows/docker-publish.yml`, `k8s/` |

This repo doesn't own the cluster/ArgoCD/MetalLB layer its Service runs on — see
[`gitops-homelab`'s architecture.md](https://github.com/koydas/gitops-homelab/blob/main/docs/architecture.md)
and that repo's [ADR-0016](https://github.com/koydas/gitops-homelab/blob/main/docs/adr/0016-onboard-whisper-piper-cpu-only.md)
(why this app exists, why CPU-only, why a custom wrapper instead of an off-the-shelf image).
The two real production callers are
[`homelab-gateway`](https://github.com/koydas/homelab-gateway) (routes `/tts`-shaped requests
here, see that repo's `docs/architecture.md`) and, through it,
[`ollama-chat`](https://github.com/koydas/ollama-chat)'s vocal mode (see that repo's
`docs/architecture.md` for the STT→chat→TTS round-trip this server is one leg of).

## Request flow

```mermaid
sequenceDiagram
    participant C as Caller<br/>(homelab-gateway, or direct)
    participant A as FastAPI app
    participant P as PiperVoice<br/>(in-process, CPU)

    C->>A: POST /tts { "text": "..." }
    A->>P: synthesize_wav(text, wav_file)
    Note over P: CPU-bound synthesis,<br/>no GPU, no network call
    P-->>A: WAV bytes written to an in-memory buffer
    A-->>C: 200, audio/wav
```

There's no streaming, no chunking, and no queueing — one request holds the process until
synthesis finishes and the full WAV buffer is returned. Given the resource limits in
`k8s/deployment.yaml` (2 CPU / 1Gi limit, single replica), a second request arriving mid-
synthesis queues behind FastAPI's own request handling rather than failing outright, but
there's no explicit backpressure or timeout configured here — a very long piece of text is the
only way this would become a real problem in practice.

## Voice model: baked in, not downloaded at runtime

```mermaid
flowchart LR
    subgraph "Docker build (multi-stage)"
        S1["Stage 'voices':<br/>pip install piper-tts<br/>python -m piper.download_voices<br/>fr_FR-siwis-medium"]
        S2["Final stage:<br/>COPY --from=voices /voices /models"]
    end
    S1 --> S2
    S2 --> I["Image: ghcr.io/koydas/piper-tts-server:&lt;sha&gt;<br/>/models/fr_FR-siwis-medium.onnx already present"]
    I --> R["Pod starts: PiperVoice.load(MODEL_PATH)<br/>no network call, no volume mount"]
```

See [ADR-0001](./adr/0001-bake-voice-model-at-build-time.md) for why this is baked in at build
time (a separate Docker build stage) instead of downloaded on pod start or mounted from a PVC.

## Deployment pipeline

```mermaid
flowchart TD
    A[git push to main] --> B{Touches only<br/>k8s/**, docs/**, **.md?}
    B -- yes --> Z[docker-publish workflow<br/>does not run]
    B -- no --> C[docker-publish.yml:<br/>build image, incl. voice-download stage]
    C --> D["push ghcr.io/koydas/piper-tts-server:&lt;sha&gt;"]
    D --> E[workflow commits new tag<br/>into k8s/deployment.yaml]
    E --> F[push commit to main]
    F --> G[ArgoCD polls / gets refreshed]
    G --> H[Applies k8s/ manifests]
    H --> I[New pod pulls the new tag<br/>old pod terminates]
```

Same three-step "build → tag-rewrite commit → ArgoCD sync" shape as this app's siblings
(`homelab-gateway`, `ollama-chat`) — see either of those repos' `docs/architecture.md` for the
general mechanics (`paths-ignore`, why the tag-rewrite commit doesn't re-trigger itself, and a
real race between ArgoCD's poll-sync and the tag-rewrite commit that's been hit in practice).
Unlike those two, this repo has no test suite yet, so nothing currently gates the build beyond
CI's implicit "did the Docker image build at all."

## Runtime topology

```mermaid
flowchart TB
    subgraph Caller
        Gateway["homelab-gateway pod"]
        Dev["Local dev<br/>(Vite proxy, direct)"]
    end
    subgraph "microk8s cluster"
        subgraph "piper namespace"
            Pod["piper pod<br/>FastAPI :8000<br/>CPU-only"]
        end
        SvcLB["Service (LoadBalancer)<br/>192.168.1.246:8000"]
    end
    Gateway -->|in-cluster:<br/>piper.piper.svc.cluster.local:8000| Pod
    Dev -->|LAN IP, no /etc/hosts needed| SvcLB --> Pod
```

`192.168.1.246` is a dedicated MetalLB IP — not for production traffic (which reaches this pod
in-cluster, via `homelab-gateway`), but so `ollama-chat`'s local Vite dev server can call this
service directly without any backend running, the same way it already does for Ollama and
Whisper. See `gitops-homelab`'s ADR-0016 for the full reasoning on why every voice/STT backend
here got its own LAN-reachable IP.
