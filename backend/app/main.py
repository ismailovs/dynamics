import json
import math
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .db import Database


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_iso(dt: datetime | None = None) -> str:
    current = dt or utc_now()
    return current.isoformat()


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


class LeadRequest(BaseModel):
    customer_name: str
    contact_channel: str = Field(description="phone|email|messenger")
    contact_value: str
    request_text: str


class MissedCallRequest(BaseModel):
    phone_number: str
    reason: str = "No agent available"


class EstimateRequest(BaseModel):
    customer_name: str
    amount: float
    follow_up_in_hours: int = 24


class JobRequest(BaseModel):
    title: str
    required_skill: str
    latitude: float
    longitude: float


class MaintenancePlanRequest(BaseModel):
    customer_name: str
    asset_name: str
    next_service_date: str
    interval_days: int = 180


class SolarProposalRequest(BaseModel):
    customer_name: str
    system_kw: float
    site_address: str


class PermitRequest(BaseModel):
    owner_name: str
    project_type: str
    city: str
    notes: str = ""


class QuoteRequest(BaseModel):
    customer_name: str
    service_type: str
    labor_hours: float
    materials_cost: float
    urgency: str = "standard"


def score_priority(text: str) -> str:
    lower = text.lower()
    if any(term in lower for term in ("fire", "sparking", "outage", "burning")):
        return "urgent"
    if any(term in lower for term in ("flicker", "panel", "breaker")):
        return "high"
    return "normal"


def ai_qualification_script(lead: LeadRequest) -> tuple[bool, str]:
    priority = score_priority(lead.request_text)
    qualified = len(lead.request_text.strip()) > 12 and "spam" not in lead.request_text.lower()
    summary = (
        f"AI intake: {lead.customer_name} requested '{lead.request_text}'. "
        f"Priority={priority}. Qualified={qualified}. Next step=auto acknowledge and dispatch readiness check."
    )
    return qualified, summary


def distance_score(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    return math.sqrt((lat_a - lat_b) ** 2 + (lon_a - lon_b) ** 2)


def create_app(db_path: str | None = None) -> FastAPI:
    app = FastAPI(title="Automative OS MVP", version="0.1.0")
    database = Database(db_path or os.getenv("APP_DB_PATH", "backend/data/mvp.sqlite3"))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    app.mount("/assets", StaticFiles(directory=frontend_dir), name="assets")

    def send_message(channel: str, target: str, body: str, context_type: str, context_id: int | None) -> int:
        return database.execute(
            """
            INSERT INTO messages(channel, target, body, context_type, context_id, sent_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (channel, target, body, context_type, context_id, utc_iso()),
        )

    def assign_technician(job_id: int, required_skill: str, latitude: float, longitude: float) -> dict:
        candidates = database.query_all("SELECT * FROM technicians WHERE available = 1")
        best = None
        best_score = None
        for tech in candidates:
            skill_match = required_skill.lower() in tech["skills"].lower()
            if not skill_match:
                continue
            score = distance_score(latitude, longitude, tech["latitude"], tech["longitude"])
            if best_score is None or score < best_score:
                best = tech
                best_score = score
        if not best:
            return {"assigned": False, "reason": "No available qualified technician"}

        database.execute(
            "UPDATE jobs SET technician_id = ?, status = ? WHERE id = ?",
            (best["id"], "assigned", job_id),
        )
        send_message(
            channel="dispatch",
            target=best["name"],
            body=f"New job assigned: {required_skill} - job #{job_id}",
            context_type="job",
            context_id=job_id,
        )
        return {"assigned": True, "technician": best}

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "time": utc_iso()}

    @app.post("/api/leads")
    def create_lead(payload: LeadRequest) -> dict:
        qualified, summary = ai_qualification_script(payload)
        priority = score_priority(payload.request_text)
        lead_id = database.execute(
            """
            INSERT INTO leads(customer_name, contact_channel, contact_value, request_text, priority, qualified, ai_summary, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.customer_name,
                payload.contact_channel,
                payload.contact_value,
                payload.request_text,
                priority,
                int(qualified),
                summary,
                utc_iso(),
                "new",
            ),
        )
        acknowledgment = (
            "Thanks for contacting us. We received your request and are qualifying it now. "
            "A scheduler will provide the next available slot shortly."
        )
        send_message(
            channel=payload.contact_channel,
            target=payload.contact_value,
            body=acknowledgment,
            context_type="lead",
            context_id=lead_id,
        )
        return {
            "lead_id": lead_id,
            "qualified": qualified,
            "priority": priority,
            "ai_summary": summary,
            "acknowledgment": acknowledgment,
        }

    @app.get("/api/leads")
    def list_leads() -> list[dict]:
        return database.query_all("SELECT * FROM leads ORDER BY id DESC")

    @app.post("/api/calls/missed")
    def missed_call(payload: MissedCallRequest) -> dict:
        call_id = database.execute(
            """
            INSERT INTO calls(phone_number, reason, status, created_at, text_back_sent_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (payload.phone_number, payload.reason, "missed", utc_iso(), utc_iso()),
        )
        text_back = (
            "Sorry we missed your call. Reply with your service address and issue type, "
            "and we will auto-schedule the next available licensed technician."
        )
        send_message("sms", payload.phone_number, text_back, "call", call_id)
        return {"call_id": call_id, "text_back_sent": True, "message": text_back}

    @app.post("/api/estimates")
    def create_estimate(payload: EstimateRequest) -> dict:
        follow_up_at = utc_now() + timedelta(hours=payload.follow_up_in_hours)
        estimate_id = database.execute(
            """
            INSERT INTO estimates(customer_name, amount, status, follow_up_at, follow_up_sent_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (payload.customer_name, payload.amount, "sent", utc_iso(follow_up_at), None, utc_iso()),
        )
        return {"estimate_id": estimate_id, "follow_up_at": utc_iso(follow_up_at)}

    @app.get("/api/estimates")
    def list_estimates() -> list[dict]:
        return database.query_all("SELECT * FROM estimates ORDER BY id DESC")

    @app.post("/api/jobs")
    def create_job(payload: JobRequest) -> dict:
        job_id = database.execute(
            """
            INSERT INTO jobs(title, required_skill, latitude, longitude, status, technician_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (payload.title, payload.required_skill, payload.latitude, payload.longitude, "pending", None, utc_iso()),
        )
        assignment = assign_technician(job_id, payload.required_skill, payload.latitude, payload.longitude)
        return {"job_id": job_id, "assignment": assignment}

    @app.get("/api/jobs")
    def list_jobs() -> list[dict]:
        return database.query_all(
            """
            SELECT jobs.*, technicians.name AS technician_name
            FROM jobs
            LEFT JOIN technicians ON jobs.technician_id = technicians.id
            ORDER BY jobs.id DESC
            """
        )

    @app.get("/api/dispatch/dashboard")
    def dispatch_dashboard() -> dict:
        technicians = database.query_all("SELECT * FROM technicians ORDER BY id")
        jobs = database.query_all(
            """
            SELECT jobs.*, technicians.name AS technician_name
            FROM jobs
            LEFT JOIN technicians ON jobs.technician_id = technicians.id
            ORDER BY jobs.id DESC
            """
        )
        return {"technicians": technicians, "jobs": jobs}

    @app.post("/api/maintenance/plans")
    def create_maintenance_plan(payload: MaintenancePlanRequest) -> dict:
        plan_id = database.execute(
            """
            INSERT INTO maintenance_plans(customer_name, asset_name, next_service_date, interval_days, last_reminder_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (payload.customer_name, payload.asset_name, payload.next_service_date, payload.interval_days, None),
        )
        return {"plan_id": plan_id}

    @app.get("/api/maintenance/plans")
    def list_maintenance_plans() -> list[dict]:
        return database.query_all("SELECT * FROM maintenance_plans ORDER BY id DESC")

    @app.post("/api/solar/proposals")
    def create_solar_proposal(payload: SolarProposalRequest) -> dict:
        doc_payload = {
            "site_address": payload.site_address,
            "system_kw": payload.system_kw,
            "steps": ["utility interconnection form", "permit intake", "design package"],
        }
        doc_id = database.execute(
            """
            INSERT INTO documents(doc_type, owner_name, payload_json, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("solar_packet", payload.customer_name, json.dumps(doc_payload), "generated", utc_iso()),
        )
        proposal_id = database.execute(
            """
            INSERT INTO solar_proposals(customer_name, system_kw, status, doc_packet_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (payload.customer_name, payload.system_kw, "draft_ready", doc_id, utc_iso()),
        )
        send_message(
            "email",
            payload.customer_name,
            f"Solar proposal workflow started. Document packet #{doc_id} is ready for review.",
            "solar_proposal",
            proposal_id,
        )
        return {"proposal_id": proposal_id, "doc_packet_id": doc_id}

    @app.get("/api/solar/proposals")
    def list_solar_proposals() -> list[dict]:
        return database.query_all("SELECT * FROM solar_proposals ORDER BY id DESC")

    @app.post("/api/permits/generate")
    def generate_permit(payload: PermitRequest) -> dict:
        permit_document = {
            "project_type": payload.project_type,
            "city": payload.city,
            "notes": payload.notes,
            "required_docs": ["license copy", "insurance certificate", "scope of work"],
        }
        doc_id = database.execute(
            """
            INSERT INTO documents(doc_type, owner_name, payload_json, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("permit_packet", payload.owner_name, json.dumps(permit_document), "generated", utc_iso()),
        )
        return {"document_id": doc_id, "document": permit_document}

    @app.post("/api/quotes/generate")
    def generate_quote(payload: QuoteRequest) -> dict:
        urgency_multiplier = {"standard": 1.0, "priority": 1.15, "emergency": 1.3}.get(payload.urgency, 1.0)
        labor_rate = 125.0
        subtotal = payload.labor_hours * labor_rate + payload.materials_cost
        total = round(subtotal * urgency_multiplier, 2)
        notes = (
            f"Generated with quote assistant: labor={payload.labor_hours}h @ ${labor_rate}/h, "
            f"materials=${payload.materials_cost}, urgency={payload.urgency}."
        )
        quote_id = database.execute(
            """
            INSERT INTO quotes(customer_name, service_type, labor_hours, materials_cost, total, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.customer_name,
                payload.service_type,
                payload.labor_hours,
                payload.materials_cost,
                total,
                notes,
                utc_iso(),
            ),
        )
        return {"quote_id": quote_id, "total": total, "notes": notes}

    @app.get("/api/quotes")
    def list_quotes() -> list[dict]:
        return database.query_all("SELECT * FROM quotes ORDER BY id DESC")

    @app.post("/api/automation/run")
    def run_automation() -> dict:
        now = utc_now()
        estimate_actions = []
        maintenance_actions = []

        due_estimates = database.query_all(
            """
            SELECT * FROM estimates
            WHERE follow_up_sent_at IS NULL AND status = 'sent'
            """
        )
        for est in due_estimates:
            if parse_iso(est["follow_up_at"]) <= now:
                body = (
                    f"Follow-up: estimate #{est['id']} for {est['customer_name']} is ready for approval."
                )
                send_message("email", est["customer_name"], body, "estimate", est["id"])
                database.execute(
                    "UPDATE estimates SET follow_up_sent_at = ?, status = ? WHERE id = ?",
                    (utc_iso(), "follow_up_sent", est["id"]),
                )
                estimate_actions.append(est["id"])

        due_plans = database.query_all("SELECT * FROM maintenance_plans")
        for plan in due_plans:
            if parse_iso(plan["next_service_date"]) <= now:
                body = (
                    f"Maintenance reminder for {plan['asset_name']}: schedule your preventive service now."
                )
                send_message("sms", plan["customer_name"], body, "maintenance", plan["id"])
                next_date = parse_iso(plan["next_service_date"]) + timedelta(days=plan["interval_days"])
                database.execute(
                    "UPDATE maintenance_plans SET next_service_date = ?, last_reminder_at = ? WHERE id = ?",
                    (utc_iso(next_date), utc_iso(), plan["id"]),
                )
                maintenance_actions.append(plan["id"])

        return {
            "estimate_follow_ups_sent": estimate_actions,
            "maintenance_reminders_sent": maintenance_actions,
        }

    @app.get("/api/messages")
    def list_messages() -> list[dict]:
        return database.query_all("SELECT * FROM messages ORDER BY id DESC")

    @app.get("/api/documents")
    def list_documents() -> list[dict]:
        docs = database.query_all("SELECT * FROM documents ORDER BY id DESC")
        for doc in docs:
            doc["payload_json"] = json.loads(doc["payload_json"])
        return docs

    @app.get("/api/kpi/dashboard")
    def kpi_dashboard() -> dict:
        total_leads = database.query_one("SELECT COUNT(*) AS value FROM leads")["value"]
        qualified_leads = database.query_one(
            "SELECT COUNT(*) AS value FROM leads WHERE qualified = 1"
        )["value"]
        assigned_jobs = database.query_one(
            "SELECT COUNT(*) AS value FROM jobs WHERE status = 'assigned'"
        )["value"]
        follow_ups_sent = database.query_one(
            "SELECT COUNT(*) AS value FROM estimates WHERE follow_up_sent_at IS NOT NULL"
        )["value"]
        quotes_total = database.query_one("SELECT COUNT(*) AS value FROM quotes")["value"]
        revenue_projection = database.query_one(
            "SELECT COALESCE(SUM(total), 0) AS value FROM quotes"
        )["value"]

        conversion = round((qualified_leads / total_leads) * 100, 2) if total_leads else 0.0
        return {
            "lead_conversion_percent": conversion,
            "qualified_leads": qualified_leads,
            "total_leads": total_leads,
            "assigned_jobs": assigned_jobs,
            "estimate_follow_ups_sent": follow_ups_sent,
            "quotes_generated": quotes_total,
            "revenue_projection": revenue_projection,
        }

    @app.get("/")
    def frontend() -> FileResponse:
        index_file = frontend_dir / "index.html"
        if not index_file.exists():
            raise HTTPException(status_code=404, detail="Frontend not found")
        return FileResponse(index_file)

    return app


app = create_app()
