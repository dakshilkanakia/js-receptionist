"""Tools the LLM can call. Every action the agent claims must go through one of these."""

import json

import phonenumbers
from loguru import logger
from pipecat.adapters.llm.schemas.function_schema import FunctionSchema
from pipecat.adapters.llm.schemas.tools_schema import ToolsSchema
from pipecat.frames.frames import EndWorkerFrame, FunctionCallResultProperties
from pipecat.services.llm_service import FunctionCallParams, LLMService

from app.agent.recorder import CallRecorder
from app.agent.speech_tracker import SpeechTracker
from app.db.models import CallbackRequest, UnansweredQuestion
from app.db.session import SessionLocal
from app.facts.schema import Facts
from app.pricing.quote import quote


def normalize_us_phone(raw: str) -> str | None:
    try:
        n = phonenumbers.parse(raw, "US")
    except phonenumbers.NumberParseException:
        return None
    if n.country_code != 1 or not phonenumbers.is_valid_number(n):
        return None
    return phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164)


def build_tools(facts: Facts) -> ToolsSchema:
    item_ids = [p.id for p in facts.prices]
    addon_ids = [a.id for a in facts.addons]
    return ToolsSchema(
        standard_tools=[
            FunctionSchema(
                name="get_quote",
                description=(
                    "Calculate an exact price for an order. Use for any total, multiple items, "
                    "weights, add-ons or rush. Quantities: pounds for wash_fold, count otherwise."
                ),
                properties={
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "enum": item_ids},
                                "qty": {"type": "number"},
                            },
                            "required": ["id", "qty"],
                        },
                    },
                    "addons": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "enum": addon_ids},
                                "qty": {"type": "number"},
                            },
                            "required": ["id", "qty"],
                        },
                    },
                    "rush": {"type": "string", "enum": ["none", "next_day", "same_day"]},
                },
                required=["items"],
            ),
            FunctionSchema(
                name="save_callback",
                description=(
                    "Save a callback request for a team member. Only call after the caller "
                    "confirmed their phone number."
                ),
                properties={
                    "first_name": {"type": "string"},
                    "phone": {"type": "string", "description": "US phone number, digits only"},
                    "reason": {"type": "string", "description": "Short reason for the callback"},
                },
                required=["first_name", "phone", "reason"],
            ),
            FunctionSchema(
                name="log_unanswered_question",
                description="Record a caller question you could not answer from the facts.",
                properties={"question": {"type": "string"}},
                required=["question"],
            ),
            FunctionSchema(
                name="set_transcript_consent",
                description="Call with granted=false if the caller does not want the call transcribed.",
                properties={"granted": {"type": "boolean"}},
                required=["granted"],
            ),
            FunctionSchema(
                name="end_call",
                description="Hang up after you have said goodbye.",
                properties={},
                required=[],
            ),
        ]
    )


def register_tools(llm: LLMService, facts: Facts, rec: CallRecorder, speech: SpeechTracker) -> None:
    def follow_up() -> FunctionCallResultProperties:
        # Only ask the LLM to speak again if it hasn't already said something this response.
        return FunctionCallResultProperties(run_llm=not speech.spoke_this_response)

    async def get_quote(params: FunctionCallParams):
        args = params.arguments
        result = quote(facts, args.get("items") or [], args.get("addons") or [], args.get("rush"))
        payload = result.as_tool_result()
        summary = f"Quote: total {payload['total']}" if result.ok else f"Quote error: {'; '.join(result.errors)}"
        await rec.add_turn("tool", f"{summary} | request {json.dumps(args)}")
        await params.result_callback(payload)

    async def save_callback(params: FunctionCallParams):
        args = params.arguments
        name = (args.get("first_name") or "").strip()
        reason = (args.get("reason") or "").strip()
        phone = normalize_us_phone(args.get("phone") or "")
        if not name or not reason:
            await params.result_callback({"ok": False, "error": "First name and reason are required."})
            return
        if phone is None:
            await params.result_callback(
                {"ok": False, "error": "That phone number isn't a valid US number. Ask the caller to repeat it."}
            )
            return
        try:
            async with SessionLocal() as s:
                row = CallbackRequest(call_id=rec.call_id, first_name=name, phone_e164=phone, reason=reason)
                s.add(row)
                await s.commit()
        except Exception:
            logger.exception("save_callback failed")
            await params.result_callback({"ok": False, "error": "Could not save. Give the caller the main line."})
            return
        rec.callback_saved = True
        await rec.add_turn("tool", f"Callback saved #{row.id}: {name}, {phone}, reason: {reason}")
        await params.result_callback({"ok": True, "callback_id": row.id, "phone_saved": phone})

    async def log_unanswered_question(params: FunctionCallParams):
        question = (params.arguments.get("question") or "").strip()
        if question:
            async with SessionLocal() as s:
                s.add(UnansweredQuestion(call_id=rec.call_id, question=question))
                await s.commit()
            rec.unanswered_logged = True
            await rec.add_turn("tool", f"Logged unanswered question: {question}")
        await params.result_callback({"ok": True}, properties=follow_up())

    async def set_transcript_consent(params: FunctionCallParams):
        if params.arguments.get("granted") is False:
            await rec.decline_consent()
            await params.result_callback({"ok": True, "transcript": "stopped and deleted"}, properties=follow_up())
        else:
            await params.result_callback({"ok": True})

    async def end_call(params: FunctionCallParams):
        await params.result_callback({"ok": True}, properties=FunctionCallResultProperties(run_llm=False))
        # Pushed downstream so the goodbye audio already queued plays before hang-up.
        await params.llm.push_frame(EndWorkerFrame())

    llm.register_function("get_quote", get_quote)
    llm.register_function("save_callback", save_callback)
    llm.register_function("log_unanswered_question", log_unanswered_question)
    llm.register_function("set_transcript_consent", set_transcript_consent)
    llm.register_function("end_call", end_call)
