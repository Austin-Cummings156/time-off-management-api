from datetime import UTC, date, datetime, time

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import database
import models
import services


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Give each test its own temporary SQLite database."""

    test_database = tmp_path / "test_time_off.db"

    monkeypatch.setattr(
        database,
        "DATABASE_PATH",
        test_database
    )

    database.create_database()

    return test_database


def create_test_department(
    max_people_off: int = 2
) -> int:
    return database.add_department(
        models.DepartmentCreate(
            name="Test Department",
            max_people_off=max_people_off
        )
    )


def create_test_shift(
    work_pattern: str = "1",
    cycle_length_days: int = 1,
    anchor_date: date = date(2026, 10, 21)
) -> int:
    return database.add_shift(
        models.ShiftCreate(
            name="Night Shift",
            start_time=time(19, 0),
            end_time=time(7, 0),
            length_hours=12,
            cycle_length_days=cycle_length_days,
            work_pattern=work_pattern,
            anchor_date=anchor_date
        )
    )


def create_test_employee(
    department_id: int,
    shift_id: int,
    name: str = "Test Employee",
    vacation_hours: float = 40
) -> int:
    return database.add_employee(
        models.EmployeeCreate(
            name=name,
            department_id=department_id,
            shift_id=shift_id,
            active=True,
            vacation_hours=vacation_hours,
            personal_hours=20,
            sick_hours=20
        )
    )


def test_calculate_shift_overlap():
    hours = services.calculate_shift_overlap(
        request_start=datetime(2026, 10, 21, 20, 0),
        request_end=datetime(2026, 10, 22, 2, 0),
        work_date=date(2026, 10, 21),
        shift_start_time=time(19, 0),
        shift_end_time=time(7, 0)
    )

    assert hours == 6.0


def test_calculate_partial_shift_overlap():
    hours = services.calculate_shift_overlap(
        request_start=datetime(2026, 10, 21, 21, 0),
        request_end=datetime(2026, 10, 22, 1, 0),
        work_date=date(2026, 10, 21),
        shift_start_time=time(19, 0),
        shift_end_time=time(7, 0)
    )

    assert hours == 4.0


def test_calculate_no_overlap():
    hours = services.calculate_shift_overlap(
        request_start=datetime(2026, 10, 21, 10, 0),
        request_end=datetime(2026, 10, 21, 12, 0),
        work_date=date(2026, 10, 21),
        shift_start_time=time(19, 0),
        shift_end_time=time(7, 0)
    )

    assert hours == 0.0


def test_invalid_shift_work_pattern():
    with pytest.raises(ValidationError):
        models.ShiftCreate(
            name="Night Shift",
            start_time=time(19, 0),
            end_time=time(7, 0),
            length_hours=12,
            cycle_length_days=4,
            work_pattern="1102",
            anchor_date=date(2026, 10, 21)
        )


def test_shift_pattern_length_must_match_cycle():
    with pytest.raises(ValidationError):
        models.ShiftCreate(
            name="Night Shift",
            start_time=time(19, 0),
            end_time=time(7, 0),
            length_hours=12,
            cycle_length_days=4,
            work_pattern="110",
            anchor_date=date(2026, 10, 21)
        )


def test_shift_length_must_match_times():
    with pytest.raises(ValidationError):
        models.ShiftCreate(
            name="Night Shift",
            start_time=time(19, 0),
            end_time=time(7, 0),
            length_hours=8,
            cycle_length_days=1,
            work_pattern="1",
            anchor_date=date(2026, 10, 21)
        )


def test_employee_cannot_have_negative_leave_balance():
    with pytest.raises(ValidationError):
        models.EmployeeCreate(
            name="Test Employee",
            department_id=1,
            shift_id=1,
            active=True,
            vacation_hours=-1,
            personal_hours=10,
            sick_hours=10
        )


def test_calculate_requested_hours_for_scheduled_day(test_db):
    department_id = create_test_department()
    shift_id = create_test_shift()
    employee_id = create_test_employee(
        department_id,
        shift_id
    )

    request = models.TimeOffRequestCreate(
        employee_id=employee_id,
        start_datetime=datetime(2026, 10, 21, 20, 0),
        end_datetime=datetime(2026, 10, 22, 2, 0),
        leave_type="vacation"
    )

    hours = services.calculate_requested_hours(request)

    assert hours == 6.0


def test_request_on_day_off_returns_zero(test_db):
    department_id = create_test_department()

    shift_id = create_test_shift(
        work_pattern="10",
        cycle_length_days=2,
        anchor_date=date(2026, 10, 21)
    )

    employee_id = create_test_employee(
        department_id,
        shift_id
    )

    request = models.TimeOffRequestCreate(
        employee_id=employee_id,
        start_datetime=datetime(2026, 10, 22, 19, 0),
        end_datetime=datetime(2026, 10, 23, 7, 0),
        leave_type="vacation"
    )

    hours = services.calculate_requested_hours(request)

    assert hours == 0.0


def test_overlapping_request_is_rejected(test_db):
    department_id = create_test_department()
    shift_id = create_test_shift()

    employee_id = create_test_employee(
        department_id,
        shift_id
    )

    existing_request = models.TimeOffRequestCreate(
        employee_id=employee_id,
        start_datetime=datetime(2026, 10, 21, 19, 0),
        end_datetime=datetime(2026, 10, 22, 7, 0),
        leave_type="vacation"
    )

    database.add_time_off_request(
        existing_request,
        hours_requested=12,
        created_at=datetime.now(UTC)
    )

    new_request = models.TimeOffRequestCreate(
        employee_id=employee_id,
        start_datetime=datetime(2026, 10, 21, 22, 0),
        end_datetime=datetime(2026, 10, 22, 2, 0),
        leave_type="vacation"
    )

    hours = services.calculate_requested_hours(new_request)

    with pytest.raises(HTTPException) as error:
        services.validate_time_off_request(
            new_request,
            hours
        )

    assert error.value.status_code == 409


def test_approval_deducts_leave_balance(test_db):
    department_id = create_test_department()
    shift_id = create_test_shift()

    employee_id = create_test_employee(
        department_id,
        shift_id,
        vacation_hours=40
    )

    request = models.TimeOffRequestCreate(
        employee_id=employee_id,
        start_datetime=datetime(2026, 10, 21, 19, 0),
        end_datetime=datetime(2026, 10, 22, 7, 0),
        leave_type="vacation"
    )

    request_id = database.add_time_off_request(
        request,
        hours_requested=12,
        created_at=datetime.now(UTC)
    )

    services.approve_time_off_request(request_id)

    updated_request = database.get_time_off_request(
        request_id
    )

    updated_employee = database.get_employee(
        employee_id
    )

    assert updated_request["status"] == "approved"
    assert updated_employee["vacation_hours"] == 28


def test_denial_does_not_deduct_leave_balance(test_db):
    department_id = create_test_department()
    shift_id = create_test_shift()

    employee_id = create_test_employee(
        department_id,
        shift_id,
        vacation_hours=40
    )

    request = models.TimeOffRequestCreate(
        employee_id=employee_id,
        start_datetime=datetime(2026, 10, 21, 19, 0),
        end_datetime=datetime(2026, 10, 22, 7, 0),
        leave_type="vacation"
    )

    request_id = database.add_time_off_request(
        request,
        hours_requested=12,
        created_at=datetime.now(UTC)
    )

    services.deny_time_off_request(request_id)

    updated_request = database.get_time_off_request(
        request_id
    )

    updated_employee = database.get_employee(
        employee_id
    )

    assert updated_request["status"] == "denied"
    assert updated_employee["vacation_hours"] == 40


def test_department_capacity_blocks_approval(test_db):
    department_id = create_test_department(
        max_people_off=1
    )

    shift_id = create_test_shift()

    employee_one = create_test_employee(
        department_id,
        shift_id,
        name="Employee One"
    )

    employee_two = create_test_employee(
        department_id,
        shift_id,
        name="Employee Two"
    )

    request_one = models.TimeOffRequestCreate(
        employee_id=employee_one,
        start_datetime=datetime(2026, 10, 21, 19, 0),
        end_datetime=datetime(2026, 10, 22, 7, 0),
        leave_type="vacation"
    )

    request_two = models.TimeOffRequestCreate(
        employee_id=employee_two,
        start_datetime=datetime(2026, 10, 21, 19, 0),
        end_datetime=datetime(2026, 10, 22, 7, 0),
        leave_type="vacation"
    )

    request_one_id = database.add_time_off_request(
        request_one,
        hours_requested=12,
        created_at=datetime.now(UTC)
    )

    request_two_id = database.add_time_off_request(
        request_two,
        hours_requested=12,
        created_at=datetime.now(UTC)
    )

    services.approve_time_off_request(
        request_one_id
    )

    with pytest.raises(HTTPException) as error:
        services.approve_time_off_request(
            request_two_id
        )

    assert error.value.status_code == 409

    second_request = database.get_time_off_request(
        request_two_id
    )

    second_employee = database.get_employee(
        employee_two
    )

    assert second_request["status"] == "pending"
    assert second_employee["vacation_hours"] == 40