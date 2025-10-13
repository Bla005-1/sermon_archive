# Sermon Archive Deployment Guide

This document outlines how the **Sermon Archive** Django project is deployed across two hosts:

- **App Server (bryce-srv-1)** — Runs Django under Gunicorn via systemd, behind a WireGuard VPN.
- **Droplet (Proxy)** — Public-facing server running Nginx for HTTPS termination, static file serving, and reverse-proxying requests to the app server.

---

## 1. App Server Setup

### 1.1 Project location and environment

- Poetry creates an in-project virtual environment at `.venv/`.
- Gunicorn runs inside this virtualenv.

### 1.2 Systemd service unit

`sermon-archive.service`

## 6. Static File Deployment
### 6.1 On the app server

Collect static files:

cd ~/personal_services/sermon_archive
poetry run python manage.py collectstatic --noinput

This writes to:

sermon_archive/staticfiles/

6.2 Push to the droplet

Assuming the droplet WireGuard IP is 10.100.0.1 and static directory is /var/www/sermon_static:

rsync -avz --delete sermon_archive/staticfiles droplet:/var/www/sermon_static/
