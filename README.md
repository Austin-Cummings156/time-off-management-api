# Time-Off Management API

A FastAPI and SQLite backend for managing employee schedules, rotating shifts, leave balances, and time-off requests.

The project is based on a practical scheduling problem: determining how much time off an employee is actually requesting while accounting for overnight shifts, repeating work schedules, leave balances, overlapping requests, and department staffing limits.

## Features

- Create and retrieve departments
- Create and retrieve employee shifts
- Create and retrieve employees
- Submit and retrieve time-off requests
- Approve or deny pending requests
- Store vacation, personal, and sick leave balances
- Support repeating work patterns using an anchor date
- Support overnight shifts
- Calculate requested leave hours from scheduled work time
- Reject requests that do not overlap scheduled work
- Reject overlapping pending or approved requests for the same employee
- Validate available leave before submission and approval
- Deduct leave balances only when a request is approved
- Enforce department time-off capacity during approval
- Store creation timestamps in UTC
- Use SQLite foreign keys for related records
- Separate API routes, business logic, database operations, and validation models
- Include automated tests for scheduling and approval rules

## Tech Stack

- Python
- FastAPI
- SQLite
- Pydantic
- Uvicorn
- pytest

## Project Structure

```text
time-off-management-api/
├── main.py
├── services.py
├── database.py
├── models.py
├── requirements.txt
├── README.md
├── tests/
│   ├── __init__.py
│   └── test_services.py
└── .gitignore
```

### `main.py`

Defines the FastAPI application and HTTP routes.

### `services.py`

Contains scheduling calculations and business rules, including:

- calculating scheduled leave hours
- validating time-off requests
- checking leave balances
- approving requests
- denying requests
- checking department capacity

### `database.py`

Handles SQLite setup, queries, inserts, status changes, overlap checks, capacity queries, and approval transactions.

### `models.py`

Contains Pydantic models for validating incoming API data.

## Running Locally

Create and activate a virtual environment, then install the dependencies:

```bash
pip install -r requirements.txt
```

Start the API:

```bash
uvicorn main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive FastAPI documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## API Routes

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/` | Check API status |
| GET | `/departments` | Retrieve departments |
| POST | `/departments` | Create a department |
| GET | `/departments/{department_id}` | Retrieve one department |
| GET | `/shifts` | Retrieve shifts |
| POST | `/shifts` | Create a shift |
| GET | `/shifts/{shift_id}` | Retrieve one shift |
| GET | `/employees` | Retrieve employees |
| POST | `/employees` | Create an employee |
| GET | `/employees/{employee_id}` | Retrieve one employee |
| GET | `/time_off_requests` | Retrieve time-off requests |
| POST | `/time_off_requests` | Submit a time-off request |
| GET | `/time_off_requests/{time_off_request_id}` | Retrieve one request |
| PATCH | `/time_off_requests/{request_id}/status` | Approve or deny a request |

## Scheduling Logic

Each shift defines:

- start time
- end time
- shift length
- repeating work pattern
- cycle length
- anchor date

A work pattern uses `1` for a scheduled workday and `0` for a scheduled day off.

For example:

```text
11001110011000
```

The anchor date identifies the first position in the repeating pattern.

The API determines which days an employee is scheduled to work and calculates only the portion of a time-off request that overlaps those scheduled shifts.

Overnight shifts are assigned to the date on which the shift begins.

For example, a shift from:

```text
19:00 -> 07:00
```

belongs to the date on which the employee starts work at 19:00.

A request from:

```text
18:00 -> 02:00
```

therefore contains seven hours of scheduled leave:

```text
19:00 -> 02:00
```

## Request Validation

Before a request is stored, the API verifies that:

- the employee exists
- the employee is active
- the request overlaps scheduled work
- the employee has enough leave available
- the employee does not already have an overlapping pending or approved request

Leave types are limited to:

- `vacation`
- `personal`
- `sick`

New requests are stored with a `pending` status.

## Approval and Denial

Pending requests can be either:

```text
approved
denied
```

Approval rechecks:

- employee status
- available leave balance
- department capacity

When approval succeeds, the request status is changed and the appropriate leave balance is deducted in the same database transaction.

Denied requests do not deduct leave.

## Department Capacity

Each department defines a maximum number of employees who may have approved time off during an overlapping requested period.

Only approved requests count toward this limit. Pending and denied requests do not.

The current implementation uses conservative interval-overlap counting: an approved request is counted when any portion of its time range overlaps the request being evaluated.

## Database

SQLite is used for local persistence.

The database contains four tables:

- `departments`
- `shifts`
- `employees`
- `time_off_requests`

Foreign keys connect employees to departments and shifts and connect time-off requests to employees.

The generated `time_off.db` file remains local and should not be committed to Git.

## Testing

Run the automated test suite with:

```bash
python -m pytest
```

The tests cover:

- overnight shift overlap
- partial shift overlap
- non-overlapping requests
- invalid work patterns
- invalid shift lengths
- negative leave balances
- rotating scheduled days
- scheduled days off
- overlapping employee requests
- approval and leave deduction
- denial without leave deduction
- department capacity enforcement

Tests use temporary SQLite databases so the development database is not modified.

## Project Status

Complete portfolio project.

The project demonstrates a small layered FastAPI backend with schedule-based business logic, SQLite persistence, validation, transactional updates, and automated testing.
