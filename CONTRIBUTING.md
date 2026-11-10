# Contributing

Thanks for helping make dear-skills better.

## The one hard rule: no personal data

Skills in this repo are recipes. They are customised per user at first install and keep their memory in the user's own storage.

- Never commit real names, email addresses, phone numbers, customer or company names, mail subjects, chat text or calendar entries.
- Tests and examples use the fictional persona **Alex** and `example.com` / `example.org` domains only.
- Never commit a user's store (`head/`, `store/`, `index.json`). These paths are in `.gitignore`.
- CI runs a personal-data scan and fails the build on any hit.

## How to contribute

1. Open an issue describing the change, or pick an existing one.
2. Keep changes small and include tests on synthetic fixtures.
3. Respect the token budget in [DESIGN.md](DESIGN.md#10-token-budget). CI checks file sizes.
4. Never add an operation that sends, forwards, posts, deletes or declines. See [DESIGN.md §9](DESIGN.md#9-safety-guarantees-enforced-in-engine-and-host-mapping).

## Licence of contributions

By submitting a pull request you agree that your contribution is licensed under the [Apache License 2.0](LICENSE) (section 5 of the licence), the same as the rest of the project.

## Adding an agent (host adapter)

Copy `skills/dear-inbox-zero/hosts/_template.md`, map every abstract operation to your agent's tools, expose none of the forbidden ones, and include the `doctor` output in your pull request.

## How changes land

- `main` is protected: changes arrive through pull requests, and the checks (tests on Python 3.10 and 3.12, privacy scan, doctor, manifest) must pass. @saju01 reviews every change (CODEOWNERS).
- The same checks also run every Monday, so breakage from newer Python versions shows up early.

## Releasing (maintainers)

1. Bump `version` in `skills/dear-inbox-zero/SKILL.md` and `install.json`, add a CHANGELOG entry, then run `python scripts/build_release.py` and `python scripts/build_manifest.py`.
2. Merge to `main`, then push a tag `vX.Y.Z` matching the version.
3. The `release` workflow runs every check, builds `dear-inbox-zero-vX.Y.Z.zip` with its `.sha256`, and attaches both to the GitHub release.
4. Before tagging, run the new version for a day in a real mailbox (dry run first).
