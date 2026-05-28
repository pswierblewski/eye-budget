# Quickstart: CI/CD Pipeline Setup

**Feature**: `004-cicd-local-deploy` | **Date**: 2026-03-21

This document describes the one-time setup required on the Debian server (<SERVER_IP>) to enable automatic deployments.

---

## Prerequisites

- Debian server with Docker already installed (confirmed)
- Portainer running (confirmed)
- A GitHub account with admin access to the `eye-budget` repository

---

## Step 1: Create a dedicated runner user

Run on the Debian server as root or a sudoer:

```bash
sudo useradd -m -s /bin/bash github-runner
sudo usermod -aG docker github-runner
```

The `docker` group membership lets the runner invoke Docker without `sudo`.

---

## Step 2: Install the GitHub Actions self-hosted runner

1. Go to your GitHub repo → **Settings** → **Actions** → **Runners** → **New self-hosted runner**
2. Select **Linux** / **x64**
3. Follow the shown commands. As the `github-runner` user (the runner tarball includes `./bin/installdependencies.sh` which auto-installs all required Debian packages):

```bash
su - github-runner
mkdir actions-runner && cd actions-runner
# Download the runner tarball shown by GitHub (URL is version-specific)
curl -o actions-runner-linux-x64.tar.gz -L <URL shown by GitHub>
tar xzf actions-runner-linux-x64.tar.gz
./config.sh --url https://github.com/<org>/<repo> --token <TOKEN shown by GitHub> --labels self-hosted,linux,eye-budget --name eye-budget-runner
```

---

## Step 3: Register as a systemd service

```bash
# Still as github-runner user inside ~/actions-runner
sudo ./svc.sh install github-runner
sudo ./svc.sh start
sudo systemctl status actions.runner.*
```

The runner now starts automatically on server boot.

---

## Step 4: Set GitHub Secrets

In the GitHub repo → **Settings** → **Secrets and variables** → **Actions**, add:

| Name | Value |
|------|-------|
| `NEXT_PUBLIC_API_URL` | URL of the backend API (e.g., `http://<SERVER_IP>:8080`) |

---

## Step 5: Verify

Push any commit to the `master` branch. The **Actions** tab on GitHub should show the workflow running on the `self-hosted` runner and deploying successfully.

The app will be accessible at: **http://<SERVER_IP>:3000**

---

## Maintenance

- **Update runner**: GitHub enforces a maximum runner age. Check **Settings → Runners** for update warnings. Run `./svc.sh stop && ./config.sh remove && <re-run Step 2>`.
- **Disk cleanup**: Old Docker images accumulate. Add a weekly cron for the `github-runner` user. This keeps `:latest` and `:previous` but removes untagged intermediate layers:
  ```
  0 3 * * 0 docker image prune -f --filter "until=168h"
  ```
  To add it: `crontab -e` as `github-runner` user and paste the line above.
- **View logs**: `sudo journalctl -u actions.runner.* -f`
