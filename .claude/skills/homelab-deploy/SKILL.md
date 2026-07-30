---
name: homelab-deploy
description: Deploy/verify workflow for piper-tts-server — pushing to main and confirming a rollout actually landed. No test suite exists yet, so nothing gates the build besides "did the Docker image build at all."
---

# homelab-deploy

## When to Apply

Any time you push a commit to `main` in this repo and expect the live service at
`192.168.1.246:8000` (direct, dev) or via `homelab-gateway` (production) to reflect it.

## Expected Behavior

### Pushing to main: expect a rejected push, it's not an error

`.github/workflows/docker-publish.yml` builds the image on every push to `main` that isn't
docs-only (`k8s/**`, `docs/**`, `**.md` are ignored) and **commits the new tag back into
`k8s/deployment.yaml` on `main`**. If that workflow's commit lands between your last
`git fetch` and your `git push`, the push is rejected with `! [rejected] main -> main (fetch
first)`. Resolve it the same way every time:

```bash
git fetch origin
git log --oneline main..origin/main   # sanity check: should only be a "chore: deploy <sha>" commit
git pull --rebase origin main
git push origin main
```

### No test gate — verify manually before pushing anything nontrivial

Unlike `homelab-gateway`/`ollama-chat`, this repo has no automated test suite, so
`docker-publish.yml` will happily build and deploy broken code — CI only proves the Docker
image built, not that `/tts` actually works. Before pushing a change to `app/main.py`, run it
locally:

```bash
pip install -r requirements.txt
python -m piper.download_voices fr_FR-siwis-medium --data-dir /tmp/piper-voices  # once
MODEL_PATH=/tmp/piper-voices/fr_FR-siwis-medium.onnx uvicorn app.main:app --port 8000 &
curl -s -X POST http://localhost:8000/tts -H "Content-Type: application/json" \
  -d '{"text":"bonjour"}' -o /tmp/test.wav -w "%{http_code}\n"
file /tmp/test.wav   # should say "WAVE audio"
```

(`app/main.py` hardcodes `MODEL_PATH = "/models/fr_FR-siwis-medium.onnx"` — override via env
if that constant hasn't been made configurable yet, or point the download at that exact path.)

### Confirming the build actually ran

```bash
gh run list --limit 1
```

Wait for `status: completed` / `conclusion: success` before assuming the image exists in
GHCR.

### Getting ArgoCD to pick it up now, not in ~3 minutes

```bash
sudo microk8s kubectl -n argocd annotate application piper argocd.argoproj.io/refresh=hard --overwrite
sudo microk8s kubectl -n argocd get application piper -o custom-columns=SYNC:.status.sync.status,HEALTH:.status.health.status
```

Same class of race as `homelab-gateway` has documented (ArgoCD grabbing the code-push commit
before CI's tag-rewrite commit lands) is possible here too, even though it hasn't been
specifically hit on this repo yet — don't trust the first "Synced" status alone; compare the
pod's actual image tag against the latest commit on `origin/main`:

```bash
git log origin/main -1 --oneline
sudo microk8s kubectl get pod -n piper -l app=piper -o jsonpath='{.spec.containers[0].image}'
```

### Confirming the pod actually rolled out

```bash
sudo microk8s kubectl get pods -n piper -o wide
curl -s -X POST http://192.168.1.246:8000/tts -H "Content-Type: application/json" -d '{"text":"test"}' -o /tmp/test.wav -w "%{http_code}\n"
```

## Constraints

- `kubectl` is not installed bare — always `sudo microk8s kubectl`.
- Don't force-push or reset to work around the rejected-push case — always rebase onto the CI
  commit.
- Don't assume a push deployed just because `git push` succeeded — check the CI run, then the
  pod's actual image tag, then a real `/tts` call, in that order.

## References

- `docs/deployment.md` — the pipeline diagram
- `docs/adr/0001-bake-voice-model-at-build-time.md` — why the voice is baked into the image
  rather than downloaded/mounted at runtime
- `.github/workflows/docker-publish.yml` — exact trigger/paths-ignore rules
