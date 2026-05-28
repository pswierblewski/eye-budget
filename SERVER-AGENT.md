# Server Agent Setup Instructions

> **For the Claude Code agent running on the Debian server (<SERVER_IP>).**
> Execute all tasks below in order. After completion, this agent session should be closed.
> Future access to this server will only be via the restricted `deploy` SSH user.

---

## Task 1 — Create the `deploy` user

```bash
sudo useradd -m -s /bin/bash deploy
sudo passwd -l deploy
```

Verify: `sudo passwd -S deploy` should show `deploy L` (locked).

---

## Task 2 — Set up SSH key for the `deploy` user

```bash
sudo mkdir -p /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chown deploy:deploy /home/deploy/.ssh
```

Now add the public key of the machine where the LLM agent will run (e.g. your laptop):

```bash
echo "<YOUR_SSH_PUBLIC_KEY>" | sudo tee /home/deploy/.ssh/authorized_keys
sudo chmod 600 /home/deploy/.ssh/authorized_keys
sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys
```

> **Replace `PASTE_PUBLIC_KEY_HERE` with the actual `~/.ssh/id_ed25519.pub` (or equivalent) from the machine where Claude Code will connect from.**

Verify: `sudo cat /home/deploy/.ssh/authorized_keys` — should contain one key line.

---

## Task 3 — Configure sudoers (gateway script only)

One entry — `deploy` may run only the gateway script as root.
`env_keep` ensures `SSH_ORIGINAL_COMMAND` is passed through `sudo` to the script:

```bash
sudo tee /etc/sudoers.d/10-deploy-docker << 'EOF'
Defaults:deploy !requiretty
Defaults:deploy env_keep += "SSH_ORIGINAL_COMMAND"
deploy ALL=(root) NOPASSWD: /usr/local/bin/deploy-gateway.sh
EOF
sudo chmod 440 /etc/sudoers.d/10-deploy-docker
```

Verify: `sudo visudo -cf /etc/sudoers.d/10-deploy-docker` — should print `OK`.

---

## Task 4 — Create the deployment gateway script

```bash
sudo tee /usr/local/bin/deploy-gateway.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail

case "${SSH_ORIGINAL_COMMAND:-}" in

  "deploy")
    docker tag eye-budget-frontend:latest eye-budget-frontend:previous 2>/dev/null || true
    docker stop eye-budget-frontend 2>/dev/null || true
    docker rm   eye-budget-frontend 2>/dev/null || true
    docker run -d --name eye-budget-frontend \
      -p 3000:3000 --restart unless-stopped eye-budget-frontend:latest
    echo "OK: deployed eye-budget-frontend:latest"
    ;;

  "rollback")
    docker image inspect eye-budget-frontend:previous > /dev/null 2>&1 \
      || { echo "ERROR: no previous image available"; exit 1; }
    docker stop eye-budget-frontend 2>/dev/null || true
    docker rm   eye-budget-frontend 2>/dev/null || true
    docker run -d --name eye-budget-frontend \
      -p 3000:3000 --restart unless-stopped eye-budget-frontend:previous
    echo "OK: rolled back to eye-budget-frontend:previous"
    ;;

  "status")
    docker ps \
      --filter name=eye-budget-frontend \
      --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    ;;

  logs | "logs "[0-9]*)
    LINES=$(echo "${SSH_ORIGINAL_COMMAND}" | awk '{print $2}')
    LINES=${LINES:-50}
    [[ "$LINES" =~ ^[0-9]+$ ]] || { echo "ERROR: invalid line count"; exit 1; }
    docker logs --tail "$LINES" eye-budget-frontend
    ;;

  "health")
    curl -sf http://localhost:3000/api/health \
      && echo "" || { echo "UNHEALTHY"; exit 1; }
    ;;

  *)
    echo "ERROR: unknown command."
    echo "Allowed: deploy | rollback | status | logs [N] | health"
    exit 1
    ;;

esac
SCRIPT

sudo chmod 755 /usr/local/bin/deploy-gateway.sh
sudo chown root:root /usr/local/bin/deploy-gateway.sh
```

Verify: `sudo cat /usr/local/bin/deploy-gateway.sh` — should show the script content.

---

## Task 5 — Restrict SSH for the `deploy` user

```bash
sudo tee /etc/ssh/sshd_config.d/99-deploy-restrict.conf << 'EOF'
Match User deploy
    PasswordAuthentication    no
    PermitEmptyPasswords      no
    X11Forwarding             no
    AllowTcpForwarding        no
    AllowAgentForwarding      no
    PermitTunnel              no
    ForceCommand              sudo /usr/local/bin/deploy-gateway.sh
EOF
```

Test the config and reload sshd:

```bash
sudo sshd -t && sudo systemctl reload sshd
```

Verify: `sudo sshd -t` must return exit code 0 with no errors before reloading.

---

## Task 6 — Verify the setup

Run each check and confirm it passes:

```bash
# 1. deploy user exists and is locked
sudo passwd -S deploy

# 2. sudoers file is valid
sudo visudo -cf /etc/sudoers.d/10-deploy-docker

# 3. gateway script is executable and owned by root
ls -la /usr/local/bin/deploy-gateway.sh

# 4. SSH config is valid
sudo sshd -t

# 5. authorized_keys is in place
sudo cat /home/deploy/.ssh/authorized_keys
```

All commands should succeed without errors.

---

## Done

After all tasks complete successfully, this agent session should be closed.

From your laptop you will connect as:
```bash
ssh -i ~/.ssh/deploy_eye_budget deploy@<SERVER_IP> status
ssh -i ~/.ssh/deploy_eye_budget deploy@<SERVER_IP> health
ssh -i ~/.ssh/deploy_eye_budget deploy@<SERVER_IP> "logs 50"
ssh -i ~/.ssh/deploy_eye_budget deploy@<SERVER_IP> deploy
ssh -i ~/.ssh/deploy_eye_budget deploy@<SERVER_IP> rollback
```

To avoid typing `-i` every time, add this to `~/.ssh/config` on your laptop:

```
Host eye-budget-deploy
    HostName <SERVER_IP>
    User deploy
    IdentityFile ~/.ssh/deploy_eye_budget
    IdentitiesOnly yes
```

Then you can use:
```bash
ssh eye-budget-deploy status
ssh eye-budget-deploy health
ssh eye-budget-deploy "logs 50"
ssh eye-budget-deploy deploy
ssh eye-budget-deploy rollback
```

Any other command or interactive shell attempt will be rejected with an error.
