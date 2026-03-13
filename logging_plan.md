# Observability Plan: Loki, Grafana, and Promtail

This document outlines the architecture and implementation plan for adding a secure, low-resource observability stack to the `erez.ac` portfolio site running on an Intel NUC (RHEL 9).

## 1. Architectural Overview

The current architecture consists of Nginx and systemd webhooks running directly on the RHEL host, proxying traffic to a Dockerized Flask/Nuxt application. 

To achieve total visibility without compromising security (e.g., exposing the Docker socket), we will implement a "Socket-less" Grafana Loki stack.

*   **Loki:** The central log aggregation database. Runs as a Docker container. Stores data in a local volume.
*   **Grafana:** The visualization UI. Runs as a Docker container. Connects to Loki. Will be exposed securely via Nginx reverse proxy with built-in authentication.
*   **Docker Loki Driver:** A Docker daemon plugin that pushes container `stdout/stderr` (the Flask/Nuxt app) directly to Loki.
*   **Promtail:** A log scraping agent. Runs as a Docker container with **strict read-only bind mounts** to capture host-level logs (Nginx, SSH, systemd webhooks) and pushes them to Loki.

## 2. Resource Constraints

The host is a low-power Intel NUC. 
*   Loki must be configured in `monolithic` (single binary) mode.
*   Log retention should be strictly limited (e.g., 14 or 30 days) to prevent disk exhaustion.
*   Total expected RAM overhead: ~150-200MB.

## 3. Implementation Steps

The next agent should follow these steps to implement the stack.

### Step 3.1: Host Preparation (Manual Step for User)
The user must SSH into the RHEL 9 NUC and install the Docker Loki driver.
**Note:** Do not use `--grant-all-permissions`. Let the user verify the network privileges interactively.
```bash
docker plugin install grafana/loki-docker-driver:latest --alias loki
```

### Step 3.2: Create Configuration Directories
Create a new directory in the project root: `server/observability/`. 
This will hold the configuration files for the new containers.

### Step 3.3: Configure Loki (`server/observability/loki-config.yaml`)
Create a minimal configuration file for Loki.
*   Must use `auth_enabled: false` (since it's only accessed locally by Promtail/Grafana/Docker driver).
*   Must configure the `common` block to use `filesystem` storage (no cloud buckets).
*   Must configure `limits_config` to enforce retention (e.g., `retention_period: 14d`).

### Step 3.4: Configure Promtail (`server/observability/promtail-config.yaml`)
Create a configuration file for Promtail to scrape host logs.
*   **Client:** Point to `http://loki:3100/loki/api/v1/push`.
*   **Scrape Config 1 (Nginx):** Read from `/var/log/nginx/*log`. Assign labels `{job="nginx", host="nuc"}`.
*   **Scrape Config 2 (Journald):** Use the `journal` scrape configuration to capture host systemd logs (SSH, `webhook.service`, etc.). Assign labels `{job="systemd", host="nuc"}`.

### Step 3.5: Configure Grafana Auto-Provisioning
Create `server/observability/grafana-datasources.yaml` to automatically link Grafana to Loki on startup, preventing manual UI setup.
```yaml
apiVersion: 1
datasources:
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    isDefault: true
```

### Step 3.6: Update `docker-compose.yml`
Add the three new services to the existing `docker-compose.yml` (or create a secondary `docker-compose.observability.yml` if the user prefers separation).

1.  **Loki Service:**
    *   Image: `grafana/loki:latest`
    *   Ports: `3100:3100` (Needed for the Docker driver on the host network bridge).
    *   Volumes: Mount `loki-config.yaml` and a persistent named volume for `/loki`.
2.  **Promtail Service:**
    *   Image: `grafana/promtail:latest`
    *   Volumes (Strictly Read-Only):
        *   `promtail-config.yaml`
        *   `/var/log/nginx:/var/log/nginx:ro`
        *   `/var/log/journal:/var/log/journal:ro`
        *   `/etc/machine-id:/etc/machine-id:ro` (Required for journald reading).
3.  **Grafana Service:**
    *   Image: `grafana/grafana:latest`
    *   Ports: `3000:3000` (To be proxied by Nginx).
    *   Volumes: Mount `grafana-datasources.yaml` and a persistent named volume for `/var/lib/grafana`.
    *   Environment: Disable anonymous access, disable signups.

### Step 3.7: Update App Service Logging
Modify the main Flask application service in `docker-compose.yml` to utilize the newly installed Docker plugin:
```yaml
    logging:
      driver: loki
      options:
        loki-url: "http://localhost:3100/loki/api/v1/push"
        loki-retention: "14d"
        # Extract docker labels as Loki labels
        loki-external-labels: "compose_service"
```

### Step 3.8: Nginx Reverse Proxy (Host Configuration)
Provide the user with the Nginx configuration block to expose Grafana securely.
*   Create a location block (e.g., `location /logs/` or a subdomain).
*   Proxy pass to `http://127.0.0.1:3000`.
*   Ensure WebSockets are supported (required for Grafana live tailing).

### Step 3.9: Application-Level Security Auditing (Optional Extension)
Instruct the user/agent on how to utilize Python's built-in `logging` module in Flask (`app/auth.py`, `app/api/kenno.py`) to log specific business logic events (e.g., Failed Logins, Word Blocks) to stdout, which will now automatically flow into Loki and become searchable in Grafana.