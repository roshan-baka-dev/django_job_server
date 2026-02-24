# Django Job Scheduling Server

This is a centralized asynchronous job scheduling server built with Django, Celery, Redis, and RabbitMQ. It provides a single API endpoint to create and manage background tasks for Monday.com applications, supporting immediate execution, scheduled execution (cron/delayed), and stateful recursive polling.

## 🏗 Architecture Overview

- **Web Server:** Django (REST Framework)
- **Task Queue:** Celery
- **Message Broker:** RabbitMQ
- **Results Backend:** Redis
- **State Management:** PostgreSQL / SQLite

## ⚙️ Prerequisites

Before you begin, ensure you have the following installed on your machine:

- Python 3.9+
- [Pipenv](https://pipenv.pypa.io/en/latest/) (for virtual environment management)
- [RabbitMQ](https://www.rabbitmq.com/download.html) (running locally on port 5672)
- [Redis](https://redis.io/download) (running locally on port 6379)

---

## 🚀 Step 1: Environment Setup

1. **Clone the repository and navigate to the project folder:**

```bash
 cd django_job_server
```

1. **Install the dependencies using Pipenv:**

```bash
 pipenv install
```

1. **Activate the virtual environment:**

```bash
 pipenv shell
```

1. **Apply database migrations:**

```bash
 python manage.py migrate
```

## 🏃‍♂️ Step 2: Running the Application

Because this is a distributed background task system, you will need to open multiple terminal windows (ensure your virtual environment is activated in each one via pipenv shell).

1.**Terminal 1: The Django API Server**

```bash
   python manage.py runserver
```

2.**Terminal 2: The Celery Worker**

```bash
   celery -A config worker -l INFO -P threads
```

3.**Terminal 3: The Celery Beat Scheduler**

```bash
   celery -A config beat -l INFO
```

4.**Terminal 4: The Mock Node Server (For Local Testing Only)**

```bash
python mockserver.py
```

5.**Terminal 5.Redis Use WSL (Windows Subsystem for Linux)**

```bash
sudo apt update
sudo apt install redis-server
```

```bash
redis-server
```

## 🧪 Step 3: API Usage

Once all services are running, you can create a job by sending a POST request to the main API endpoint.

**Endpoint:** POST [http://127.0.0.1:8000/api/jobs/create](http://127.0.0.1:8000/api/jobs/create)

**Headers:** Content-Type: application/json

Example Payload (Stateful Polling):

```json
{
  "app_name": "app_a",
  "user_id": "user1",
  "account_id": "acc1",
  "task_type": "polling_task",
  "schedule": {
    "type": "polling",
    "interval_seconds": 30
  },
  "data": {
    "some_key": "some_value"
  }
}
```

### checking job status

You can track the progress of your background task by taking the UUID returned from the creation endpoint and calling the status endpoint:

Endpoint: GET [http://127.0.0.1:8000/api/jobs/[job_uuid]/status](http://127.0.0.1:8000/api/jobs/[job_uuid]/status)

**job_uuid** is the id of the job

# 📂 Supported Scheduling Primitives

The server supports the following `schedule.type` configurations in the creation payload:

- **`immediate`**: Runs the task as soon as the request is received.
- **`run_at`**: Runs the task at a specific exact UTC timestamp.
- **`delay_from_now`**: Runs the task relative to the current time, after a specified `duration_seconds`.
- **`cron`**: Runs the task recursively based on a standard cron expression (e.g., `* * * * *`).
- **`polling`**: Runs the task recursively every `interval_seconds`, carrying its progress state forward until explicitly marked as `"done": true` by the callback server.
