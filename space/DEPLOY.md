# Deploying the replay Space

Three steps, once:

1. On huggingface.co: **New Space** → SDK **Docker** → name it (e.g.
   `steeropathy`). Free CPU tier is enough — the Space replays saved runs,
   no model runs anywhere.
2. Put the two files from this folder in the Space repo root:
   `README.md` (the Space card) and `Dockerfile`.
3. Push. The build clones this GitHub repo, so the Space tracks `main` —
   to pick up new commits, hit **Factory rebuild** (Space settings), or
   push any commit to the Space repo.

Local dry-run of exactly what the Space will run:

```bash
docker build -t steeropathy-space space/
docker run -p 7860:7860 steeropathy-space
# → http://localhost:7860#zomb-replay
```
