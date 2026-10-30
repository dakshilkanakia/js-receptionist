"""After a caller declines transcription, no turn text may reach the logs."""

from loguru import logger

from app.agent.recorder import CallRecorder


def test_loggable_respects_consent():
    rec = CallRecorder(call_id=1)
    assert rec.loggable("How much are pants?") == "How much are pants?"
    rec.consent = False
    assert "pants" not in rec.loggable("How much are pants?")
    assert rec.loggable(None).startswith("[withheld")


def test_no_turn_text_in_log_output_after_decline():
    rec = CallRecorder(call_id=1)
    lines: list[str] = []
    sink = logger.add(lines.append, level="INFO")
    try:
        logger.info(f"call 1 USER: {rec.loggable('my number is 2125550147')}")
        rec.consent = False
        logger.info(f"call 1 USER: {rec.loggable('my secret refund story')}")
    finally:
        logger.remove(sink)
    assert "2125550147" in lines[0]
    assert "secret refund story" not in lines[1]
