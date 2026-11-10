# AGENTS.md — instructions for AI agents

You are reading the `dear-skills` repository. It contains **skills**: folders with a `SKILL.md` in the open Agent Skills format.

## If a user asked you to install a skill from this repo

Follow [INSTALL.md](INSTALL.md) step by step. The machine-readable manifest is [install.json](install.json).

Hard rules while installing:
1. **Install first, then start setup.** Copying files never reads the user's mail, calendar or chats. After a successful install, start `dear-inbox-zero setup` straight away; its first step is the consent prompt, and nothing is read or stored before the user agrees.
2. **Verify, don't trust.** Check each file's sha256 against `install.json` before writing it. Stop if any hash differs.
3. **Ask once, only when needed.** Ask the user only for things you can't detect (for example which skills folder to use when several exist). One question, clear options.
4. **Never widen permissions.** Do not request send, post, delete or decline permissions for this skill. It never needs them.
5. **Report what you did:** the target folder, the files written, the adapter chosen and the `doctor` result, then continue into setup.
6. **Default automation is Auto · Medium** (see `skills/dear-inbox-zero/policy/buckets.md`). Schedule only what the user ticked in the consent prompt.

## If you are contributing to this repo

Read [CONTRIBUTING.md](CONTRIBUTING.md). No personal data, ever. Tests use the fictional persona "Alex" and `example.com` only.
