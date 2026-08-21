# RealityNG Sprint 15 Persona E2E Matrix

Status: automated journeys complete; visual/device execution blocked

| Persona | Automated journey evidence | Status |
| --- | --- | --- |
| Anonymous | Public properties/providers; protected actions rejected | PASS |
| Buyer/tenant | Auth, favorites, inquiry, viewing, application, messaging, transaction, proof, financing | PASS |
| Landlord/owner | Property, inquiry/application, leads, transactions, escrow, construction visibility | PASS |
| Agent/property manager | Explicit property-capability access and negative role-only/revoked cases | PASS |
| Service provider | Profile, portfolio, quotes, reviews, complaints and appeals | PASS |
| Inspector | Assignment, evidence and report workflow; inactive assignment denied | PASS |
| Construction stakeholder/investor | Project/evidence visibility according to access level | PASS |
| Financing applicant | Application, consent, documents, offers and acceptance | PASS |
| Admin | Verification, service, inspection, construction, payment, escrow and financing operations | PASS |

The frontend regression covers 46 files and 91 tests across public, dashboard,
admin, property, service, financing and realtime surfaces. HTTP runtime smoke
previously returned 200 for home, sign-in, properties and dashboard routes.

Desktop/tablet/mobile visual inspection is BLOCKED because no in-app or
extension browser session was available. This matrix must not be treated as a
visual accessibility or responsive-layout approval.

