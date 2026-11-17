"""Offline Graph collectors on synthetic metadata only."""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "engine"))
from diz import collect, sent, classify
from diz.util import load, parse_ts
from test_cli import run

FIXTURES = os.path.join(HERE, "fixtures", "graph")
PROFILE = {"internal_domains": ["EXAMPLE.COM"], "tz": "UTC"}
NOW = parse_ts("2026-03-02T14:00:00Z")


def fixture(name):
    return load(os.path.join(FIXTURES, name + ".json"))


class MailTests(unittest.TestCase):
    def test_metadata_and_recipients(self):
        direct, cc = collect.mail(fixture("messages"), "alex@example.com")
        self.assertEqual((direct["sender"], direct["sender_domain"], direct["sender_name"]),
                         ("contact@example.org", "example.org", "Alex"))
        self.assertEqual((direct["thread_id"], direct["received_at"]),
                         ("conversation-1", "2026-03-02T09:00:00Z"))
        self.assertTrue(direct["to_me"])
        self.assertFalse(direct["cc_only"])  # To takes precedence over CC.
        self.assertFalse(direct["is_read"])
        self.assertTrue(direct["flagged"])
        self.assertEqual(direct["categories"], ["Existing"])
        self.assertEqual(direct["importance"], "high")
        self.assertFalse(direct["other_tab"])
        self.assertFalse(cc["to_me"])
        self.assertTrue(cc["cc_only"])
        self.assertTrue(cc["other_tab"])
        self.assertTrue(cc["is_read"])
        self.assertFalse(cc["flagged"])
        self.assertFalse(cc["has_question"])
        self.assertEqual(cc["deadline_hint"], "")
        self.assertNotIn("bodyPreview", direct)

    def test_questions_and_asks_in_five_languages(self):
        for preview in ["Ready?", "Could you review this", "Kun je dit nakijken",
                        "Könnten Sie dies prüfen", "Pouvez-vous vérifier", "Por favor revisa esto"]:
            with self.subTest(preview=preview):
                row = {"id": "ask", "bodyPreview": preview}
                self.assertTrue(collect.mail(row, "alex@example.com")[0]["has_question"])
        for preview in ["An update.", "The appliance is ready.", None]:
            self.assertFalse(collect.mail({"id": "plain", "bodyPreview": preview}, "alex@example.com")[0]["has_question"])

    def test_deadlines_in_five_languages(self):
        for text, expected in [("Review by Friday", "by friday"), ("Graag uiterlijk vrijdag", "uiterlijk"),
                               ("Bitte bis Freitag", "bis"), ("Merci avant demain", "avant"),
                               ("Antes de mañana", "antes de"), ("Due 2026-03-03", "due"),
                               ("Complete 2026-03-03", "2026-03-03")]:
            with self.subTest(text=text):
                self.assertEqual(collect.mail({"id": "deadline", "bodyPreview": text}, "")[0]["deadline_hint"], expected)

    def test_missing_optional_fields_and_not_a_recipient(self):
        item = collect.mail({"id": "minimal", "from": {"emailAddress": None}}, "alex@example.com")[0]
        for key in ("to_me", "cc_only", "has_question", "flagged", "other_tab", "is_invite"):
            self.assertFalse(item[key])
        self.assertEqual(item["categories"], [])
        self.assertEqual(item["importance"], "normal")

    def test_invite_type(self):
        item = collect.mail({"id": "invite", "@odata.type": "#microsoft.graph.eventMessageRequest"}, "")[0]
        self.assertTrue(item["is_invite"])

    def test_incomplete_invite_cannot_bypass_clash_checks(self):
        message = {"id": "invite-mail", "@odata.type": "#microsoft.graph.eventMessageRequest",
                   "from": {"emailAddress": {"address": "organizer@example.com"}}}
        state = {"head": {"profile": PROFILE, "autonomy": {"calendar": {"level": 3}}},
                 "facts": [{"id": "accept-rule", "kind": "rule", "scope": "sender",
                            "key": "organizer@example.com", "bucket": "accept", "origin": "explicit"}]}
        for event_patch in [None, {"id": "event", "start": "2026-03-03T10:00:00Z"},
                            {"start": "2026-03-03T10:00:00Z", "end": "2026-03-03T11:00:00Z"}]:
            item = collect.mail(message, "alex@example.com")[0]
            item.update(event_patch or {})
            decision = classify.classify(state, [item])["decisions"][0]
            self.assertEqual(decision["recommendation"], "ask")
            self.assertFalse(any(a["op"] == "accept" for a in decision["actions"]))
        message["event"] = fixture("calendarView")["value"][0]
        item = collect.mail(message, "alex@example.com", PROFILE)[0]
        self.assertEqual(item["id"], "invite-mail")
        self.assertEqual(item["event_id"], "event-external")
        blocker = {**item, "event_id": "other-event", "my_response": "accepted"}
        decision = classify.classify(state, [item], [blocker])["decisions"][0]
        self.assertEqual(decision["reason"], "clash")
        self.assertEqual([a["op"] for a in decision["actions"]], ["flag"])
        self.assertEqual(classify.classify(state, [item])["decisions"][0]["recommendation"], "ask")
        state["head"]["profile"] = {**PROFILE, "invite_accept": True}
        self.assertEqual(classify.classify(state, [item])["decisions"][0]["recommendation"], "accept")

    def test_pages_arrays_empty_and_errors(self):
        raw = fixture("messages")
        self.assertEqual(len(collect.mail([raw, {"value": [{"id": "page-2"}]}], "")), 3)
        self.assertEqual(collect.mail({"value": []}, ""), [])
        self.assertEqual(collect.mail([], ""), [])
        for bad in [{"error": {"code": "Denied"}}, {"value": None}, "bad", {}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                collect.mail(bad, "")


class SentTests(unittest.TestCase):
    def test_metadata_and_reply_latency(self):
        received = collect.mail(fixture("messages"), "alex@example.com")
        reply, new = collect.sent(fixture("sentitems"), received)
        self.assertEqual(reply["in_reply_to_received_at"], "2026-03-02T09:00:00Z")
        self.assertEqual(reply["in_reply_to_sender"], "contact@example.org")
        self.assertEqual(reply["conversation_id"], "conversation-1")
        self.assertEqual(reply["to"], ["contact@example.org"])
        self.assertEqual(reply["cc"], ["team@example.com"])
        self.assertEqual(reply["recipient_names"], ["Alex"])
        self.assertNotIn("in_reply_to_received_at", new)
        self.assertNotIn("bodyPreview", reply)
        decisions = [{"id": "mail-ask", "thread_id": "conversation-1", "bucket": "reply",
                      "received_at": received[0]["received_at"]}]
        self.assertEqual(sent.daily_signals([reply], decisions)["signals"][0]["signal"], "replied")

    def test_latest_preceding_received_from_recipient_only(self):
        received = [{"id": str(i), "thread_id": thread, "sender": sender, "received_at": timestamp}
                    for i, (thread, sender, timestamp) in enumerate([
                        ("conversation-1", "contact@example.org", "2026-03-02T08:00:00Z"),
                        ("conversation-1", "contact@example.org", "2026-03-02T10:00:00+01:00"),
                        ("conversation-1", "contact@example.org", "2026-03-02T12:00:00Z"),
                        ("conversation-1", "other@example.net", "2026-03-02T10:00:00Z"),
                        ("other-thread", "contact@example.org", "2026-03-02T10:00:00Z"),
                    ])]
        self.assertEqual(collect.sent(fixture("sentitems"), received)[0]["in_reply_to_received_at"],
                         "2026-03-02T10:00:00+01:00")
        for timestamp in ["2026-03-02T11:00:00Z", "2026-03-02T12:00:00Z"]:
            received[0]["received_at"] = timestamp
            self.assertNotIn("in_reply_to_received_at", collect.sent(fixture("sentitems"), received[:1])[0])

    def test_no_received_index_and_meeting_response(self):
        raw = fixture("sentitems")
        self.assertNotIn("in_reply_to_received_at", collect.sent(raw)[0])
        raw["value"][0]["@odata.type"] = "#microsoft.graph.eventMessageResponse"
        received = collect.mail(fixture("messages"), "alex@example.com")
        result = collect.sent(raw, received)[0]
        self.assertTrue(result["is_meeting_response"])
        self.assertNotIn("in_reply_to_received_at", result)


class CalendarTests(unittest.TestCase):
    def test_fields_external_domains_and_time_offsets(self):
        external, internal = collect.calendar(fixture("calendarView"), PROFILE)
        self.assertTrue(external["external"])
        self.assertFalse(internal["external"])
        self.assertEqual(external["invitees"], 2)
        self.assertTrue(external["is_series"])
        self.assertFalse(internal["is_series"])
        self.assertEqual(external["my_response"], "none")
        self.assertEqual(internal["my_response"], "accepted")
        self.assertEqual(external["start"], "2026-03-03T10:00:00Z")
        self.assertEqual(internal["start"], "2026-03-03T11:00:00Z")
        self.assertEqual(internal["end"], "2026-03-03T12:00:00Z")
        self.assertEqual(external["sender"], "organizer@example.com")
        self.assertEqual(external["channel"], "invite")
        self.assertEqual(external["event_id"], external["id"])

    def test_external_exact_domain_not_suffix(self):
        raw = fixture("calendarView")["value"][0]
        raw["attendees"] = [{"emailAddress": {"address": "contact@sub.example.com"}}]
        self.assertTrue(collect.calendar(raw, PROFILE)[0]["external"])
        self.assertFalse(collect.calendar(raw, {"internal_domains": ["sub.example.com", "example.com"]})[0]["external"])
        self.assertTrue(collect.calendar(raw, {})[0]["external"])
        raw["attendees"] = []
        self.assertFalse(collect.calendar(raw, PROFILE)[0]["external"])

    def test_external_organizer_protects_internal_attendees(self):
        raw = fixture("calendarView")["value"][1]
        raw["organizer"]["emailAddress"]["address"] = "organizer@example.org"
        self.assertTrue(collect.calendar(raw, PROFILE)[0]["external"])

    def test_responses_recurrence_cancellation_and_timezones(self):
        raw = fixture("calendarView")["value"][0]
        for response, expected in [("tentativelyAccepted", "tentative"), ("declined", "declined"),
                                   ("organizer", "organizer"), ("accepted", "accepted"), ("none", "none")]:
            raw["responseStatus"]["response"] = response
            self.assertEqual(collect.calendar(raw, PROFILE)[0]["my_response"], expected)
        raw.pop("seriesMasterId")
        raw["type"] = "seriesMaster"
        self.assertTrue(collect.calendar(raw, PROFILE)[0]["is_series"])
        raw["start"]["timeZone"] = "Europe/Amsterdam"
        self.assertEqual(collect.calendar(raw, PROFILE)[0]["start"], "2026-03-03T09:00:00Z")
        raw["isCancelled"] = True
        self.assertEqual(collect.calendar(raw, PROFILE), [])


class TeamsTests(unittest.TestCase):
    def collect(self, raw=None, **kw):
        return collect.teams(raw if raw is not None else fixture("chat-messages"), "alex-id",
                             kw.get("profile", PROFILE), fixture("chats"), kw.get("now", NOW))

    def test_unanswered_mentions_questions_and_no_body(self):
        direct, mention = self.collect()
        self.assertTrue(direct["direct"])
        self.assertFalse(direct["mentions_me"])
        self.assertFalse(direct["has_question"])
        self.assertTrue(mention["mentions_me"])
        self.assertTrue(mention["has_question"])
        self.assertFalse(mention["direct"])
        self.assertEqual(mention["deadline_hint"], "by friday")
        self.assertEqual(mention["subject"], "Synthetic planning")
        self.assertEqual(mention["sender"], "contact@example.org")
        self.assertEqual(mention["sender_domain"], "example.org")
        self.assertEqual(direct["sender"], "contact-id")
        self.assertTrue(mention["to_me"])
        self.assertFalse(mention["cc_only"])
        self.assertFalse(any("body" in item or "preview" in item for item in [direct, mention]))

    def test_recent_direct_plain_and_unmentioned_group_ignored(self):
        self.assertEqual(len(self.collect(now=parse_ts("2026-03-02T10:00:00Z"))), 1)
        raw = fixture("chat-messages")["value"][1]
        raw["mentions"] = [{"mentioned": {"user": {"id": "other-id"}}}]
        raw["body"]["content"] = "Synthetic update."
        self.assertEqual(self.collect(raw), [])
        raw["body"]["content"] = "<p>Ready&#63;</p>"
        self.assertTrue(self.collect(raw)[0]["has_question"])

    def test_latest_own_reply_and_input_order(self):
        raw = fixture("chat-messages")["value"]
        self.assertEqual(self.collect(list(reversed(raw))), self.collect(raw))
        self.assertNotIn("chat-answered", [m["thread_id"] for m in self.collect()])

    def test_message_ids_scoped_to_chat_and_retained_for_host(self):
        raw = fixture("chat-messages")["value"][1]
        items = self.collect([raw, {**raw, "chatId": "other-chat"}])
        self.assertEqual(len(items), 2)
        self.assertNotEqual(items[0]["id"], items[1]["id"])
        self.assertEqual(items[0]["message_id"], items[1]["message_id"])
        items = self.collect([{**raw, "chatId": "a/b", "id": "c"},
                              {**raw, "chatId": "a", "id": "b/c"}])
        self.assertNotEqual(items[0]["id"], items[1]["id"])

    def test_deleted_system_and_missing_sender(self):
        raw = fixture("chat-messages")["value"][1]
        for patch in [{"deletedDateTime": "2026-03-02T13:00:00Z"},
                      {"messageType": "systemEventMessage"}, {"from": None}]:
            self.assertEqual(self.collect({**raw, **patch}), [])
        raw.pop("chatId")
        with self.assertRaises(ValueError):
            self.collect(raw)

    def test_working_hours_weekends_timezone_and_threshold(self):
        raw = fixture("chat-messages")["value"][0]
        raw["createdDateTime"] = "2026-02-27T16:00:00Z"  # Friday.
        self.assertEqual(self.collect(raw, now=parse_ts("2026-03-02T11:00:00Z")), [])
        self.assertEqual(len(self.collect(raw, now=parse_ts("2026-03-02T12:00:00Z"))), 1)
        profile = {**PROFILE, "tz": "Europe/Amsterdam", "working_hours": [10, 18], "teams_reply_hours": 2}
        raw["createdDateTime"] = "2026-03-02T09:00:00Z"
        self.assertEqual(len(self.collect(raw, profile=profile, now=parse_ts("2026-03-02T11:00:00Z"))), 1)


class CollectorCliTests(unittest.TestCase):
    def test_equal_message_ids_from_different_chats_survive_output_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = lambda name: os.path.join(tmp, name)
            message = fixture("chat-messages")["value"][1]
            for name, value in [("messages.json", [message, {**message, "chatId": "other-chat"}]),
                                ("state.json", {"head": {"profile": PROFILE}})]:
                with open(path(name), "w") as fh:
                    json.dump(value, fh)
            run("collect-teams", "--input", path("messages.json"), "--state", path("state.json"),
                "--me-id", "alex-id", "--out", path("items.json"))
            items = load(path("items.json"))
            self.assertEqual(len(items), 2)
            self.assertEqual(len({item["id"] for item in items}), 2)
            self.assertEqual({item["message_id"] for item in items}, {"teams-mention"})

    def test_saved_graph_to_classification_and_sent_signals(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = lambda name: os.path.join(tmp, name)
            graph = lambda name: os.path.join(FIXTURES, name + ".json")
            run("store-init", "--store", path("memory"), "--account", "alex")
            run("store-load", "--store", path("memory"), "--out", path("state.json"))
            state = load(path("state.json"))
            state["head"]["profile"].update(PROFILE)
            with open(path("state.json"), "w") as fh:
                json.dump(state, fh)
            run("collect-mail", "--input", graph("messages"), "--me", "alex@example.com", "--out", path("items.json"))
            run("collect-sent", "--input", graph("sentitems"), "--received", path("items.json"), "--out", path("sent.json"))
            for _ in range(2):
                run("collect-teams", "--input", graph("chat-messages"), "--chats", graph("chats"),
                    "--state", path("state.json"), "--me-id", "alex-id", "--now", "2026-03-02T14:00:00Z",
                    "--out", path("items.json"), "--append")
            run("collect-calendar", "--input", graph("calendarView"), "--state", path("state.json"),
                "--out", path("calendar.json"))
            items = load(path("items.json"))
            self.assertEqual(len(items), 4)
            self.assertEqual(len(load(path("calendar.json"))), 2)
            self.assertEqual(set(load(path("calendar.json"))[0]),
                             {"event_id", "subject", "start", "end", "my_response", "external"})
            run("classify", "--state", path("state.json"), "--items", path("items.json"),
                "--calendar", path("calendar.json"), "--out", path("decisions.json"), "--dry-run")
            self.assertEqual(load(path("decisions.json"))["decisions"][0]["bucket"], "reply")
            result = sent.daily_signals(load(path("sent.json")), load(path("decisions.json"))["decisions"])
            self.assertEqual(result["signals"][0]["signal"], "replied")
            self.assertFalse(any(key in json.dumps(items) for key in ["bodyPreview", "contentType"]))

    def test_multiple_saved_pages_and_empty_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = os.path.join(tmp, "items.json")
            empty = os.path.join(tmp, "empty.json")
            with open(empty, "w") as fh:
                json.dump({"value": []}, fh)
            graph = os.path.join(FIXTURES, "messages.json")
            run("collect-mail", "--input", graph, graph, empty, "--me", "alex@example.com", "--out", output)
            self.assertEqual(len(load(output)), 2)
            run("collect-mail", "--input", empty, "--me", "alex@example.com", "--out", output)
            self.assertEqual(load(output), [])


if __name__ == "__main__":
    unittest.main()
