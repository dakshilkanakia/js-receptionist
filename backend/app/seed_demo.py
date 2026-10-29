"""Fill an empty database with made-up demo calls so the dashboard isn't blank.

Run once after the first deploy:  python -m app.seed_demo
All callers, names and phone numbers are fictional (555 numbers).
Refuses to run if any calls exist, unless --force is given.
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.db.models import Call, CallbackRequest, TranscriptTurn, UnansweredQuestion
from app.db.session import SessionLocal
from app.facts.repo import latest_facts, seed_if_empty

GREETING = ("Hi, thanks for calling J's Cleaners! I'm Jenny, an AI assistant. Just so you know, this call is "
            "transcribed so our team can follow up. If you'd rather it not be, just say so. How can I help?")

# (hours ago, duration s, outcome, consent_declined, turns, callback, question)
DEMO = [
    (52, 74, "answered", False, [
        ("user", "Hi, how much is it to get a few shirts done?"),
        ("assistant", "Shirts on a hanger start at $4.95 each, or $5.95 boxed. How many do you have?"),
        ("user", "Six on hangers."),
        ("tool", 'Quote: total $29.70 | request {"items": [{"id": "shirt_hanger", "qty": 6}]}'),
        ("assistant", "Six shirts on hangers come to $29.70, a starting price. Anything else?"),
        ("user", "No, that's it, thanks."),
        ("assistant", "Thanks for calling J's Cleaners, have a great day!"),
    ], None, None),
    (49, 96, "callback_requested", False, [
        ("user", "Is my order ready? I dropped off a suit on Monday."),
        ("assistant", "I can't check order status, but a team member can. Would you like a callback?"),
        ("user", "Yes please. It's Maria."),
        ("assistant", "Thanks, Maria. What's the best number to reach you?"),
        ("user", "Two one two, five five five, zero one two three."),
        ("assistant", "That's two, one, two, five, five, five, zero, one, two, three. Is that right?"),
        ("user", "Yes."),
        ("tool", "Callback saved: Maria, +12125550123, reason: Wants to know if her suit order is ready."),
        ("assistant", "You're all set, Maria. A team member will call you back about your suit."),
    ], ("Maria", "+12125550123", "Wants to know if her suit order is ready."), None),
    (30, 63, "answered", False, [
        ("user", "How much for ten pounds of wash and fold, next day?"),
        ("tool", 'Quote: total $44.85 | request {"items": [{"id": "wash_fold", "qty": 10}], "rush": "next_day"}'),
        ("assistant", "Ten pounds with next-day rush comes to $44.85, a starting price."),
        ("user", "Great, thanks."),
    ], None, None),
    (27, 58, "unanswered", False, [
        ("user", "Do you clean suede boots?"),
        ("tool", "Logged unanswered question: Do you clean suede boots?"),
        ("assistant", "I'm not sure about suede boots. Would you like a team member to call you back about it?"),
        ("user", "No, I'll check the website. Bye."),
    ], None, "Do you clean suede boots?"),
    (20, 41, "answered", True, [], None, None),
    (8, 6, "abandoned", False, [], None, None),
    (5, 88, "callback_requested", False, [
        ("user", "I want a refund, my sweater shrank."),
        ("assistant", "I'm sorry about your sweater. Refunds need a team member. Can I take your name for a callback?"),
        ("user", "Sam."),
        ("assistant", "Thanks, Sam. What's the best number to reach you?"),
        ("user", "Nine one seven, five five five, zero one nine eight."),
        ("assistant", "That's nine, one, seven, five, five, five, zero, one, nine, eight. Correct?"),
        ("user", "Yes."),
        ("tool", "Callback saved: Sam, +19175550198, reason: Sweater shrank; asking about a refund."),
        ("assistant", "Done, Sam. Someone from our team will call you back about the sweater."),
    ], ("Sam", "+19175550198", "Sweater shrank; asking about a refund."), None),
    (2, 52, "answered", False, [
        ("user", "Is the Park Avenue South store open on Saturday?"),
        ("assistant", "Yes, 425 Park Avenue South is open Saturday from 9 AM to 5 PM."),
        ("user", "Perfect."),
    ], None, None),
]


async def main(force: bool) -> None:
    async with SessionLocal() as s:
        await seed_if_empty(s)
        if not force and await s.scalar(select(func.count()).select_from(Call)):
            print("Calls already exist; not adding demo data (use --force to add anyway).")
            return
        version_id, _ = await latest_facts(s)
        now = datetime.now(timezone.utc)
        for hours_ago, duration, outcome, declined, turns, callback, question in DEMO:
            started = now - timedelta(hours=hours_ago)
            call = Call(started_at=started, ended_at=started + timedelta(seconds=duration), duration_s=duration,
                        outcome=outcome, consent_declined=declined, has_unanswered=question is not None,
                        facts_version_id=version_id)
            s.add(call)
            await s.flush()
            if turns:
                s.add(TranscriptTurn(call_id=call.id, idx=1, role="assistant", text=GREETING, created_at=started))
            for i, (role, text) in enumerate(turns, start=2):
                s.add(TranscriptTurn(call_id=call.id, idx=i, role=role, text=text,
                                     created_at=started + timedelta(seconds=6 * i)))
            if callback:
                name, phone, reason = callback
                s.add(CallbackRequest(call_id=call.id, first_name=name, phone_e164=phone, reason=reason,
                                      created_at=started + timedelta(seconds=duration - 10)))
            if question:
                s.add(UnansweredQuestion(call_id=call.id, question=question, created_at=started + timedelta(seconds=12)))
        await s.commit()
        print(f"Added {len(DEMO)} demo calls.")


if __name__ == "__main__":
    asyncio.run(main("--force" in sys.argv))
