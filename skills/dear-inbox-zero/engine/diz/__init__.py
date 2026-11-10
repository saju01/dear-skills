"""dear-inbox-zero engine: deterministic classification, memory store, learning and reporting.

Standard library only. All commands take JSON files in and write JSON/Markdown out.
"""
__version__ = "0.1.0"
BUCKETS = ("noise", "fyi", "reply", "personal")
AUTONOMY_BUCKETS = ("noise", "fyi", "reply", "calendar")
MAX_LEVEL = {"noise": 2, "fyi": 2, "reply": 2, "calendar": 3}
FORBIDDEN_ACTIONS = ("send", "forward", "post", "delete", "move", "decline", "tentative")
CATEGORY = {"noise": "DIZ Noise", "fyi": "DIZ FYI", "reply": "DIZ Reply", "personal": "DIZ Personal"}
