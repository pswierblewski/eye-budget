# Feature Specification: CI/CD Pipeline for Local Network Deployment

**Feature Branch**: `004-cicd-local-deploy`
**Created**: 2026-03-21
**Status**: Draft
**Input**: User description: "I have a debian server in my local network. It's not accessible from the internet, only from local network. It's ip is 192.168.1.184. It has docker installed with portainer. It doesn't have any hosting tools installed for nextjs/react deployments. I want to have a CICD pipeline to deploy a master branch at any change to my debian server."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Deployment on Push (Priority: P1)

A developer pushes a code change to the master branch. Without any manual steps, the application is automatically built and deployed to the local Debian server. Within minutes, the updated application is live and accessible on the local network.

**Why this priority**: This is the core value of the feature. Everything else is secondary to having automatic deployment work reliably.

**Independent Test**: Can be fully tested by pushing a visible change (e.g., a text update) to master and verifying the change appears at the server's address on the local network.

**Acceptance Scenarios**:

1. **Given** a developer has pushed a commit to the master branch, **When** the pipeline triggers, **Then** the application is automatically built, deployed, and accessible on the local network within 5 minutes.
2. **Given** the previous deployment is running, **When** a new deployment completes successfully, **Then** the previous version is replaced without manual intervention.
3. **Given** a push is made to any branch other than master, **When** the pipeline evaluates the trigger, **Then** no deployment to the server occurs.

---

### User Story 2 - Deployment Status Visibility (Priority: P2)

A developer can observe the status and outcome of each deployment — whether it succeeded or failed — without needing to SSH into the server to check manually.

**Why this priority**: Without visibility, failed deployments go unnoticed until someone manually checks the server or notices the app is broken.

**Independent Test**: Can be tested by checking the CI/CD pipeline run history and verifying success/failure is clearly reported after a push.

**Acceptance Scenarios**:

1. **Given** a deployment has just completed, **When** a developer checks the pipeline run history, **Then** the result (success or failure) is clearly visible with a timestamp.
2. **Given** a deployment fails at any stage (build, transfer, or container startup), **When** the developer reviews the pipeline output, **Then** the failure reason is described in enough detail to diagnose the issue.

---

### User Story 3 - Safe Failure Handling (Priority: P3)

When a deployment fails (e.g., the build fails or the new container crashes on startup), the currently running version of the application remains accessible on the local network. The server does not end up in a broken state where no version is running.

**Why this priority**: Protects against accidental downtime caused by a bad push. Important for reliability, but less urgent than getting basic deployment working.

**Independent Test**: Can be tested by deploying a deliberately broken build and verifying the previous working version remains accessible on the local network.

**Acceptance Scenarios**:

1. **Given** the application is running on the server, **When** a deployment fails during the build stage, **Then** the existing running application continues to serve traffic.
2. **Given** the application is running on the server, **When** a new container fails to start after deployment, **Then** the system either keeps the old container running or restarts it.

---

### Edge Cases

- When the Debian server is unreachable (offline or network issue), the pipeline fails immediately with a clear error message. No automatic retries occur; the developer re-triggers the deployment manually once the server is back.
- What happens when disk space on the server is exhausted during image build or transfer?
- When two pushes to master occur in rapid succession, the second deployment is queued and waits for the first to complete before starting. Concurrent deployments to the same server are not permitted.
- What happens when the pipeline runner itself has no network access to the local server (e.g., if a cloud CI environment is used)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The pipeline MUST trigger automatically whenever a commit is pushed to the master branch. Concurrent deployment runs MUST be queued so that at most one deployment runs at a time.
- **FR-002**: The pipeline MUST build the application into a deployable artifact as part of each run.
- **FR-003**: The pipeline MUST transfer the deployable artifact to the Debian server at 192.168.1.184 on the local network.
- **FR-004**: The pipeline MUST start the application on the server after a successful transfer, replacing the previous running version.
- **FR-005**: The pipeline MUST report success or failure for each deployment run in a way visible to the developer without accessing the server directly. If the server is unreachable, the pipeline MUST fail immediately with a descriptive error and MUST NOT retry automatically.
- **FR-006**: The pipeline MUST NOT deploy to the server when triggered by pushes to branches other than master.
- **FR-007**: The server MUST serve the application continuously over the local network on port 3000 (accessible at `http://192.168.1.184:3000`), surviving across deployments.
- **FR-008**: The pipeline runner MUST be a self-hosted GitHub Actions runner installed on the local network, able to reach the Debian server at 192.168.1.184. Cloud-hosted GitHub runners MUST NOT be used for deployment steps, as the server is not internet-accessible.
- **FR-009**: The deployment process MUST use the Docker runtime already present on the Debian server, without requiring additional virtualisation layers.
- **FR-010**: The repository MUST contain all pipeline configuration files needed to reproduce the deployment from scratch.

### Key Entities

- **Pipeline Configuration**: The set of files in the repository that define trigger conditions, build steps, and deployment steps.
- **Deployable Artifact**: The packaged application produced by the build step and deployed to the server.
- **Server Environment**: The Debian host at 192.168.1.184 running Docker and Portainer, which receives and runs the application.
- **Running Application**: The containerised instance of the Next.js application currently serving traffic on the local network.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A push to the master branch results in the updated application being live on the local network within 5 minutes, with no manual steps required.
- **SC-002**: 100% of master branch pushes that produce a successful build result in a live deployment to the server.
- **SC-003**: A developer can determine whether a deployment succeeded or failed, and why it failed if applicable, by checking the pipeline run history alone — without accessing the server.
- **SC-004**: A failed deployment (broken build or crashing container) leaves the server in a state where the previous working version of the application is still accessible.
- **SC-005**: A developer new to the project can understand and reproduce the full deployment setup by reading only the repository files and any documented server setup steps.

## Clarifications

### Session 2026-03-21

- Q: Where is the git repository hosted? → A: GitHub (github.com) — requires a self-hosted Actions runner on the local network to reach the server.
- Q: What port should the application be accessible on? → A: Port 3000.
- Q: How should concurrent deployments (two pushes in rapid succession) be handled? → A: Queue — the second deployment waits for the first to complete before starting.
- Q: What should happen when the server is unreachable during deployment? → A: Fail immediately with a clear error; developer re-triggers manually when server is back.

## Assumptions

- The repository is hosted on GitHub (github.com). A self-hosted GitHub Actions runner is installed on a machine on the local network (e.g., the Debian server itself or another local machine) and can reach 192.168.1.184 directly.
- The Debian server has sufficient resources (CPU, RAM, disk) to build and run the containerised Next.js application.
- The existing Docker and Portainer installation on the server will remain in place; no OS reinstall or Docker removal is expected.
- The application to be deployed is the Next.js frontend in this repository; the backend and database are out of scope for this pipeline unless explicitly included later.
- A single environment (the local server) is the deployment target; staging and production environment separation are out of scope.
- Credentials required for the pipeline to access the server (e.g., SSH keys) will be stored securely as pipeline secrets, not committed to the repository.
