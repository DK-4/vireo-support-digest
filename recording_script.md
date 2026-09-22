# Screen-recording script — max 3:00

Talking script with suggested on-screen action. Read naturally, don't rush —
if it runs long, cut from "Extra if time allows" first.

---

**[0:00–0:20] Open: what this is**
*Show: README.md*

"This is a support-ops tool for Vireo Audio, built from their ticket export,
orders, and support policy. It does three things: a weekly digest of what
customers are complaining about, an agent leaderboard, and — the thing that
actually moves money — a weekly watchlist for Finance."

**[0:20–0:55] The number**
*Show: decisions.md, D13, scrolled to the goal statement — or out/digest.md*

"178 orders in the last 18 months were compensated for more than they cost —
refunded twice, or refunded and replaced. It's in the support policy that
this should never happen and should go to Finance same-day. It doesn't,
because the two events are usually weeks apart on different tickets, so no
one sees the pattern. Fixing this to 1% of orders is worth forty-five to
seventy-five thousand rupees a quarter — I give a range, not a point number,
because part of it is legitimate goodwill and I didn't want to overstate it."

**[0:55–1:25] How I know it's real, not a guess**
*Show: run a quick `python -m pytest tests/ -q` live, or show the green output*

"Every number here is computed in code from the actual files — eleven tests
lock down the three real data problems I found: seven hundred sixty-five
duplicate rows from a system migration, a timezone bug that made resolution
times look impossible, and a satisfaction score where zero secretly meant 'no
response,' not a bad rating. All three are in decisions.md with the evidence
that made me sure, not just assumed."

**[1:25–2:00] The leaderboard, and why I didn't just ship what was asked**
*Show: out/leaderboard.md, both tables*

"I was asked for tickets-closed-per-week, and it's here. But I checked
whether it was fair first, and it isn't — it mostly measures which team you
sit in, not skill. So I shipped a second, corrected view next to it, ranked
within team, and I flagged that the raw one shouldn't be used to judge
anyone. That's a real example of me pushing back on the brief rather than
just executing it."

**[2:00–2:35] What's honestly unfinished**
*Show: COST_LOG.md, the live-attempt section*

"The theme classifier — what customers are complaining about — is built and
tested against a keyword placeholder, sixty-seven percent accurate, which I
know because I hand-labelled ninety-six tickets blind myself and scored
against them. I did attempt a real run against Gemini's free tier, hit their
rate limit, fixed the retry logic for it, tried again, and ran into a second
issue I didn't have time to fully chase down. That's logged honestly, with
the actual error codes, not smoothed over. It doesn't touch the business
number — that's pure order-and-refund arithmetic, no model involved."

**[2:35–3:00] Close**
*Show: file tree of the project*

"Everything here — the tests, the decisions log, the cost log — is meant to
let someone else pick this up cold. Thanks for watching."

---

## Extra, if you have time to spare (cut this first if over 3:00)
Show `out/breach_watchlist.csv` — "this is the literal list Finance would
work from, one row per order, ticket IDs included."
