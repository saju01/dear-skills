# Learning loop

Learns from one source only: what **the user** did.

1. **Signals** (from each channel's Observe section) are kept for 7 days.
2. **Grouping** by series rule, else sender. ≥ 2 signals pointing the same way → a **proposal**: an inferred rule at confidence 0.6 with the evidence ids. Mixed directions → listed as inconsistent, never promoted.
3. **Asking**: the report asks about each proposal once (one question). Confirm → explicit rule (confidence 1.0). Reject → a `correction` fact that blocks the same proposal for 60 days.
4. **Expiry**: proposals expire after 14 days unanswered. Inferred rules with no supporting signal for 30 days are retired.
5. **Autonomy** per bucket (`engine autonomy`): a run counts when it had ≥ 3 decisions. Promotion needs ≥ 5 counted runs in a row with override rate < 5% and ≥ 30 decisions in the streak. Any wrong action (binned draft, Noise item marked unread, invite answered differently) pauses that rule and drops the bucket one level.

## Weekly review (`dear-inbox-zero learn`)

`python engine/dear_engine.py review --state …` → accuracy per bucket and channel, rules learned/retired this week, proposals waiting, top unknown senders. Ask the waiting proposals one at a time. Then publish.

## Store hygiene

Facts are append-only. A changed rule writes a new fact plus a supersession record. The head stays under 16 KB: closed ledger items older than 30 days and run history beyond 30 runs are dropped at publish.
