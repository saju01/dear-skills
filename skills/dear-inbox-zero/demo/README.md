# Demo data (fictional)

A morning for Alex, a fictional user, used by `python engine/dear_engine.py quickstart`. Every address is on `example.com`, `example.org` or `example.net`.

- `observations.json`: what a Sent-box and behaviour study might have seen (`learn.study`).
- `answers.json`: calibration answers: rules Alex confirmed, a VIP and a personal sender.
- `items.json`: normalized mail, invites and one Teams chat, as the collectors produce them.
- `calendar.json`: an event already on Alex's calendar, so one invite clashes.

`quickstart` runs setup and one daily run with `--dry-run` semantics: it plans no action and writes only to the folder it's given.
