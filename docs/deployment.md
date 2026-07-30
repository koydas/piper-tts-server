# Deployment pipeline

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
(`homelab-gateway`, `ollama-chat`) — see either of those repos' `docs/deployment.md` for the
general mechanics (`paths-ignore`, why the tag-rewrite commit doesn't re-trigger itself, and a
real race between ArgoCD's poll-sync and the tag-rewrite commit that's been hit in practice).
Unlike those two, this repo has no test suite yet, so nothing currently gates the build beyond
CI's implicit "did the Docker image build at all."
