import asyncio
import json
import logging
from datetime import datetime, timezone

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:8b"
MAX_BATCH = 20

logger = logging.getLogger(__name__)

SERVICE_OFFERS = {
    "ev_charger": "EV charger installation for Tesla, ChargePoint, and universal Level 2 chargers",
    "panel_upgrade": "panel upgrades to support modern electrical loads and avoid breaker tripping",
    "commercial_electrical": "commercial electrical work including tenant improvements and new construction",
    "general_electrical": "general electrical repairs, outlets, lighting, and troubleshooting",
    "solar": "solar panel interconnection and battery storage electrical work",
}

URGENCY_LINES = {
    "high": "I noticed many properties in your area are upgrading their electrical systems right now",
    "medium": "As licensed electricians serving Los Angeles, we partner with property teams like yours",
    "low": "I wanted to introduce myself as a local electrical contractor serving your area",
}


async def _ollama_generate(prompt: str, max_tokens: int = 300) -> str:
    proc = await asyncio.create_subprocess_exec(
        "curl", "-s", "-X", "POST", OLLAMA_URL,
        "-d", json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=300)
        data = json.loads(stdout.decode())
        return data.get("response", "").strip()
    except asyncio.TimeoutError:
        proc.kill()
        raise TimeoutError("Ollama request timed out")


async def generate_email(lead) -> tuple[str, str]:
    name = lead.contact_name or ""
    company = lead.company_name or ""
    category = lead.service_category or "general_electrical"
    urgency = lead.urgency or "medium"
    service_desc = SERVICE_OFFERS.get(category, SERVICE_OFFERS["general_electrical"])
    opening = URGENCY_LINES.get(urgency, URGENCY_LINES["medium"])
    city = lead.city or lead.zip_code or "Los Angeles"

    greeting = f"{name}" if name else f"team at {company}" if company else "there"

    prompt = f"""Write a short email from Amy, an LA electrical contractor, to {greeting} at {company}.

Key details:
- Recipient: {greeting}
- Service: {service_desc}
- Opening line: {opening}
- Location: {city}

Write 3 short paragraphs: intro, value prop with the service mentioned naturally, CTA for a free quote. Max 100 words. No markdown. No placeholders."""

    subject = f"Electrical partner for {company or city} — Amy Electric"
    body = await _ollama_generate(prompt)
    body = body.replace("**", "").replace("Subject: ", "").strip()

    return subject, body


async def send_email(to_email: str, subject: str, body: str) -> bool:
    logger.info(f"[DRY-RUN] To: {to_email} | Subject: {subject}")
    return True


async def run_outreach(dry_run: bool = True, max_leads: int = MAX_BATCH):
    from app.database.session import async_session, init_db
    from app.database.models import Lead
    from sqlalchemy import select

    await init_db()

    async with async_session() as db:
        result = await db.execute(
            select(Lead)
            .where(Lead.email.isnot(None)).where(Lead.email != "")
            .order_by(Lead.score.desc())
            .limit(max_leads)
        )
        leads = result.scalars().all()

    leads = [l for l in leads if not (l.extra_data or {}).get("outreach", {}).get("status")]

    if not leads:
        print("No leads to contact")
        return

    print(f"Processing {len(leads)} leads for outreach")
    sent = 0
    failed = 0

    for lead in leads:
        try:
            subject, body = await generate_email(lead)

            if dry_run:
                print(f"\n{'='*50}")
                print(f"To: {lead.email}")
                print(f"Company: {lead.company_name}")
                print(f"Subject: {subject}")
                print(f"Body:\n{body}")
                print(f"{'='*50}")
                sent_status = "dry_run"
            else:
                ok = await send_email(lead.email, subject, body)
                sent_status = "sent" if ok else "failed"

            extra = lead.extra_data or {}
            if isinstance(extra, str):
                extra = {}
            outreach = extra.get("outreach", {})
            outreach.update({
                "status": sent_status,
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "subject": subject,
                "body_preview": body[:200],
            })
            extra["outreach"] = outreach
            lead.extra_data = extra

            if sent_status != "failed":
                sent += 1

        except Exception as e:
            logger.exception(f"Failed outreach to {lead.email}")
            extra = lead.extra_data or {}
            if isinstance(extra, str):
                extra = {}
            outreach = extra.get("outreach", {})
            outreach.update({"status": "error", "error": str(e)})
            extra["outreach"] = outreach
            lead.extra_data = extra
            failed += 1

    async with async_session() as db:
        for lead in leads:
            db.add(lead)
        await db.commit()

    print(f"\nOutreach complete: {sent} generated, {failed} failed")
