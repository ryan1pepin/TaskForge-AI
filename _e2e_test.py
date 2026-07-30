"""E2E smoke test for TaskForge AI backend."""
import requests, sys

BASE = "http://localhost:8000"
results = []

def step(name, resp, ok_codes=(200, 201, 204)):
    ok = resp.status_code in ok_codes
    icon = "PASS" if ok else "FAIL"
    detail = ""
    if not ok and len(resp.content) < 300:
        detail = f" body={resp.text[:120]}"
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: HTTP {resp.status_code}{detail}")
    return ok

print("=== Backend E2E Test ===")

# 1. Health
step("Health", requests.get(f"{BASE}/health"))

# 2. Register + Login
r = requests.post(f"{BASE}/api/v1/auth/register", json={"email": "demo@demo.com", "password": "DemoPass123!"})
step("Register", r, (200,))

login = requests.post(f"{BASE}/api/v1/auth/login", json={"email": "demo@demo.com", "password": "DemoPass123!"})
if login.status_code == 200:
    print(f"  [PASS] Login: HTTP {login.status_code}")
    results.append(True)
else:
    print(f"  [FAIL] Login: HTTP {login.status_code} body={login.text[:100]}")
    results.append(False)

token_data = login.json() if login.status_code == 200 else {}
token = token_data.get("access_token", "")
auth = {"Authorization": f"Bearer {token}"} if token else {}

# 3. OpenAPI docs exist
step("OpenAPI spec", requests.get(f"{BASE}/openapi.json"))
step("Swagger UI", requests.get(f"{BASE}/docs"))

# 4. Create project
r = requests.post(f"{BASE}/api/v1/projects/", json={"title": "My Project", "description": "test"}, headers=auth)
step("Create project", r, (200,)) if token else results.append(False)

if r.status_code in (200,) and token:
    pid = r.json().get("id", "")
    
    # 5. List projects
    step("List projects", requests.get(f"{BASE}/api/v1/projects/active", headers=auth))
    
    # 6. Create task
    r2 = requests.post(f"{BASE}/api/v1/tasks/", json={"project_id": pid, "title": "Test Task", "description": "smoke test"}, 
        headers=auth)
    step("Create task", r2, (200,)) if token else results.append(False)
    
    # 7. List project tasks
    tid = ""
    if r2.status_code == 200:
        tid = str(r2.json().get("id", ""))
        step("List tasks", requests.get(f"{BASE}/api/v1/projects/{pid}/tasks/active", headers=auth))
        
        # 8. Update task status
        r3 = requests.put(f"{BASE}/api/v1/tasks/{tid}", json={"status": "in_progress"}, headers=auth)
        if token: step("Update task status", r3, (200,))
    
    # 9. Refresh token rotation
    refresh_token = token_data.get("refresh_token", "")
    step("Refresh token", requests.post(f"{BASE}/api/v1/auth/refresh", json={"refresh_token": refresh_token}) if refresh_token else requests.get("about:blank"), (200,))
    
    # 10. AI endpoint returns 400 without key (expected)
    r4 = requests.post(f"{BASE}/api/v1/projects/{pid}/tasks/{tid}/suggest-priority", headers=auth) if tid else None
    if r4:
        ai_ok = r4.status_code in (400, 500)
        print(f"  [{'PASS' if ai_ok else 'FAIL'}] AI suggest (no key → expected error): HTTP {r4.status_code}")
        results.append(ai_ok)

# 11. Logout
step("Logout", requests.post(f"{BASE}/api/v1/auth/logout", headers=auth), (200,))

print("\n" + "=" * 30)
passed = sum(1 for x in results if x)
total = len(results)
print(f"Results: {passed}/{total} passed")
if passed == total:
    print("ALL CHECKS PASSED")
else:
    print(f"{total - passed} failures detected")
