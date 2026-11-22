<img width="1616" height="605" alt="GalaReserve: event booking REST API" src="https://github.com/user-attachments/assets/b5c9d117-5a1a-4de1-8a07-40d8904a0f34" />

# GalaReserve

[![Python 3.14](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/release/python-3140/)
[![Coverage 97%](https://img.shields.io/badge/coverage-97%25-brightgreen)](gala_reserve/tests)

> Backend REST API for an event booking platform, built with Django REST Framework, PostgreSQL, Celery, RabbitMQ, Redis and Docker. The focus is race-condition-safe seat booking, integrity enforced at the database and application level, JWT security, and a clean services/selectors architecture.

GalaReserve lets users with a verified email create events with a limited number of seats. Other users register for an event and receive an e-ticket by email, and organizers check tickets in at the door.

**Live demo:** [Swagger UI](https://gala-reserve.ru/schema/swagger-ui/)

[Highlights](#highlights) · [Features](#features) · [Quick start](#quick-start) · [Testing](#testing) · [Design decisions](#key-design-decisions)

## Highlights

- **Race-condition-safe booking.** `book_free_event` runs in a single transaction and locks the event row with `select_for_update()` before checking capacity, so concurrent requests for the same event are serialized. The registration, the seat counter and the ticket are committed atomically. See [`events/services/booking.py`](gala_reserve/apps/events/services/booking.py).
- **Integrity enforced by PostgreSQL, not only by Python.** CHECK constraints (for example `capacity >= seats_taken`, `end_at > start_at`), a partial unique index that forbids duplicate active registrations, case-insensitive unique indexes and composite indexes. See [`events/models.py`](gala_reserve/apps/events/models.py) and [`booking/models.py`](gala_reserve/apps/booking/models.py).
- **Services + selectors architecture.** Views stay thin. Business rules and transactions live in `services/`, and read-side querysets and visibility rules live in `selectors`. Business errors are domain exceptions mapped to one error format.
- **Reliable background work.** Celery with RabbitMQ. Emails are dispatched through `transaction.on_commit` (no email for a rolled-back booking), retried with exponential backoff and jitter, and routed to a dedicated `emails` queue. Celery Beat completes finished events every 5 minutes.
- **Security by design.** Rotating JWT refresh tokens with a blacklist, revocation of all refresh tokens on password change, HMAC-hashed one-time codes with attempt limits, per-endpoint throttling backed by Redis, endpoint- and object-level permissions.
- **Consistent API contract.** One error envelope with stable machine-readable codes, URL versioning (`/v1/`), and an OpenAPI 3 schema with Swagger UI and ReDoc generated from the code.
- **Tested and reproducible.** Nearly 300 pytest test functions, `97%` test coverage, a multi-stage Dockerfile that produces a ~260 MB image, dependencies locked with `uv`, and Docker Compose setups for development and production.

## Features

**Accounts and security**
- Registration, login, token refresh and logout (JWT, access 30 min / refresh 7 days, rotation with blacklist).
- Email verification with a 6-digit one-time code (15-minute TTL, 5 attempts, resend cooldown).
- Password reset by emailed code and password change by old password; both revoke all active refresh tokens.
- Profile management and photo upload (validated and re-encoded to WebP, EXIF metadata stripped with Pillow).

**Events**
- Full event lifecycle management - creation of draft event, then publishing with validated status transitions and event cancellation. \
  Celery Beat transitions the event to the completed status.
- Categories with case-insensitive unique names. A category that has events cannot be deleted.
- Public event list with
    - search (title, description, address),
    - filters (category, organizer, status, price range, start-date range),
    - sorting (start time, price, creation time, popularity)
    - pagination (20 per page by default, max 100).
- Drafts are visible only to their organizer and to staff.

**Registration and tickets (free events)**
- Instant confirmation and a UUID ticket, delivered by email.
- Registration closes when the event starts. A confirmed registration can be cancelled until 24 hours before the start; cancelling frees the seat, invalidates the ticket and sends a notification.
- Organizer or admin check-in, opening 60 minutes before the start.
- "My events", "my registrations" and "my tickets" endpoints with filters.
- Cancelling an event cascades: registrations are cancelled with reason `event_cancelled` and valid tickets are invalidated.

**Background jobs**
- Ticket, verification code, password reset and registration cancellation emails (Celery, `emails` queue).
- Periodic completion of finished events (Celery Beat, every 5 minutes, one bulk `UPDATE`).

**Database-level guarantees**
- `event_capacity_gte_seats_taken`: the seat counter can never exceed capacity, even if application code has a bug.
- `reg_active_user_event_uidx`: a partial unique index on `(user, event)` for `pending`/`confirmed` registrations. A user cannot hold two active registrations, but can register again after cancelling.
- Various CHECK constraints for Event model like price range, the capacity range, `end_at > start_at`, allowed statuses, and `published_at` matching the status.
- Case-insensitive unique indexes (`Lower(...)`) on user email, username and category name.
- Composite indexes for the main query paths, for example `(event, status)` and `(user, status, -created_at)`.
- `on_delete=PROTECT` on events, registrations and tickets, so history is not deleted by accident.

Each app follows the same layout: `models.py`, `services/`, `selectors.py`, `views/`, `serializers/`, `tasks/`, `filters.py`, `factories.py`.

## Tech stack

* [Python 3.14](https://www.python.org/downloads/release/python-3140/)
* [Django 5.2](https://docs.djangoproject.com/en/5.2/)
* [Django REST Framework](https://www.django-rest-framework.org/)
* [PostgreSQL 18](https://www.postgresql.org/docs/18/)
* [Celery 5.6](https://docs.celeryq.dev/en/stable/)
* [Redis 7](https://redis.io/)
* [RabbitMQ 4.2](https://www.rabbitmq.com/)
* [Docker](https://www.docker.com/) ([Docker Compose](https://docs.docker.com/compose/))
* [Nginx](https://nginx.org/)
* [Gunicorn](https://gunicorn.org/)
* [djangorestframework-simplejwt](https://django-rest-framework-simplejwt.readthedocs.io/en/latest/)
* [drf-spectacular](https://drf-spectacular.readthedocs.io/en/latest/)
* [django-filter](https://django-filter.readthedocs.io/en/stable/)
* [django-cleanup](https://github.com/un1t/django-cleanup)
* [django-environ](https://django-environ.readthedocs.io/en/latest/)
* [Pillow](https://pillow.readthedocs.io/en/stable/)
* [pytest](https://pytest.org/) ([pytest-django](https://pytest-django.readthedocs.io/en/latest/), [pytest-mock](https://pytest-mock.readthedocs.io/en/latest/), [pytest-cov](https://pytest-cov.readthedocs.io/en/latest/), [pytest-xdist](https://pytest-xdist.readthedocs.io/en/latest/))
* [uv](https://docs.astral.sh/uv/)
* [factory-boy](https://factoryboy.readthedocs.io/en/stable/)
* [freezegun](https://github.com/spulec/freezegun)

## Quick start

Requirements: Docker with Docker Compose v2.

```
git clone https://github.com/quintessenc3/gala-reserve.git
cd gala-reserve

cp .env.example .env
docker compose up --build -d
```

Then wait until all the services are fully started, and (for the first run only) run the migrations:

```
docker compose exec api python manage.py migrate
```

In development, emails use Django's console backend, so verification codes and tickets are printed in the worker log:

```
docker compose logs -f worker
```

### Production deployment

```
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The production override adds Nginx (TLS termination, HTTP to HTTPS redirect), Gunicorn, a non-root container user, restart policies and log rotation. The domain and certificate paths in [`nginx/nginx.conf`](nginx/nginx.conf) belong to the author's domain and must be changed for another deployment.

## Testing

The test suite uses isolated settings: eager Celery, in-memory file storage, a local-memory cache and a fast password hasher. It needs PostgreSQL, which the Compose stack provides.

```
docker compose exec api pytest --ds=config.settings.test
docker compose exec api pytest --ds=config.settings.test --cov=apps --cov-report=term-missing
```

What is covered, with nearly 300 test functions:
- **Services:** booking, registration cancellation, ticket check-in, event lifecycle, authentication and one-time codes, profile photos.
- **API layer:** views (status codes, permissions, object ownership), serializers and validators, filters, the exception handler.
- **Data layer:** model constraints, selectors, permissions.
- **Infrastructure code:** Celery tasks and image processing.

Techniques: `factory_boy` factories, `freezegun` for time boundaries (24-hour cancellation deadline, 60-minute check-in window), `pytest-mock` for Celery dispatch, and an atomicity test that proves a failure in the middle of a booking rolls back the registration, the ticket and the seat counter.

## Key design decisions

**Pessimistic locking for seat booking.** The event row is locked with `SELECT ... FOR UPDATE` inside `transaction.atomic()`. For a hot row guarding a capacity counter this is simple and easy to reason about. The trade-off is lock contention on very popular events. A conditional `UPDATE ... WHERE seats_taken < capacity` would be the alternative if that became a bottleneck.

**A denormalized `seats_taken` counter guarded by a CHECK constraint.** Availability is a simple row read instead of a `COUNT(*)`. The database constraint turns any counter bug into a failed transaction instead of overbooking.

**A partial unique index instead of check-then-insert.** Duplicate registrations are prevented by the database, and the `IntegrityError` is translated into a `409 already_registered`. This is race-free and still allows re-registration after a cancellation.

**Emails dispatched in `transaction.on_commit`.** A worker can never receive a task for a ticket that is not yet committed, and a rolled-back booking sends nothing.

**Hashed one-time codes with attempt limits.** Codes are stored as HMAC-SHA256 digests, compared in constant time, expire after 15 minutes and lock after 5 failed attempts. The password-reset request returns the same `202` response whether or not the email exists, so it does not reveal registered addresses.