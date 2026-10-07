from datetime import date, datetime, time

from pydantic import BaseModel


class DepartmentCreate(BaseModel):
    name: str
    max_people_off: int


class ShiftCreate(BaseModel):
    name: str
    start_time: time
    end_time: time
    length_hours: float
    cycle_length_days: int
    work_pattern: str
    anchor_date: date


class EmployeeCreate(BaseModel):
    name: str
    department_id: int
    shift_id: int
    active: bool
    vacation_hours: float
    personal_hours: float
    sick_hours: float


class TimeOffRequestCreate(BaseModel):
    employee_id: int
    start_datetime: datetime
    end_datetime: datetime
    leave_type: str
    status: str
    hours_requested: int
    created_at: datetime
    notes: str | None = None