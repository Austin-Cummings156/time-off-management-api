from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class DepartmentCreate(BaseModel):
    name: str
    max_people_off: int = Field(gt = 0)


class ShiftCreate(BaseModel):
    name: str
    start_time: time
    end_time: time
    length_hours: float = Field(gt=0)
    cycle_length_days: int = Field(gt=0)
    work_pattern: str
    anchor_date: date

    @model_validator(mode="after")
    def validate_shift(self):
        if any(character not in {"0", "1"} for character in self.work_pattern):
            raise ValueError("Work pattern must contain only 0 and 1.")

        if len(self.work_pattern) != self.cycle_length_days:
            raise ValueError(
                "Work pattern length must match cycle length."
            )

        start_seconds = (
                self.start_time.hour * 3600
                + self.start_time.minute * 60
                + self.start_time.second
        )

        end_seconds = (
                self.end_time.hour * 3600
                + self.end_time.minute * 60
                + self.end_time.second
        )

        if end_seconds <= start_seconds:
            end_seconds += 24 * 3600

        calculated_length = (end_seconds - start_seconds) / 3600

        if abs(self.length_hours - calculated_length) > 0.01:
            raise ValueError(
                "Shift length must match the start and end times."
            )

        return self


class EmployeeCreate(BaseModel):
    name: str
    department_id: int
    shift_id: int
    active: bool
    vacation_hours: float = Field(ge=0)
    personal_hours: float = Field(ge=0)
    sick_hours: float = Field(ge=0)


class TimeOffRequestCreate(BaseModel):
    employee_id: int
    start_datetime: datetime
    end_datetime: datetime
    leave_type: Literal["vacation", "personal", "sick"]
    notes: str | None = None


class TimeOffRequestStatusUpdate(BaseModel):
    status: Literal["approved", "denied"]