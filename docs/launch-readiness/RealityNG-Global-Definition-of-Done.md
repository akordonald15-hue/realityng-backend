# RealityNG Global Launch Definition of Done

Status: planning locked

## Code

- backend lint passes;
- Django check passes;
- migration check passes;
- clean PostgreSQL migration passes;
- full backend PostgreSQL regression passes;
- frontend lint passes;
- frontend typecheck passes;
- frontend tests pass;
- mock and real API builds pass;
- OpenAPI validates with no new errors;
- generated artifacts are not committed accidentally.

## Security

- authorization reviewed;
- IDOR tested across roles and personas;
- revoked/suspended assignment behavior tested;
- private files protected;
- signed URLs require authorization;
- upload validation tested;
- secrets absent from frontend bundles and docs;
- financial workflows are backend-authoritative;
- webhook/idempotency/race controls tested;
- sensitive logging reviewed.

## Infrastructure

- staging exists;
- dedicated production environment ready before broad public launch;
- PostgreSQL backups and restore verified;
- Redis health and queue behavior monitored;
- object storage bucket classifications documented;
- Celery and Beat monitored;
- ASGI/WebSockets routed correctly;
- rollback procedure rehearsed;
- monitoring and alerting active.

## Product

- critical user journeys pass;
- mobile/responsive QA completed;
- browser support matrix documented;
- placeholder/mock/fake public content removed;
- support and safety flows visible;
- empty, loading, and error states checked;
- high-risk financial/verification/inspection wording approved.

## Compliance

- privacy policy approved;
- terms and conditions approved;
- data retention/deletion rules approved;
- consent matrix approved;
- escrow/financing boundaries approved;
- moderation/fraud/complaint procedures approved;
- required professional review recorded.

## Operations

- incident process defined;
- support process defined;
- moderation ownership assigned;
- daily beta monitoring routine defined;
- launch risk register reviewed;
- public launch go/no-go signed off.

