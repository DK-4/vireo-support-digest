# Taxonomy — 13 labels

One line per label, then two real customer messages from the export (PII
stripped, ticket IDs given so every example can be checked against the data).
Examples were chosen by hand from the 66-ticket sample read in Phase 1 plus a
keyword search of the full export; they illustrate the label, they are not
model output and they are not a gold set.

See decisions.md D14 for why this is 13 labels and not 12.

### Delivery delayed or not received
Order has not arrived, is late, tracking is stuck, or courier marked delivered but nothing received.

- `TK-240014` (social) — "hello ji / tracking has said out for delivery for a week now / a month ago se / my nexa fit band [ORDER_ID] / help"
- `TK-240104` (voice) — "[IVR transcript] hi vireo support, airlite purchased around diwali, order [ORDER_ID]. the courier marked it delivered but nobody in my house got anything. i want my money back."

### Arrived damaged or dead on arrival
Item arrived physically damaged, cracked, dented, or non-functional straight out of the box.

- `TK-240540` (voice) — "hey / screen has a crack before i even switched it on / anyone there"
- `TK-240412` (email) — "hi there, ordered nexa 2 around diwali.  box was crushed and the nexa 2 is cracked. i took photos. what do i do now? please revert, siddharth mittal"

### Charging & battery fault
Device or case will not charge, shows 0%, drains abnormally fast, or will not power on.

- `TK-240138` (chat) — "no light comes on the case when I plug it in"
- `TK-242675` (email) — "To the Vireo Customer Care Team, /  / I am writing witth reference to my order of the AirLite buds placed on 02-06-2025. Left earbud shows 0% and never charges. I have removed and reinserted it 10 tim"

### Audio quality fault
Sound problem in a working device: one side silent, buzzing, distortion, low or unclear microphone.

- `TK-240059` (email) — "namaste, order [ORDER_ID] (arc neckband).  i hear music in one ear only, other is mute. please advise. rgds,"
- `TK-240002` (chat) — "hello / buzzing sound from the speaker / ??"

### Connectivity & pairing fault
Bluetooth will not pair, drops, cuts out, or the device no longer appears in the phone's device list.

- `TK-240396` (email) — "hello / bluetooth keeps cutting out"
- `TK-240133` (chat) — "Hi Vireo support, / I bought the neckband on 07-12-2024. Keeps losing my phone if I walk to the other room. / Please help. / Thank you, Tarun"

### App & firmware fault
Companion app crashes, shows a blank screen, or a firmware update fails or hangs.

- `TK-240174` (email) — "app crashes when i open device settings - [ORDER_ID]"
- `TK-240316` (voice) — "[IVR transcript] hi sir firmware update stuck for 2 hours kal se my pulse [ORDER_ID]"

### Payment & invoice
Money taken with no order created, duplicate charge, coupon or discount not applied, or tax invoice / receipt request.

- `TK-240136` (email) — "I AM LOSING PATIENCE. Thsi is regaarding the neckband. my bank says Rs 3499 went to you but your site says I have no orders. I already waited 24 hours. Refund. Now."
- `TK-240641` (chat) — "Very poor quality. I bought my Nexa on 07 Feb. my company accounts team is asking for the tax bill. I already tried different browser. Fix this or I am posting on twitter."

### Account access / login
Cannot sign in, OTP not arriving, or account locked.

- `TK-240062` (chat) — "sir ji / not receiving otp to login / anyone there"
- `TK-240048` (voice) — "[IVR transcript] locked out of my own account since recently [ORDER_ID] what do i do now?"

### Return pickup & refund status
Return pickup not collected or rescheduled, or a refund already agreed has not reached the customer.

- `TK-240043` (chat) — "hi team, / i bought my strata 2 headphones on december 06.  packed the box a week ago & it's still here. / please advise. / regards, varun kapoor"
- `TK-240006` (email) — "Got airlite earbuds from Amazon 3 weeks back. Refund not received yet. I emailed twice. Kindly look into it. Thanks & regards,"

### Warranty claim / RMA status
Chasing an existing warranty claim or RMA number, or asking for warranty repair.

- `TK-244149` (email) — "hello ji / warranty claim pending for 20 days"
- `TK-240126` (chat) — "what is the status of my warranty claim, i want my money back"

### Order change, cancellation & address
Cancel before dispatch, wrong variant ordered, or delivery address needs changing.

- `TK-240221` (voice) — "ordered the wrong colour, don't ship it / pleaase advise"
- `TK-240159` (chat) — "hi there, i bought my pulse on january 05. please cancel, ordered by mistake. i tried cancel button, greyed out. nothing changed. not acceptable at this price. can someone fix this?"

### Pre-sales / compatibility (no fault)
Question about whether a product works with something, or what it does, with no fault reported. Excluded from fault-cost work.

- `TK-240313` (chat) — "Dear Sir/Madam, /  / I am writing with reference to my order of the strata 3 ([ORDER_ID]) placed on 20 Jan.  Will this survive a shower. I request you to process a refund to my original payment method"
- `TK-245320` (email) — "not what i expeected from vireo. got my pulse 2 from amazon 10 days ago. does my pulse 2 work with iphone. refund. now."

### Unclear / other
Genuinely cannot be placed in a theme above from the message alone.

- `TK-240032` (email) — "touch screen not responding" — a hardware fault on a
  watch that is not audio, charging, connectivity or app. No theme fits.
- `TK-240163` (email) — "strap pin came off / [ORDER_ID] / please help" — a
  physical breakage in use. Not damage on arrival, not a warranty claim yet,
  and the customer has not said what they want.

Note: the two examples above were selected by hand as genuinely unplaceable.
The MOCK keyword fallback currently sends 27% of tickets here, which is a
property of the fallback, not of the corpus, and is one of the first things
the real classifier should beat.
