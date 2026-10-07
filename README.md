# Time-Off Management API

A FastAPI and SQLite backend for managing departments, employee shifts, rotating schedules, leave balances, and time-off requests.

The project is based on a practical scheduling problem: determining how much time off an employee is actually requesting when different departments, overnight shifts, and repeating work patterns are involved.

## Features

- Create and retrieve departments
- Create and retrieve shifts
- Create and retrieve employees
- Create and retrieve time-off requests
- Store employee vacation, personal, and sick leave balances
- Support repeating shift patterns with an anchor date
- Support overnight shifts
- Calculate requested leave hours based on overlap with an employee's scheduled work time
- Store time-off requests with pending status and creation timestamps
- Use SQLite foreign keys to link employees, departments, shifts, and requests

## Tech Stack

- Python
- FastAPI
- SQLite
- Pydantic
- Uvicorn

## Project Structure

```text
time-off-management-api/
├── main.py
├── database.py
├── models.py
├── requirements.txt
├── README.md
└── .gitignore
```

`main.py` contains the FastAPI application, routes, and scheduling logic.

`database.py` handles SQLite setup and database operations.

`models.py` contains the Pydantic models used to validate incoming API data.

## Running Locally

Create and activate a virtual environment if desired, then install the dependencies:

```bash
pip install -r requirements.txt
```

Start the API with:

```bash
uvicorn main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

FastAPI's interactive documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Current API Routes

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/` | Check that the API is running |
| GET | `/departments` | Retrieve all departments |
| POST | `/departments` | Create a department |
| GET | `/departments/{department_id}` | Retrieve one department |
| GET | `/shifts` | Retrieve all shifts |
| POST | `/shifts` | Create a shift |
| GET | `/shifts/{shift_id}` | Retrieve one shift |
| GET | `/employees` | Retrieve all employees |
| POST | `/employees` | Create an employee |
| GET | `/employees/{employee_id}` | Retrieve one employee |
| GET | `/time_off_requests` | Retrieve all time-off requests |
| POST | `/time_off_requests` | Create a time-off request |
| GET | `/time_off_requests/{time_off_request_id}` | Retrieve one time-off request |

## Scheduling Logic

Each shift stores:

- Start and end times
- Shift length
- A repeating work pattern
- The number of days in the repeating cycle
- An anchor date used to determine where the cycle begins

A work pattern uses `1` for a scheduled workday and `0` for a scheduled day off.

For example:

```text
11001110011000
```

The API uses the anchor date and repeating pattern to determine whether an employee is scheduled to work on a given date.

When a time-off request is created, the API calculates the overlap between the requested time range and the employee's scheduled shift. This also supports overnight shifts that continue into the following calendar day.

## Database

SQLite is used for local persistence.

The database contains four primary tables:

- `departments`
- `shifts`
- `employees`
- `time_off_requests`

Foreign keys connect employees to departments and shifts, and connect time-off requests to employees.

The generated `time_off.db` file is intended to remain local and should not be committed to Git.

## Project Status

This project is actively being developed as a portfolio backend project. The current version includes the core database structure, FastAPI routes, and schedule-based leave-hour calculation.
