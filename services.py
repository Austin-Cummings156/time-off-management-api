from fastapi import HTTPException
from datetime import date, datetime, time, timedelta

import database
import models


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
            detail="Employee not found."
        )

    shift = database.get_shift(employee["shift_id"])

    if shift is None:
        raise HTTPException(
            status_code=404,
            detail="Shift not found."
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


def validate_time_off_request(
        time_off_request: models.TimeOffRequestCreate,
        hours_requested: float
) -> None:
    employee = database.get_employee(time_off_request.employee_id)

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="Employee not found."
        )

    if not employee["active"]:
        raise HTTPException(
            status_code=400,
            detail="Inactive employees cannot request time off."
        )

    if hours_requested <= 0:
        raise HTTPException(
            status_code=400,
            detail="Request does not overlap any scheduled work hours."
        )

    balance_key = f"{time_off_request.leave_type}_hours"
    available_hours = employee[balance_key]

    if hours_requested > available_hours:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Request exceeds employee "
                f"{time_off_request.leave_type} balance."
            )
        )

    if database.has_overlapping_time_off_request(
            employee["id"],
            time_off_request.start_datetime,
            time_off_request.end_datetime
    ):
        raise HTTPException(
            status_code=409,
            detail="Employee already has an overlapping time-off request."
        )


def approve_time_off_request(request_id: int) -> dict:
    request = database.get_time_off_request(request_id)

    if request is None:
        raise HTTPException(404, "Time-off request not found.")

    if request["status"] != "pending":
        raise HTTPException(409, "Only pending requests can be approved.")

    employee = database.get_employee(request["employee_id"])

    if employee is None:
        raise HTTPException(404, "Employee not found.")

    if not employee["active"]:
        raise HTTPException(
            409,
            "Inactive employee request cannot be approved."
        )

    department = database.get_department(employee["department_id"])

    if department is None:
        raise HTTPException(404, "Department not found.")

    available_hours = employee[f"{request['leave_type']}_hours"]

    if request["hours_requested"] > available_hours:
        raise HTTPException(409, "Insufficient leave balance.")

    overlapping_approved = database.count_approved_department_overlaps(
        employee["department_id"],
        datetime.fromisoformat(request["start_datetime"]),
        datetime.fromisoformat(request["end_datetime"])
    )

    if overlapping_approved >= department["max_people_off"]:
        raise HTTPException(
            409,
            "Department time-off capacity has been reached."
        )

    approved = database.approve_time_off_request(
        request_id,
        employee["id"],
        request["leave_type"],
        request["hours_requested"]
    )

    if not approved:
        raise HTTPException(
            409,
            "Request could not be approved."
        )

    return database.get_time_off_request(request_id)


def deny_time_off_request(request_id: int) -> dict:
    request = database.get_time_off_request(request_id)

    if request is None:
        raise HTTPException(404, "Time-off request not found.")

    if request["status"] != "pending":
        raise HTTPException(409, "Only pending requests can be denied.")

    updated = database.update_time_off_request_status(
        request_id,
        "denied"
    )

    if not updated:
        raise HTTPException(
            409,
            "Request could not be denied."
        )

    return database.get_time_off_request(request_id)