"""dear-inbox-zero engine: deterministic classification, memory store, learning and reporting.

Standard library only. All commands take JSON files in and write JSON/Markdown out.
"""
__version__ = "0.1.0"
BUCKETS = ("noise", "fyi", "reply", "personal")
AUTONOMY_BUCKETS = ("noise", "fyi", "reply", "calendar")
MAX_LEVEL = {"noise": 2, "fyi": 2, "reply": 2, "calendar": 3}
FORBIDDEN_ACTIONS = ("send", "forward", "post", "delete", "move", "decline", "tentative")
CATEGORY = {"noise": "DIZ Noise", "fyi": "DIZ FYI", "reply": "DIZ Reply", "personal": "DIZ Personal"}

# Automation presets: starting level and ceiling per bucket. Earned promotion and demotion still apply
# inside the ceiling. Sending, forwarding, posting, deleting and declining are never on the ladder.
PRESETS = {
    "low":    {"start": {"noise": 1, "fyi": 1, "reply": 1, "calendar": 1},
               "cap":   {"noise": 1, "fyi": 1, "reply": 1, "calendar": 1}},
    "medium": {"start": {"noise": 2, "fyi": 2, "reply": 2, "calendar": 1},
               "cap":   {"noise": 2, "fyi": 2, "reply": 2, "calendar": 3}},
    "high":   {"start": {"noise": 2, "fyi": 2, "reply": 2, "calendar": 3},
               "cap":   {"noise": 2, "fyi": 2, "reply": 2, "calendar": 3}},
}
DEFAULT_PRESET = "medium"
# Accepting an invite sends the organiser a response: the one action that reaches another person. It is a separate
# opt-in (profile.invite_accept), off by default at every preset; without it the engine asks instead of accepting.
