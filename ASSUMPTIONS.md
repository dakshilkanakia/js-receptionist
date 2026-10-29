# Assumptions

The spec says "Don't wait on us. We don't answer questions about the task; decide, and mention your assumptions in the video." These are the decisions we made where the spec was silent or ambiguous. Each one is mentioned in the Loom.

| # | Assumption | Why |
|---|---|---|
| A1 | The greeting tells the caller the call is transcribed, and storage starts right away. If the caller declines at any point, the stored transcript is deleted and nothing more is stored; only metadata is kept (time, length, outcome). If they still want a callback, the agent asks permission to save just their first name, number and reason. | Spec: "tell callers the call is transcribed; if they decline, stop storing it." A callback can't happen without storing contact details, so we ask explicitly. |
| A2 | Only 425 Park Ave S hours are known. For other stores, the agent points to jscleaners.nyc/locations or offers a callback. | Those are the only hours in the facts; inventing hours breaks "answers only from the facts". |
| A3 | "+50% / +100% of the order" applies to the whole order subtotal. | Literal reading of the spec. |
| A4 | The agent states the same-day "drop off before 9 AM" condition but can't verify drop-off time. | The agent has no order system. |
| A5 | The agent never gives a ready date or time, only the turnaround rules (about 2 days, rush options, plant closed on weekends). | A date would be a promise, and "say an order is ready" is forbidden. |
| A6 | Callback phone numbers are US numbers, read back digit by digit before saving. | NYC business; avoids saving a wrong number. |
| A7 | One owner login is enough for the demo. Multi-user access / IAM with roles is future work. | Scope for 5 days. |
| A8 | Every price spoken is "starting at", with the note that fabric, size or designer details can add to it. | Spec says prices are "starting at". |
| A9 | Same-day rush applies only to dry-cleaning items: shirts (hanger, boxed, hand-pressed), pants, jacket, dress, coat, gown. Wash & fold, comforters and sneakers are not eligible. | Spec: "same day +100%, dry cleaning dropped off before 9 AM". |
| A10 | Rush does not apply to alterations. Pants hem is always $25; for a rush alteration the agent says it isn't sure and offers a callback. | The spec gives no rush rule for alterations, and the tailor prices everything else in person. |
