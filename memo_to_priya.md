# Vireo Audio Support — findings from 18 months of tickets

*For Priya Raman, Head of Customer Experience — 5 min read*

## The headline number

**Some orders are being compensated for more than they cost — 178 of them in
the last 18 months, worth roughly Rs 45,000–75,000 a quarter.**

This isn't refunds or replacements alone — both are normal and expected. It's
orders where a customer received refunds and/or a replacement adding up to
*more than they paid*. Example: an order worth Rs 5,199 was refunded in full,
twice, on two separate tickets six weeks apart — plus a replacement was sent.
Because these cases are spread across several tickets, weeks apart, nobody
handling any single ticket would have seen the pattern.

**Recommendation:** a weekly list of these orders goes to Finance, matching
what your own support policy already says should happen — it currently isn't,
because nothing surfaces the pattern. Cutting this from 3.5% to 1.0% of
orders that generate a ticket is worth the number above. That range, not a
single figure, because a small amount of this is legitimate (approved
goodwill on top of another remedy) — the range accounts for that.

## What else 18 months of tickets show

- **8.9% of tickets miss their first-response target** and each one auto-issues
  a Rs 350 credit — about Rs 61,600 a quarter. Email is the worst channel,
  missing its target 11.6% of the time.
- **13.2% of resolved tickets come back within 30 days** — the customer
  contacts again about the same kind of problem. About Rs 72,000 a quarter in
  repeat contact cost.
- **A pattern I checked because it looked like an easy target for
  cost-cutting, and it wasn't:** goodwill credits over your Rs 500-per-ticket
  cap. 37 of 42 goodwill tickets exceed it — worth flagging to whoever
  approves these, since it's a small, clear, fixable leak (~Rs 3,000/quarter).

## About the leaderboard

You asked for tickets-closed-per-week by agent, and it's included. But I'd
treat it carefully before using it to judge anyone: it mostly reflects which
team an agent sits in, not how good they are. Logistics and Billing agents
close 5+ tickets a week almost automatically because those tickets are fast;
email tickets take 8× longer to handle than chat, so an email agent can never
catch up. Your warranty team comes out at the bottom every time, which your
own policy explicitly says shouldn't be used to judge them — their cases are
built to take days.

The good news: once you compare agents *within their own team*, closing more
tickets goes with **better** customer satisfaction, not worse. There's no
evidence anyone is rushing tickets to inflate their count. I've included a
second, corrected view ranked within team alongside the one you asked for.

## What this cost to build, and what's not finished yet

Built with AI-assisted analysis and Python; the business number above is
computed directly from your ticket, order and policy data, not estimated. A
first accuracy check on the "what are people complaining about" categorizer
came back honest but unfinished — full detail and the reason is in the
technical package, in `decisions.md` and `COST_LOG.md`. It doesn't affect the
number above, which never depended on it.

Happy to walk through any of this on a call.
