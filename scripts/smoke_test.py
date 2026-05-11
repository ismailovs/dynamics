import json
import sys
import urllib.request


BASE_URL = "http://127.0.0.1:8000"


def post(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    health = get("/api/health")
    if health.get("status") != "ok":
        print("Health check failed", health)
        return 1

    lead = post(
        "/api/leads",
        {
            "customer_name": "Smoke Test Co",
            "contact_channel": "email",
            "contact_value": "ops@smoketest.co",
            "request_text": "Urgent breaker issue with frequent tripping",
        },
    )
    post("/api/calls/missed", {"phone_number": "+16145559999", "reason": "No answer"})
    post("/api/estimates", {"customer_name": "Smoke Test Co", "amount": 995, "follow_up_in_hours": 0})
    post(
        "/api/jobs",
        {
            "title": "Dispatch smoke test",
            "required_skill": "service",
            "latitude": 39.96,
            "longitude": -82.99,
        },
    )
    post(
        "/api/maintenance/plans",
        {
            "customer_name": "Smoke Test Co",
            "asset_name": "Main panel",
            "next_service_date": "2020-01-01T00:00:00+00:00",
            "interval_days": 180,
        },
    )
    post(
        "/api/solar/proposals",
        {
            "customer_name": "Smoke Test Co",
            "system_kw": 12.5,
            "site_address": "1 Main St, Columbus, OH",
        },
    )
    post(
        "/api/permits/generate",
        {
            "owner_name": "Smoke Test Co",
            "project_type": "Electrical service upgrade",
            "city": "Columbus",
            "notes": "Smoke permit packet",
        },
    )
    quote = post(
        "/api/quotes/generate",
        {
            "customer_name": "Smoke Test Co",
            "service_type": "service_upgrade",
            "labor_hours": 5,
            "materials_cost": 650,
            "urgency": "priority",
        },
    )
    automation = post("/api/automation/run", {})
    kpi = get("/api/kpi/dashboard")
    messages = get("/api/messages")

    print("Lead:", lead["lead_id"])
    print("Quote Total:", quote["total"])
    print("Automation:", automation)
    print("KPI:", kpi)
    print("Messages Count:", len(messages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
