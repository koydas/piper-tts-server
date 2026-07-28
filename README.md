# piper-tts-server

A tiny FastAPI wrapper around [Piper](https://github.com/OHF-Voice/piper1-gpl) (`piper-tts` on
PyPI) exposing text-to-speech as a plain REST endpoint, CPU-only. Built to be called by
[`ollama-chat`](https://github.com/koydas/ollama-chat)'s vocal mode, the way that app already
calls Ollama for chat.

## API

- `POST /tts` — JSON body `{"text": "..."}`, response is raw `audio/wav` bytes.
- `GET /healthz` — `{"status": "ok"}`.

## Voice

Bundled at build time (baked into the image, no runtime network dependency):
`fr_FR-siwis-medium` (French).

## Deployment

Runs on the homelab microk8s cluster via ArgoCD, onboarded as a git-source Application in
[`koydas/gitops-homelab`](https://github.com/koydas/gitops-homelab) (`apps/piper/application.yaml`),
which points at this repo's `k8s/` directory as its source — same pattern as `ollama-chat`
itself. See that repo's ADR-0016 for why (CPU-only, split from Whisper's raw-manifest
onboarding).

On every push to `main` (that isn't docs-only), `.github/workflows/docker-publish.yml` builds
the image, pushes it to `ghcr.io/koydas/piper-tts-server:<sha>`, and commits the new tag into
`k8s/deployment.yaml` — that commit is what ArgoCD syncs on.
