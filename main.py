from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from datetime import date, datetime, time, timedelta

import database
import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.create_database()
    yield


app = FastAPI(lifespan=lifespan)


# Department operations
@app.get("/")
def home():
    return {
        "message": "Time-Off Request Management API is running."
    }


@app.get("/departments")
def get_departments():
    return database.get_departments()


@app.post("/departments")
def create_department(department: models.DepartmentCreate):
    department_id = database.add_department(department)

    return {
        "id": department_id,
        "name": department.name,
        "max_people_off": department.max_people_off
    }


@app.get("/departments/{department_id}")
def get_department(department_id: int):
    department = database.get_department(department_id)

    if department is None:
        raise HTTPException(
            status_code=404,
            detail="Department not found."
        )

    return department


# Shift operations
@app.get("/shifts")
def get_shifts():
    return database.get_shifts()


@app.post("/shifts")
def create_shift(shift: models.ShiftCreate):
    shift_id = database.add_shift(shift)

    return {
        "id": shift_id,
        "name": shift.name,
        "start_time": shift.start_time,
        "end_time": shift.end_time,
        "length_hours": shift.length_hours,
        "cycle_length_days": shift.cycle_length_days,
        "work_pattern": shift.work_pattern,
        "anchor_date": shift.anchor_date,
    }


@app.get("/shifts/{shift_id}")
def get_shift(shift_id: int):
    shift = database.get_shift(shift_id)

    if shift is None:
        raise HTTPException(
            status_code=404,
            detail="shift not found."
        )

    return shift


# Employee operations
@app.get("/employees")
def get_employees():
    return database.get_employees()


@app.post("/employees")
def create_employee(employee: models.EmployeeCreate):
    employee_id = database.add_employee(employee)

    return {
        "id": employee_id,
        "name": employee.name,
        "department_id": employee.department_id,
        "shift_id": employee.shift_id,
        "active": employee.active,
        "vacation_hours": employee.vacation_hours,
        "personal_hours": employee.personal_hours,
        "sick_hours": employee.sick_hours
    }


@app.get("/employees/{employee_id}")
def get_employee(employee_id: int):
    employee = database.get_employee(employee_id)

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="employee not found."
        )

    return employee


def calculate_shift_overlap(
    request_start: datetime,
    request_end: datetime,
    work_date: date,
    shift_start_time: time,
    shift_end_time: time
) -> float:
    shift_start = datetime.combine(work_date, shift_start_time)

    if shift_end_time <= shift_start_time:
        shift_end = datetime.combine(
            work_date + timedelta(days=1),
            shift_end_time
        )

    else:
        shift_end = datetime.combine(
            work_date,
            shift_end_time
        )

    overlap_start = max(request_start, shift_start)
    overlap_end = min(shift_end, request_end)

    if overlap_end <= overlap_start:
        return 0.0

    duration = overlap_end - overlap_start

    return duration.total_seconds() / 3600


def is_scheduled_workday(
    work_date: date,
    anchor_date: date,
    work_pattern: str
) -> bool:
    days_since_anchor = (work_date - anchor_date).days
    pattern_position = days_since_anchor % len(work_pattern)

    return work_pattern[pattern_position] == "1"


def calculate_requested_hours(
    time_off_request: models.TimeOffRequestCreate
) -> float:
    if time_off_request.end_datetime <= time_off_request.start_datetime:
        raise HTTPException(
            status_code=400,
            detail="End datetime must be after start datetime."
        )

    employee = database.get_employee(time_off_request.employee_id)

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="employee not found."
        )

    shift = database.get_shift(employee["shift_id"])

    if shift is None:
        raise HTTPException(
            status_code=404,
            detail="shift not found."
        )

    shift_start_time = time.fromisoformat(shift["start_time"])
    shift_end_time = time.fromisoformat(shift["end_time"])
    anchor_date = date.fromisoformat(shift["anchor_date"])
    work_pattern = shift["work_pattern"]

    total_hours = 0.0

    current_date = (time_off_request.start_datetime.date() - timedelta(days=1))
    final_date = (time_off_request.end_datetime.date())

    while current_date <= final_date:
        if is_scheduled_workday(
                current_date,
                anchor_date,
                work_pattern
        ):
            total_hours += calculate_shift_overlap(
                time_off_request.start_datetime,
                time_off_request.end_datetime,
                current_date,
                shift_start_time,
                shift_end_time
            )

        current_date += timedelta(days=1)

    return total_hours


# Time-off request operations
@app.get("/time_off_requests")
def get_time_off_requests():
    return database.get_time_off_requests()


@app.post("/time_off_requests")
def create_time_off_request(time_off_request: models.TimeOffRequestCreate):
    hours_requested = calculate_requested_hours(time_off_request)

    created_at = datetime.now()


    time_off_request_id = database.add_time_off_request(
        time_off_request,
        hours_requested,
        created_at
    )

    return {
        "id": time_off_request_id,
        "employee_id": time_off_request.employee_id,
        "start_datetime": time_off_request.start_datetime,
        "end_datetime": time_off_request.end_datetime,
        "leave_type": time_off_request.leave_type,
        "status": "pending",
        "hours_requested": hours_requested,
        "created_at": created_at,
        "notes": time_off_request.notes
    }


@app.get("/time_off_requests/{time_off_request_id}")
def get_time_off_request(time_off_request_id: int):
    time_off_request = database.get_time_off_request(time_off_request_id)

    if time_off_request is None:
        raise HTTPException(
            status_code=404,
            detail="time_off_request not found."
        )

    return time_off_request


