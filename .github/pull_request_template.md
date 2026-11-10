## What changes

<!-- One or two sentences. Link the issue: Fixes #… -->

## Checklist

- [ ] No personal data: fixtures use the fictional persona Alex and `example.com` / `.org` / `.net` only
- [ ] No operation that sends, forwards, posts, deletes, moves or declines
- [ ] Tests added or updated; `python -m unittest discover -s tests` passes in `skills/dear-inbox-zero`
- [ ] `python skills/dear-inbox-zero/engine/dear_engine.py doctor` passes (token budget, adapters)
- [ ] `python scripts/privacy_scan.py` passes
- [ ] `python scripts/build_manifest.py` run (install.json up to date)
- [ ] CHANGELOG updated if users will notice
