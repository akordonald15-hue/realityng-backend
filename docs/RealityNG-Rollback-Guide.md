# RealityNG Rollback Guide

## Purpose

This guide describes how to roll back a RealityNG production deployment without disrupting Caretekk, which shares the same VPS and Nginx routing layer.

Do not delete Docker volumes. Do not run Docker prune. Do not restart the Caretekk stack.

## Known Existing Rollback Assets

Verify these existing assets before deployment:

- `/opt/realityng/backups/release-s6-s7-20260727-133926`
- `/root/telehealthapp/nginx/default.conf.realityng-s67-backup-20260727-134949`

Create a new Sprint 9 rollback point before the deployment and record its path in the deployment report.

## Rollback Levels

### Level 1: Frontend Rollback

Use when the API is healthy but the frontend release has a regression.

Preferred Vercel rollback:

1. Open the RealityNG Vercel project.
2. Select the last known good production deployment.
3. Promote or redeploy it.
4. Confirm environment variables remain:
   ```env
   NEXT_PUBLIC_USE_MOCKS=false
   NEXT_PUBLIC_API_BASE_URL=https://api.realityng.com/api/v1
   ```
5. Verify `https://www.realityng.com`.

Git rollback alternative:

```bash
git checkout main
git revert <frontend_release_commit>
git push origin main
```

Use this only if repository history should explicitly contain the rollback.

### Level 2: Backend Code Rollback

Use when backend code is unhealthy but database state is still compatible.

```bash
cd /opt/realityng/backend
git fetch origin
git checkout <last_known_good_backend_commit>
docker compose -p realityng -f docker-compose.yml -f compose.production.yaml up -d --no-deps --build backend
docker compose -p realityng -f docker-compose.yml -f compose.production.yaml exec backend python manage.py check
curl -i https://api.realityng.com/api/v1/health/
```

Do not recreate PostgreSQL, Redis, or MinIO for a code-only rollback.

### Level 3: Backend Code and Database Restore

Use only when a migration or data issue requires restoring the database.

1. Stop only the RealityNG backend service:
   ```bash
   docker compose -p realityng -f docker-compose.yml -f compose.production.yaml stop backend
   ```

2. Restore the PostgreSQL dump from the verified backup.

3. Check out the matching backend commit:
   ```bash
   cd /opt/realityng/backend
   git checkout <matching_backend_commit>
   ```

4. Start backend only:
   ```bash
   docker compose -p realityng -f docker-compose.yml -f compose.production.yaml up -d --no-deps --build backend
   ```

5. Validate:
   ```bash
   curl -i https://api.realityng.com/api/v1/health/
   docker compose -p realityng ps
   ```

Database restore should be approved before execution because data created after the backup may be lost.

### Level 4: Nginx Routing Rollback

This Sprint 9 release should not require Nginx changes.

If Nginx was changed for a RealityNG-only route:

1. Restore the backed-up Nginx configuration file.
2. Validate inside the Nginx container:
   ```bash
   docker exec telehealthapp-nginx-1 nginx -t
   ```
3. Reload gracefully only if validation passes:
   ```bash
   docker exec telehealthapp-nginx-1 nginx -s reload
   ```
4. Verify:
   ```bash
   curl -i https://api.realityng.com/api/v1/health/
   curl -i https://api.caretekk.com/health/
   ```

Do not restart the Telehealth/Caretekk Compose project.

## Post-Rollback Checks

After any rollback:

- RealityNG health returns 200
- Caretekk health returns 200
- RealityNG frontend is reachable
- Authentication works
- Services public listing works
- Property marketplace still works
- No container restart loop exists
- PostgreSQL, Redis, and MinIO are healthy
- Nginx remains valid
- Working rollback commit is recorded

## Communication Template

Record:

- Reason for rollback
- Time rollback started
- Time rollback completed
- Components rolled back
- Database restored: yes/no
- Last known good backend commit
- Last known good frontend commit
- Health-check results
- Follow-up fix owner

