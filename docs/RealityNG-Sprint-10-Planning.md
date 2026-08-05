# RealityNG Sprint 10 Planning

## Planning Status

Sprint 10 has not started.

No approved Sprint 10 implementation scope was found in the repository documentation during closure. This document prepares the planning structure that leadership, product, and engineering should use before implementation begins.

## Recommended Sprint Objective

Recommended objective:

```text
Improve operational maturity and user-facing reliability of the Version 2 marketplace before adding another major business vertical.
```

This is recommended because Version 2 introduced a large surface area:

- Property marketplace
- Verification layer
- Demo assistant
- Location intelligence foundation
- Services marketplace
- Provider governance
- Reviews and complaints
- Admin moderation

Sprint 10 should consolidate the release, improve production confidence, and address the highest-value operational gaps before introducing another large workflow.

## Business Value

Sprint 10 should help RealityNG:

- Prepare for public beta growth.
- Reduce operational risk on the shared VPS.
- Improve trust and moderation throughput.
- Improve marketplace data quality.
- Make onboarding providers and customers smoother.
- Prepare the platform for future payments, messaging, or notifications without rushing into them.

## Recommended Sprint 10 Themes

### Theme 1: Production Observability

Business value:

- Faster incident response.
- Safer growth while RealityNG shares infrastructure with Caretekk.

Candidate work:

- Sentry release markers.
- Structured production error dashboards.
- Container restart alerts.
- Disk/RAM/swap monitoring.
- PostgreSQL connection and slow-query checks.
- Redis memory/eviction checks.
- MinIO storage growth checks.
- Cloudflare 4xx/5xx watch.

Complexity:

```text
Medium
```

### Theme 2: Admin Operations Readiness

Business value:

- Admins can manage verification, services, complaints, reviews, and appeals consistently.

Candidate work:

- Admin runbook.
- Queue priority rules.
- Moderation SLA definitions.
- Status explanation copy.
- Better admin empty/error states.
- CSV/export planning if required.

Complexity:

```text
Medium
```

### Theme 3: Provider Onboarding Quality

Business value:

- Services marketplace value depends on real approved provider inventory.

Candidate work:

- Provider onboarding checklist.
- Profile completeness improvements.
- Portfolio guidance.
- Service-area copy.
- Verification prompts.
- Admin review checklist.

Complexity:

```text
Medium
```

### Theme 4: Production Google Maps Activation

Business value:

- Improves location-aware property discovery.

Dependencies:

- Google Cloud billing approval.
- Restricted production browser key.
- Production coordinate population.
- Browser QA.

Complexity:

```text
Small to Medium
```

### Theme 5: Staging Load and Performance Validation

Business value:

- Establishes safe capacity estimates without risking Caretekk.

Candidate work:

- Temporary VPS or staging Docker stack.
- k6/Locust/Artillery scripts.
- Seed data.
- Baseline public/provider/admin endpoint measurements.
- Query profiling follow-ups.

Complexity:

```text
Medium
```

## Recommended Implementation Order

1. Confirm Sprint 10 theme and acceptance criteria with leadership.
2. Create backend and frontend Sprint 10 branches from latest `origin/main`.
3. Add observability and operational docs first.
4. Address low-risk admin/provider UX polish.
5. Run staging load/performance validation.
6. Activate Google Maps only if credentials and billing are ready.
7. Run full regression.
8. Prepare release notes and rollback plan.

## Architecture Impact

Expected architecture impact depends on final scope.

Likely low-impact work:

- Documentation
- Admin copy
- Dashboard polish
- Monitoring configuration
- Frontend UX refinements

Possible backend impact:

- Additional indexes from staging query profiling
- New observability settings
- Admin reporting endpoints if approved
- Data-quality fields only if leadership approves

Possible frontend impact:

- Admin queue improvements
- Provider onboarding guidance
- Public Maps activation behavior
- Better loading/error states

## Database Impact

Avoid database migrations in Sprint 10 unless there is a clear operational need.

Potential migrations only if approved:

- Indexes from measured query profiling
- Monitoring/audit metadata fields
- Provider data-quality fields
- Admin reporting models

Do not add migrations just for speculative future workflows.

## Dependencies

- Product approval for Sprint 10 objective
- Google Cloud billing if Maps activation is included
- Staging environment if load testing is included
- Admin/operator availability for workflow validation
- Vercel access if frontend production deployment is required

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Sprint 10 scope is too broad | Delays and regressions | Pick one primary theme. |
| Production load testing accidentally targets shared VPS | Caretekk disruption | Use staging only; keep production smoke tests tiny. |
| Maps activation proceeds without restricted key | API abuse/cost risk | Require billing/key checklist before activation. |
| Admin workflow changes bypass permissions | Security regression | Add permission tests for every new admin action. |
| Provider onboarding creates unverified trust claims | Brand trust issue | Keep verification badges separate from profile approval. |

## Suggested Sprint 10 Phase Structure

### Phase 1: Scope Confirmation

- Confirm objective.
- Confirm out-of-scope list.
- Confirm repositories involved.
- Confirm acceptance criteria.

### Phase 2: Branch and Baseline

- Branch from latest `origin/main`.
- Confirm clean working trees.
- Run baseline validations.

### Phase 3: Implementation

- Implement only approved scope.
- Preserve Version 2 workflows.
- Add tests with every permission-sensitive change.

### Phase 4: Validation

- Backend lint/check/migrations/OpenAPI/tests.
- Frontend lint/typecheck/tests/builds.
- Browser QA for impacted routes.

### Phase 5: Release Readiness

- Update docs.
- Update rollback notes.
- Confirm production smoke plan.
- Prepare deployment report template.

## Acceptance Criteria Template

Sprint 10 is ready for review when:

- Approved scope is complete.
- No Sprint 9 workflow regresses.
- Tests pass.
- Builds pass.
- OpenAPI is valid.
- Production rollout and rollback plan is documented.
- Caretekk safety constraints are preserved.

## Executive Recommendation

Start Sprint 10 with production observability and operational readiness unless leadership has a stronger commercial priority.

That gives the platform a safer base before the team adds heavier capabilities such as payments, messaging, notifications, subscriptions, or advanced booking.

