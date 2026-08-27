import requests

BASE = "http://127.0.0.1:5000"

s = requests.Session()
print("=== Login estudiante ===")
r = s.post(f"{BASE}/login", data={"email": "estudiante@5to-a.cardinalshalom.edu.do", "password": "Demo1234!"})
print(f"login status: {r.status_code}")
print(f"redirect: {r.url}")
print()

def check(desc, r, expected=200):
    ok = r.status_code == expected
    print(f"[{'OK' if ok else 'FAIL'}] {desc} -> {r.status_code}")
    if not ok:
        print(f"  body preview: {r.text[:200]}")
    return ok

print("=== Student views ===")
check("student/library", s.get(f"{BASE}/student/library"))
check("student/my-tasks", s.get(f"{BASE}/student/my-tasks"))
check("student/my-grades", s.get(f"{BASE}/student/my-grades"))
check("student/ranking", s.get(f"{BASE}/student/ranking"))
check("student/portfolio", s.get(f"{BASE}/student/portfolio"))

print()
print("=== Chatbot ===")
r = s.post(f"{BASE}/api/chatbot/query", data={"query": "libros"})
print(f"chatbot status: {r.status_code}")
if r.ok:
    print(f"response: {r.json()['response'][:90]}")

print()
print("=== Public library ===")
check("library (public)", s.get(f"{BASE}/library"), expected=200)

print()
print("=== Admin no-code (super_admin) ===")
s2 = requests.Session()
r = s2.post(f"{BASE}/login", data={"email": "super_admin@cardinalshalom.edu.do", "password": "Demo1234!"})
print(f"super_admin login: {r.status_code}")
check("admin/no-code", s2.get(f"{BASE}/admin/no-code"))

print()
print("=== Teacher views ===")
s3 = requests.Session()
r = s3.post(f"{BASE}/login", data={"email": "profesor@cardinalshalom.edu.do", "password": "Demo1234!"})
print(f"teacher login: {r.status_code}")
check("teacher/my-classes", s3.get(f"{BASE}/teacher/my-classes"))
check("teacher/library-manager", s3.get(f"{BASE}/teacher/library-manager"))
check("teacher/ra/1", s3.get(f"{BASE}/teacher/ra/1"))

print()
print("=== Academic admin ===")
s4 = requests.Session()
r = s4.post(f"{BASE}/login", data={"email": "academic_admin@cardinalshalom.edu.do", "password": "Demo1234!"})
print(f"academic_admin login: {r.status_code}")
check("admin/approvals", s4.get(f"{BASE}/admin/approvals"))
check("academic/grades-overview", s4.get(f"{BASE}/academic/grades-overview"))

print()
print("=== Activity admin ===")
s5 = requests.Session()
r = s5.post(f"{BASE}/login", data={"email": "activity_admin@cardinalshalom.edu.do", "password": "Demo1234!"})
print(f"activity_admin login: {r.status_code}")
check("activity/admin", s5.get(f"{BASE}/activity/admin"))

print()
print("=== System mode toggle (super_admin) ===")
r = s.post(f"{BASE}/settings/system-mode", data={"system_mode": "vacations"})
print(f"system_mode POST status: {r.status_code}")
if r.ok:
    print(f"system_mode: {r.json().get('system_mode')}")

print()
print("=== Renovacion de grado (student) ===")
check("student/renewal-request (GET)", s.get(f"{BASE}/student/renewal-request"))
r = s.post(f"{BASE}/student/renewal-request", data={"requested_grade_id": 1})
print(f"renewal request POST: {r.status_code}")

print()
print("=== Dashboard estudiante (vacations mode) ===")
check("dashboard (student)", s.get(f"{BASE}/dashboard"))
print(f"  contiene Vacaciones: {'Vacaciones' in s.get(f'{BASE}/dashboard').text}")
