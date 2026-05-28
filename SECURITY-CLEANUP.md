# Eye Budget — Security Cleanup Before Going Public

**Date:** 2026-05-28
**Status:** Pending

## Context

Security scan found credentials, personal data, and infrastructure details that must be removed before making the repo public.

## Prerequisites

- `git-filter-repo` installed (confirmed available)
- No uncommitted work (stash or commit first)
- Stash `stash@{0}` exists — save as patch before filter-repo

## Step 1: Backup

```bash
cp -r /home/pawel/projects/eye-budget /home/pawel/projects/eye-budget-backup
git stash show -p stash@{0} > /home/pawel/projects/eye-budget-stash.patch
```

## Step 2: Purge files from git history

`git filter-repo` rewrites ALL commits on ALL branches. After this every commit gets a new hash, origin remote is removed.

```bash
cd /home/pawel/projects/eye-budget
git filter-repo --invert-paths --path yoyo.ini --path input/
```

This removes:
- `yoyo.ini` — contained `postgresql://postgres:postgres@<SERVER_IP>:5432/db-eye-budget`
- `input/*.jpg` — ~25 real receipt photos with store names, prices, NIP numbers

## Step 3: Fix tracked files

### CRITICAL

| File | Issue | Fix |
|------|-------|-----|
| `SERVER-AGENT.md` | SSH public key `ssh-ed25519 AAAA...` | Remove or replace with `<SSH_PUBLIC_KEY>` |
| `.github/workflows/deploy.yml` | Nextcloud path hardcoded on line ~24 | Move to GitHub secret, replace with `${{ secrets.INPUT_DIR }}` |

### WARNING

| File | Issue | Fix |
|------|-------|-----|
| `README.md` | IP `<SERVER_IP>` (6 occurrences) | Replace with `<SERVER_IP>` |
| `CLAUDE.md` | IP `<SERVER_IP>` | Replace with `<SERVER_IP>` |
| `SERVER-AGENT.md` | IP, username, paths | Replace with placeholders |
| `docs/superpowers/specs/*.md` | IP references | Replace with `<SERVER_IP>` |
| `.github/workflows/deploy.yml` | IP in deployment summary | Replace with `<SERVER_IP>` |
| `scripts/set-github-secrets.sh` | `scp pawel@<SERVER_IP>:/home/pawel/...` | Remove real paths from comments |
| `backend/src/bank_inflow_salary_rules.py` | `pensja_pawel`, `pensja_ada` | Consider generalizing (optional — personal choice) |
| `backend/misc/db-scripts.sql` | Dev artifact | Consider removing or gitignoring |

### OPTIONAL

| Item | Issue | Fix |
|------|-------|-----|
| Git author email | `p.swierblewski@gmail.com` in all commits | Reconfigure to GitHub noreply before new commits, or use `git filter-repo --mailmap` to rewrite |
| `.cursor/`, `.vscode/` | IDE configs tracked | Add to `.gitignore` |

## Step 4: Commit cleanup

```bash
git add -A
git commit -m "security: remove credentials, IPs, and personal data before going public"
```

## Step 5: Restore remote and push

```bash
git remote add origin git@personal:pswierblewski/eye-budget.git
git push --force --all
git push --force --tags
```

**Warning:** `--force` overwrites ALL remote branches. Make sure no one else has work based on the old history.

## Step 6: Restore stash (optional)

```bash
git apply /home/pawel/projects/eye-budget-stash.patch
```

## Step 7: Post-cleanup

- [ ] Rotate PostgreSQL password on homeserver (old one is in git history until purged from GitHub)
- [ ] Verify on GitHub that `yoyo.ini` and `input/` are gone from all commits
- [ ] Delete backup after confirming everything works

---

# Legal Parrot API — Security Cleanup

**Repo:** https://github.com/pswierblewski/legal-parrot-api
**Local:** `/home/pawel/projects/legal-parrot-api`
**Note:** Single commit repo — no history rewrite needed, just fix and amend/commit.

## CRITICAL

### 1. DB credentials in `db/liquibase.properties` (line 4)

```
username: postgres
password: postgres
```

**Fix:** Replace with env var placeholders or add `db/liquibase.properties` to `.gitignore`.

### 2. JWT decoded without signature verification in `legal_parrot_api/auth.py` (line 114)

```python
decoded = jwt.decode(token, verify=False)
```

Attacker can forge arbitrary scope claims and bypass authorization.

**Fix:** Add proper signature verification with a secret/public key.

## WARNING

| File | Issue | Fix |
|------|-------|-----|
| `docker-compose.yml`, `docker-compose-local.yml` | RabbitMQ exposed with default `guest/guest` credentials (ports 5672 + 15672) | Set credentials via env vars |
| `settings.py` (line 225) | `CORS_ORIGIN_ALLOW_ALL = True` | Restrict CORS origins for production |
| `docker-compose*.yml`, `.github/workflows/ci-*.yml` | GitLab registry references (`registry.gitlab.com/aiq-software/...`) expose internal org name | Replace with current registry or remove |
| `.github/workflows/ci-*.yml` | `StrictHostKeyChecking=no` in SSH connections | Remove or use known_hosts |
| `.github/workflows/ci-*.yml` | Full list of secret names visible in workflow (OPENAI_API_KEY, Dropbox tokens, etc.) | Acceptable — values are in GitHub secrets, just be aware |
| Git author | `p.swierblewski@gmail.com` in commits | Same as eye-budget — consider noreply |

## OK

- `.env` properly gitignored
- No hardcoded API keys or tokens in source
- No certificate files committed
- No database dumps or real user data
- Redis scripts use placeholder credentials
