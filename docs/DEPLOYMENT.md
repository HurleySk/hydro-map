# Deployment Guide

**Version**: 1.7.0

## Overview

This guide covers deploying Hydro-Map to production environments. Multiple deployment strategies are supported, from Docker-based deployments to traditional server setups.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Deployment Options](#deployment-options)
- [Docker Deployment](#docker-deployment)
- [Traditional Server Deployment](#traditional-server-deployment)
- [Reverse Proxy Configuration](#reverse-proxy-configuration)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Process Management](#process-management)
- [Monitoring and Logging](#monitoring-and-logging)
- [Backup and Maintenance](#backup-and-maintenance)
- [Scaling Considerations](#scaling-considerations)

---

## Prerequisites

### System Requirements

**Minimum** (small regions, low traffic):
- CPU: 2 cores
- RAM: 4 GB
- Storage: 20 GB (10 GB for application + data, 10 GB for operating system)
- Network: 100 Mbps

**Recommended** (large DEMs, moderate traffic):
- CPU: 4-8 cores
- RAM: 8-16 GB
- Storage: 50-100 GB SSD
- Network: 1 Gbps

**Large deployment** (extensive coverage, high traffic):
- CPU: 8+ cores
- RAM: 16-32 GB
- Storage: 500 GB+ SSD (for multiple DEMs and tile caches)
- Network: 1+ Gbps
- Consider load balancing multiple backend instances

### Software Prerequisites

- **Operating System**: Linux (Ubuntu 22.04 LTS recommended) or Docker host
- **Python**: 3.11+ (backend)
- **Node.js**: 20+ (frontend build)
- **GDAL**: 3.4+ with Python bindings
- **Docker**: 24+ (if using Docker deployment)
- **Reverse Proxy**: nginx 1.18+ or Caddy 2.6+

---

## Deployment Options

### Option 1: Docker Compose (Recommended)

**Pros**:
- Containerized, reproducible environment
- Easy updates (pull new images)
- Isolated dependencies
- Simple multi-service orchestration

**Cons**:
- Requires Docker knowledge
- Slight overhead compared to native

**Best for**: Most production deployments

### Option 2: Traditional Server Deployment

**Pros**:
- Direct control over processes
- No container overhead
- Easier debugging

**Cons**:
- Manual dependency management
- More complex update process
- Environment-specific issues

**Best for**: Organizations without Docker infrastructure

### Option 3: Cloud Platforms

**Supported platforms**:
- AWS (EC2, ECS, or Elastic Beanstalk)
- Google Cloud Platform (Compute Engine, Cloud Run)
- Azure (App Service, Container Instances)
- DigitalOcean (Droplets, App Platform)

---

## Docker Deployment

### Build and Run with Docker Compose

#### 1. Prepare Environment

```bash
# Clone repository
git clone https://github.com/HurleySk/hydro-map.git
cd hydro-map

# Create .env file
cp .env.example .env

# Edit .env for production
nano .env
```

**Production .env**:
```bash
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_RELOAD=false
CORS_ORIGINS=https://yourdomain.com
CACHE_ENABLED=true
```

#### 2. Prepare Data

```bash
# Generate all required data (see DATA_PREPARATION.md)
# This must be done before building containers

# Verify data files exist
ls data/processed/dem/
ls data/tiles/
```

#### 3. Build and Start

```bash
# Build containers
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

#### 4. Verify Deployment

```bash
# Test backend API
curl http://localhost:8000/api/delineate/status

# Test frontend
curl http://localhost:5173/
```

### Production Docker Compose Configuration

**File**: `docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: hydro-map-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data:ro          # Read-only data
      - ./backend/data/cache:/app/data/cache:rw  # Writable cache
    environment:
      - BACKEND_HOST=0.0.0.0
      - BACKEND_PORT=8000
      - BACKEND_RELOAD=false
    env_file:
      - .env
    command: gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/delineate/status"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
      args:
        - VITE_API_URL=https://api.yourdomain.com
    container_name: hydro-map-frontend
    restart: unless-stopped
    ports:
      - "3000:3000"

  redis:
    image: redis:7-alpine
    container_name: hydro-map-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru

  nginx:
    image: nginx:alpine
    container_name: hydro-map-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
      - frontend

volumes:
  redis-data:
```

### Frontend Production Dockerfile

**File**: `frontend/Dockerfile.prod`

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Build application
COPY . .
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Production image
FROM node:20-alpine

WORKDIR /app

# Copy built files and package.json
COPY --from=builder /app/build ./build
COPY --from=builder /app/package*.json ./

# Install production dependencies only
RUN npm ci --production

EXPOSE 3000

CMD ["node", "build"]
```

### Docker Management Commands

```bash
# Start services
docker-compose -f docker-compose.prod.yml up -d

# Stop services
docker-compose -f docker-compose.prod.yml down

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Restart specific service
docker-compose -f docker-compose.prod.yml restart backend

# Update and restart
git pull
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Clean up old images
docker image prune -a
```

---

## Traditional Server Deployment

### Backend Deployment (Python/FastAPI)

#### 1. Install System Dependencies

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip \
  gdal-bin libgdal-dev build-essential git
```

**RHEL/CentOS**:
```bash
sudo yum install -y python311 python311-devel \
  gdal gdal-devel gcc git
```

#### 2. Create Application User

```bash
sudo useradd -m -s /bin/bash hydromap
sudo su - hydromap
```

#### 3. Clone and Setup

```bash
cd /opt
sudo git clone https://github.com/HurleySk/hydro-map.git
sudo chown -R hydromap:hydromap hydro-map
cd hydro-map

# Create virtual environment
python3.11 -m venv backend/venv
source backend/venv/bin/activate

# Install dependencies
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Configure Environment

```bash
cp ../.env.example ../.env
nano ../.env
```

#### 5. Test Backend

```bash
# Activate venv
source venv/bin/activate

# Run backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 6. Install Gunicorn (Production WSGI Server)

```bash
pip install gunicorn
```

#### 7. Create systemd Service

**File**: `/etc/systemd/system/hydro-map-backend.service`

```ini
[Unit]
Description=Hydro-Map Backend API
After=network.target

[Service]
Type=notify
User=hydromap
Group=hydromap
WorkingDirectory=/opt/hydro-map/backend
Environment="PATH=/opt/hydro-map/backend/venv/bin"
ExecStart=/opt/hydro-map/backend/venv/bin/gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile /var/log/hydro-map/access.log \
  --error-logfile /var/log/hydro-map/error.log \
  --log-level info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Create log directory
sudo mkdir /var/log/hydro-map
sudo chown hydromap:hydromap /var/log/hydro-map

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable hydro-map-backend
sudo systemctl start hydro-map-backend
sudo systemctl status hydro-map-backend
```

### Frontend Deployment (SvelteKit)

#### 1. Build Frontend

```bash
cd /opt/hydro-map/frontend

# Install dependencies
npm install

# Build for production
npm run build
```

#### 2. Option A: Node.js Server (SvelteKit)

**systemd service**: `/etc/systemd/system/hydro-map-frontend.service`

```ini
[Unit]
Description=Hydro-Map Frontend
After=network.target

[Service]
Type=simple
User=hydromap
Group=hydromap
WorkingDirectory=/opt/hydro-map/frontend
Environment="PORT=3000"
ExecStart=/usr/bin/node build
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable hydro-map-frontend
sudo systemctl start hydro-map-frontend
```

#### 2. Option B: Static File Hosting (nginx/Caddy)

If using static adapter:

```bash
# Install static adapter
npm install -D @sveltejs/adapter-static

# Update svelte.config.js to use adapter-static
# Rebuild
npm run build

# Serve build/ directory with nginx or Caddy
```

---

## Reverse Proxy Configuration

### nginx Configuration

**File**: `/etc/nginx/sites-available/hydro-map`

```nginx
# Backend API
upstream backend {
    server localhost:8000;
}

# Frontend (if using Node.js server)
upstream frontend {
    server localhost:3000;
}

# HTTP → HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logs
    access_log /var/log/nginx/hydro-map-access.log;
    error_log /var/log/nginx/hydro-map-error.log;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # PMTiles (with range request support)
    location /tiles/ {
        proxy_pass http://backend/tiles/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Range $http_range;
        proxy_set_header If-Range $http_if_range;
        proxy_pass_request_headers on;
        proxy_http_version 1.1;

        # Caching
        proxy_cache_bypass $http_pragma $http_authorization;
        add_header X-Cache-Status $upstream_cache_status;
    }

    # Increase body size for large requests
    client_max_body_size 10M;
}
```

**Enable site**:
```bash
sudo ln -s /etc/nginx/sites-available/hydro-map /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Caddy Configuration (Alternative)

**File**: `/etc/caddy/Caddyfile`

```caddy
yourdomain.com {
    # Automatic HTTPS via Let's Encrypt

    # Frontend
    reverse_proxy / localhost:3000

    # Backend API
    reverse_proxy /api/* localhost:8000

    # PMTiles with range request support
    reverse_proxy /tiles/* localhost:8000 {
        header_up Range {http.request.header.Range}
    }

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
    }

    # Logging
    log {
        output file /var/log/caddy/hydro-map-access.log
    }
}
```

**Start Caddy**:
```bash
sudo systemctl enable caddy
sudo systemctl start caddy
```

---

## SSL/TLS Configuration

### Let's Encrypt (Free SSL Certificates)

#### Option 1: Certbot (nginx)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal (certbot installs cron job automatically)
sudo certbot renew --dry-run
```

#### Option 2: Caddy (Automatic HTTPS)

Caddy handles SSL automatically - just use domain name in Caddyfile.

### Manual Certificate Installation

If using purchased SSL certificate:

```bash
# Copy certificates
sudo cp yourdomain.com.crt /etc/nginx/ssl/
sudo cp yourdomain.com.key /etc/nginx/ssl/
sudo chmod 600 /etc/nginx/ssl/yourdomain.com.key

# Update nginx config to use certificates
ssl_certificate /etc/nginx/ssl/yourdomain.com.crt;
ssl_certificate_key /etc/nginx/ssl/yourdomain.com.key;
```

---

## Process Management

### systemd Service Management

```bash
# Start services
sudo systemctl start hydro-map-backend
sudo systemctl start hydro-map-frontend

# Stop services
sudo systemctl stop hydro-map-backend
sudo systemctl stop hydro-map-frontend

# Restart services
sudo systemctl restart hydro-map-backend

# Check status
sudo systemctl status hydro-map-backend

# Enable auto-start on boot
sudo systemctl enable hydro-map-backend
sudo systemctl enable hydro-map-frontend

# View logs
sudo journalctl -u hydro-map-backend -f
```

### Supervisor (Alternative Process Manager)

**Install**:
```bash
sudo apt install supervisor
```

**Config**: `/etc/supervisor/conf.d/hydro-map-backend.conf`

```ini
[program:hydro-map-backend]
command=/opt/hydro-map/backend/venv/bin/gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
directory=/opt/hydro-map/backend
user=hydromap
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/hydro-map/backend.log
```

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl status
```

---

## Monitoring and Logging

### Log Locations

**Backend** (systemd):
- Journal: `sudo journalctl -u hydro-map-backend`
- Gunicorn logs: `/var/log/hydro-map/access.log`, `/var/log/hydro-map/error.log`

**Frontend** (systemd):
- Journal: `sudo journalctl -u hydro-map-frontend`

**nginx**:
- Access: `/var/log/nginx/hydro-map-access.log`
- Error: `/var/log/nginx/hydro-map-error.log`

### Log Rotation

**File**: `/etc/logrotate.d/hydro-map`

```
/var/log/hydro-map/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 hydromap hydromap
    sharedscripts
    postrotate
        systemctl reload hydro-map-backend > /dev/null 2>&1 || true
    endscript
}
```

### Health Checks

**Backend health endpoint**:
```bash
curl http://localhost:8000/api/delineate/status
```

**Expected response**:
```json
{
  "status": "operational",
  "cache_size": 42,
  "available_data": {
    "dem": true,
    "flow_accumulation": true,
    "flow_direction": true
  }
}
```

### Monitoring Tools

**Prometheus + Grafana** (recommended for production):
- Add FastAPI prometheus middleware
- Monitor request rates, latency, errors
- Alert on high error rates or slow responses

**Uptime monitoring**:
- UptimeRobot (free tier available)
- Pingdom
- StatusCake

---

## Backup and Maintenance

### What to Backup

**Critical**:
- Application code: `/opt/hydro-map/` (or use Git)
- Configuration: `.env` file
- Cache: `backend/data/cache/` (optional, can be regenerated)

**Non-critical** (can be regenerated):
- Data files: `data/processed/`, `data/tiles/`
- Logs

### Backup Strategy

**Option 1: rsync to backup server**:
```bash
rsync -avz --delete /opt/hydro-map/ backup-server:/backups/hydro-map/
```

**Option 2: Database backups** (if using Postgres for custom features):
```bash
pg_dump hydro_map > hydro_map_backup.sql
```

**Option 3: Cloud backups**:
```bash
# AWS S3
aws s3 sync /opt/hydro-map/backend/data/cache/ s3://hydro-map-backups/cache/
```

### Update Procedure

```bash
# 1. Pull latest code
cd /opt/hydro-map
git pull

# 2. Update backend dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt

# 3. Update frontend
cd ../frontend
npm install
npm run build

# 4. Restart services
sudo systemctl restart hydro-map-backend
sudo systemctl restart hydro-map-frontend

# 5. Verify
curl http://localhost:8000/api/delineate/status
```

---

## Scaling Considerations

### Horizontal Scaling (Multiple Backend Instances)

**Load balancer** (nginx):
```nginx
upstream backend {
    least_conn;
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}
```

**Shared cache** (Redis):
- Replace disk cache with Redis
- All backend instances share cache

**Session affinity**: Not required (API is stateless)

### Vertical Scaling

**Increase workers**:
```bash
# Calculate: (2 × CPU cores) + 1
gunicorn app.main:app --workers 8 --worker-class uvicorn.workers.UvicornWorker
```

**Memory**: 2-4 GB per worker (depends on DEM size)

### CDN for Static Assets

**PMTiles via CDN**:
- Upload tiles to S3/R2/DigitalOcean Spaces
- Serve via CloudFront/Cloudflare CDN
- Reduces server bandwidth

---

## Related Documentation

- [Configuration Guide](CONFIGURATION.md) - Environment and settings
- [Architecture](ARCHITECTURE.md) - System design
- [Troubleshooting](TROUBLESHOOTING.md) - Common deployment issues

---

## Deployment Checklist

### Pre-Deployment

- [ ] All data files generated and tested locally
- [ ] `.env` configured for production
- [ ] SSL certificates obtained
- [ ] Domain DNS configured
- [ ] Firewall rules configured (ports 80, 443)
- [ ] Backup strategy in place

### Deployment

- [ ] Application deployed (Docker or traditional)
- [ ] Services started and enabled
- [ ] Reverse proxy configured
- [ ] HTTPS working
- [ ] Health checks passing
- [ ] Logs being written

### Post-Deployment

- [ ] Monitoring configured
- [ ] Log rotation enabled
- [ ] Backups tested
- [ ] Performance tested
- [ ] Documentation updated with production URLs
- [ ] Team trained on maintenance procedures
