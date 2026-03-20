# Django Job Scheduling Server

This is a centralized asynchronous job scheduling server built with Django, Celery, Redis, RabbitMQ, and Django Channels.  
It provides one API endpoint to create and manage background jobs for Monday.com apps, including immediate, delayed, cron, and polling workloads.

## Architecture Overview

- Web API: Django + Django REST Framework + Daphne
- Background execution: Celery Worker
- Recurring scheduler: Celery Beat
- Message broker: RabbitMQ
- Result backend + channel layer + rate limiting: Redis
- Realtime updates: Django Channels (WebSocket)
- Persistence: SQLite (via shared Docker volume)

## Prerequisites

- Docker Desktop (Linux containers mode)
- Git
- Python 3.13+ only if you want to run the host mock callback server from [mockserver.py](mockserver.py)

## Step 1: Clone and Open Project

```bash
git clone <your-repository-url>
cd django_job_server
```

## Step 2: Create Environment File(just copy paste from .env.example to .env)

Create a file named .env in project root with:

```env
DJANGO_SETTINGS_MODULE=config.settings

SECRET_KEY=change-this-in-real-env
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1,web
INTERNAL_API_SECRET=

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
CELERY_RESULT_BACKEND=redis://redis:6379/0

SQLITE_PATH=/app/data/db.sqlite3

# Docker containers use this URL to call a callback server running on host machine
NODE_SERVER_URL=http://host.docker.internal:3000
```

## Step 3: Start the Docker Stack

From the folder containing [docker-compose.yml](docker-compose.yml):

```bash
docker compose up --build -d
docker compose ps
```

Services started by Compose:

- web (Daphne + Django API)
- worker (Celery worker)
- beat (Celery beat)
- rabbitmq
- redis

## Step 4: Optional Mock Callback Server for Local Testing

If you want job callbacks to succeed during testing, run the mock server on your host machine in a separate terminal:

```bash
python mockserver.py
```

If callbacks fail with connection refused, change bind host in [mockserver.py](mockserver.py#L70) from 127.0.0.1 to 0.0.0.0 and restart the mock server.

## Step 5: Basic Health Check

Test API reachability:

```bash
curl.exe -i http://localhost:8000/api/jobs/create
```

Expected result: 405 Method Not Allowed on GET.  
This is correct because /api/jobs/create accepts POST only.

## Step 6: Create a Test Job

```bash
curl.exe -s -X POST http://localhost:8000/api/jobs/create ^
  -H "Content-Type: application/json" ^
  -d "{\"app_name\":\"app_a\",\"user_id\":\"u1\",\"account_id\":\"a1\",\"task_type\":\"delayed_archive\",\"schedule\":{\"type\":\"immediate\"},\"data\":{}}"
```

Expected response:

```json
{ "id": "<job-uuid>" }
```

Check status:

```bash
curl.exe -s http://localhost:8000/api/jobs/<job-uuid>/status
```

## Step 7: Polling Test Example

```bash
curl.exe -s -X POST http://localhost:8000/api/jobs/create ^
  -H "Content-Type: application/json" ^
  -d "{\"app_name\":\"app_a\",\"user_id\":\"user1\",\"account_id\":\"acc1\",\"task_type\":\"polling_task\",\"schedule\":{\"type\":\"polling\",\"interval_seconds\":5},\"data\":{\"file_path\":\"sample_test_data.csv\"}}"
```

Then call status endpoint repeatedly with returned job id.

## API Endpoints

- POST http://localhost:8000/api/jobs/create
- GET http://localhost:8000/api/jobs/{job_id}/status
- WebSocket job updates: /ws/jobs/{job_id}/

## Supported Scheduling Primitives

- immediate: run now
- run_at: run at exact UTC timestamp
- delay_from_now: run after duration_seconds
- cron: recurring run by cron expression
- polling: recurring run every interval_seconds until callback returns done=true

## Common Troubleshooting

1. Docker engine pipe error on Windows  
   Start Docker Desktop and wait for Engine running.

2. no configuration file provided: not found  
   Run commands from folder containing [docker-compose.yml](docker-compose.yml).

3. Bind for 0.0.0.0:6379 failed: port is already allocated  
   Another Redis is running on host.  
   Update [docker-compose.yml](docker-compose.yml) redis port mapping to 6380:6379 or remove host mapping if not needed.

4. Callback failures in worker logs  
   Check .env NODE_SERVER_URL value and ensure mock server is running on host port 3000.

5. Jobs remain failed  
   Inspect logs:

```bash
docker compose logs -f web
docker compose logs -f worker
docker compose logs -f beat
```

## Useful Commands

Start services:

```bash
docker compose up -d
```

Rebuild images:

```bash
docker compose up --build -d
```

Restart app services after .env changes:

```bash
docker compose up -d --force-recreate web worker beat
```

Stop services:

```bash
docker compose down
```

Stop and remove volumes:

```bash
docker compose down -v
```
