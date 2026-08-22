# RealityNG Sprint 15 Persona E2E Matrix

Status: passed in installed Google Chrome

Date: 2026-08-22

| Persona | Real-browser evidence | Status |
| --- | --- | --- |
| Anonymous | Home, auth, property and provider discovery; protected APIs remain protected | PASS |
| Buyer/tenant | Login, dashboard, inspection, transaction, escrow, financing and messaging surfaces | PASS |
| Landlord/owner | Login, dashboard, owned-property and two-way messaging journey | PASS |
| Agent/property manager | Active assignment permits management; valid revoked-manager upload request is denied by the API | PASS |
| Service provider | Authenticated provider dashboard and service workflow surfaces | PASS |
| Inspector | Active assignment renders; declined, cancelled, reassigned and unrelated access is denied | PASS |
| Financing applicant | Application, offer and private financing-document surfaces use partner-owned wording and signed access | PASS |
| Admin | Financing and other critical queue surfaces render; ordinary user receives 403 | PASS |
| Message nonparticipant | Thread REST resources are masked with 404 and WebSocket join is denied with 403 | PASS |

Responsive authenticated buyer surfaces were exercised at 1440x900, 1366x768,
768x1024, 390x844 and 360x800. The gate checks horizontal overflow and captures
desktop/mobile evidence. The frontend unit regression remains 46 files and 91
tests; those tests supplement rather than replace the real-browser results.
