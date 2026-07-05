"""
Phase 6 smoke test — runs against a live server on localhost:8001.
Usage: python scripts/smoke_test.py
"""
import urllib.request
import urllib.error
import json
import sys

BASE = "http://localhost:8001/api"


def post(path, data, token=None):
    body = json.dumps(data).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code


def get(path, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code


def check(label, condition, detail=""):
    if condition:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}  {detail}")
        sys.exit(1)


print("\n=== Phase 6 Smoke Tests ===\n")

# 1. Login as seeded admin
data, status = post("/auth/login", {"email": "admin@lakshya.ai", "password": "admin123"})
check("1. Login returns 200", status == 200, data)
check("   access_token present", "access_token" in data)
check("   refresh_token present", "refresh_token" in data)
token = data["access_token"]
refresh = data["refresh_token"]

# 2. /me
data, status = get("/auth/me", token)
check("2. /me returns 200", status == 200, data)
check("   email correct", data.get("email") == "admin@lakshya.ai")
check("   is_email_verified=True (pre-verified in seed)", data.get("is_email_verified") is True)

# 3. Token refresh
data, status = post("/auth/refresh", {"refresh_token": refresh})
check("3. Token refresh returns 200", status == 200, data)
check("   new access_token", "access_token" in data)
new_token = data["access_token"]
new_refresh = data["refresh_token"]

# 4. Old refresh token is revoked after rotation
data_old, status_old = post("/auth/refresh", {"refresh_token": refresh})
check("4. Old refresh token rejected after rotation (401)", status_old == 401, data_old)

# 5. Deals are org-scoped
data, status = get("/deals/", new_token)
check("5. GET /deals returns 200", status == 200, data)
check("   Deals exist (seeded)", len(data) > 0)

# 6. Companies are org-scoped
data, status = get("/companies/", new_token)
check("6. GET /companies returns 200", status == 200, data)
check("   Companies exist (seeded)", len(data) > 0)

# 7. Org endpoint
data, status = get("/org", new_token)
check("7. GET /org returns 200", status == 200, data)
check("   Org name correct", data.get("name") == "Lakshya Demo Org")

# 8. Audit log accessible to owner
data, status = get("/org/audit-log", new_token)
check("8. Audit log returns 200", status == 200, data)

# 9. Register a second org, verify data isolation
data2, status2 = post("/auth/register", {
    "name": "Other User", "email": "other_smoke@test.com",
    "password": "password123", "org_name": "Other Corp"
})
check("9. Register second org returns 201", status2 == 201, data2)

data2, _ = post("/auth/login", {"email": "other_smoke@test.com", "password": "password123"})
other_token = data2["access_token"]
deals_other, _ = get("/deals/", other_token)
check("   Other org sees 0 deals (no data bleed)", len(deals_other) == 0,
      f"LEAK: saw {len(deals_other)} deals")

companies_other, _ = get("/companies/", other_token)
check("   Other org sees 0 companies (no data bleed)", len(companies_other) == 0,
      f"LEAK: saw {len(companies_other)} companies")

# 10. RBAC — member cannot access admin-only routes
# (create deal, then try to delete as member — need a member account)
# For now just verify owner can delete
data, status = get("/deals/", new_token)
if data:
    deal_id = data[0]["id"]
    # Member of second org tries to delete first org's deal — should 404 (not 403, data isolation first)
    del_data, del_status = post(f"/deals/{deal_id}", {}, token=other_token)
    # Actually test proper: owner can delete their own deal
    # (use DELETE verb via urllib)
    import urllib.request
    req = urllib.request.Request(
        f"{BASE}/deals/{deal_id}",
        method="DELETE",
        headers={"Authorization": f"Bearer {new_token}"}
    )
    try:
        with urllib.request.urlopen(req) as r:
            del_status = r.status
    except urllib.error.HTTPError as e:
        del_status = e.code
    check("10. Owner can delete deal (204)", del_status == 204, del_status)

# 11. Rate limiting on login
# Use a fresh unique email to avoid hitting the window from earlier runs
for i in range(6):
    post("/auth/login", {"email": "ratelimit_smoke@noemail.com", "password": "wrong"})
data_rl, status_rl = post("/auth/login", {"email": "ratelimit_smoke@noemail.com", "password": "wrong"})
check("11. Rate limit enforced after 6 attempts (429)", status_rl == 429, status_rl)

# 12. Logout revokes refresh token
data, status = post("/auth/logout", {"refresh_token": new_refresh})
check("12. Logout returns 200", status == 200, data)
# Refresh after logout should fail
data_after, status_after = post("/auth/refresh", {"refresh_token": new_refresh})
check("    Refresh after logout rejected (401)", status_after == 401, data_after)

print("\n=== ALL TESTS PASSED ===\n")
