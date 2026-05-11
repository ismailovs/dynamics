from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_mvp_workflows(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    app = create_app(str(db_path))
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    lead_payload = {
        "customer_name": "North Plant",
        "contact_channel": "email",
        "contact_value": "ops@northplant.io",
        "request_text": "Sparking panel and outage risk in section B",
    }
    lead_response = client.post("/api/leads", json=lead_payload)
    assert lead_response.status_code == 200
    lead_data = lead_response.json()
    assert lead_data["qualified"] is True
    assert lead_data["priority"] in {"high", "urgent"}

    missed_call = client.post(
        "/api/calls/missed",
        json={"phone_number": "+16145551212", "reason": "After-hours"},
    )
    assert missed_call.status_code == 200
    assert missed_call.json()["text_back_sent"] is True

    estimate = client.post(
        "/api/estimates",
        json={"customer_name": "North Plant", "amount": 1250.0, "follow_up_in_hours": 0},
    )
    assert estimate.status_code == 200

    maintenance_due = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    maintenance = client.post(
        "/api/maintenance/plans",
        json={
            "customer_name": "North Plant",
            "asset_name": "Main breaker",
            "next_service_date": maintenance_due,
            "interval_days": 30,
        },
    )
    assert maintenance.status_code == 200

    job = client.post(
        "/api/jobs",
        json={
            "title": "Breaker replacement",
            "required_skill": "breaker",
            "latitude": 39.96,
            "longitude": -82.99,
        },
    )
    assert job.status_code == 200
    assert job.json()["assignment"]["assigned"] is True

    quote = client.post(
        "/api/quotes/generate",
        json={
            "customer_name": "North Plant",
            "service_type": "panel_upgrade",
            "labor_hours": 4,
            "materials_cost": 1200,
            "urgency": "priority",
        },
    )
    assert quote.status_code == 200
    assert quote.json()["total"] > 0

    permit = client.post(
        "/api/permits/generate",
        json={
            "owner_name": "North Plant",
            "project_type": "Commercial panel permit",
            "city": "Columbus",
            "notes": "Rush filing",
        },
    )
    assert permit.status_code == 200
    assert permit.json()["document_id"] > 0

    solar = client.post(
        "/api/solar/proposals",
        json={
            "customer_name": "North Plant",
            "system_kw": 42,
            "site_address": "101 Grid Ave, Columbus, OH",
        },
    )
    assert solar.status_code == 200
    assert solar.json()["doc_packet_id"] > 0

    automation = client.post("/api/automation/run", json={})
    assert automation.status_code == 200
    automation_data = automation.json()
    assert len(automation_data["estimate_follow_ups_sent"]) == 1
    assert len(automation_data["maintenance_reminders_sent"]) == 1

    dashboard = client.get("/api/kpi/dashboard")
    assert dashboard.status_code == 200
    kpi = dashboard.json()
    assert kpi["total_leads"] >= 1
    assert kpi["assigned_jobs"] >= 1
    assert kpi["quotes_generated"] >= 1

    messages = client.get("/api/messages")
    assert messages.status_code == 200
    assert len(messages.json()) >= 4
