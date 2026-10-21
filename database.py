from pathlib import Path
import sqlite3
from datetime import datetime

import models


BASE_FOLDER = Path(__file__).resolve().parent
DATABASE_PATH = BASE_FOLDER / "time_off.db"


def get_connection() -> sqlite3.Connection:
    """Create and return a configured SQLite connection."""

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def create_database() -> None:
    """Create the database tables if they do not already exist."""

    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                max_people_off INTEGER NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                length_hours REAL NOT NULL,
                cycle_length_days INTEGER NOT NULL,
                work_pattern TEXT NOT NULL,
                anchor_date TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department_id INTEGER NOT NULL,
                shift_id INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                vacation_hours REAL NOT NULL DEFAULT 0,
                personal_hours REAL NOT NULL DEFAULT 0,
                sick_hours REAL NOT NULL DEFAULT 0,
                
                FOREIGN KEY (department_id)
                    REFERENCES departments(id),
                FOREIGN KEY (shift_id)
                    REFERENCES shifts(id)
            );
            
            CREATE TABLE IF NOT EXISTS time_off_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                start_datetime TEXT NOT NULL,
                end_datetime TEXT NOT NULL,
                leave_type TEXT NOT NULL,
                hours_requested REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                notes TEXT,
                created_at TEXT NOT NULL,
                
                FOREIGN KEY (employee_id)
                    REFERENCES employees(id)
            );
            """
        )


# Department operations
def add_department(department: models.DepartmentCreate) -> int | None:
    """Add a department and return its generated database ID."""

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO departments (
                name,
                max_people_off
            )
            VALUES (?, ?)
            """,
            (
                department.name,
                department.max_people_off
            )
        )

        return cursor.lastrowid


def get_departments() -> list[dict]:
    """Return all departments from the database."""

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                name,
                max_people_off
            FROM departments
            ORDER BY name
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_department(department_id: int) -> dict | None:
    """Return one department by ID, or None if it does not exist."""

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                name,
                max_people_off
            FROM departments
            WHERE id = ?
            """,
            (department_id,)
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def update_department(
    department_id: int,
    department: models.DepartmentCreate
) -> bool:
    """Update a department and return whether a record was changed."""

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE departments
            SET
                name = ?,
                max_people_off = ?
            WHERE id = ?
            """,
            (
                department.name,
                department.max_people_off,
                department_id
            )
        )

        return cursor.rowcount > 0


def count_approved_department_overlaps(
    department_id: int,
    start_datetime: datetime,
    end_datetime: datetime
) -> int:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(DISTINCT employees.id) AS count
            FROM time_off_requests
            JOIN employees
              ON employees.id = time_off_requests.employee_id
            WHERE employees.department_id = ?
              AND time_off_requests.status = 'approved'
              AND time_off_requests.start_datetime < ?
              AND time_off_requests.end_datetime > ?
            """,
            (
                department_id,
                end_datetime.isoformat(),
                start_datetime.isoformat()
            )
        ).fetchone()

    return row["count"]


# Shift operations
def add_shift(shift: models.ShiftCreate) -> int | None:
    """Add a shift and return its generated database ID."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO shifts (
                name,
                start_time,
                end_time,
                length_hours,
                cycle_length_days,
                work_pattern,
                anchor_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                shift.name,
                shift.start_time.isoformat(),
                shift.end_time.isoformat(),
                shift.length_hours,
                shift.cycle_length_days,
                shift.work_pattern,
                shift.anchor_date.isoformat()
            )
        )
        
        return cursor.lastrowid

        
def get_shifts() -> list[dict]:
    """Return all shifts from the database."""
    
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                name,
                start_time,
                end_time,
                length_hours,
                cycle_length_days,
                work_pattern,
                anchor_date
            FROM shifts
            ORDER BY name
            """
        ).fetchall()
        
    return [dict(row) for row in rows]

    
def get_shift(shift_id: int) -> dict | None:
    """Return one shift by ID, or None if it does not exist."""
    
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                name,
                start_time,
                end_time,
                length_hours,
                cycle_length_days,
                work_pattern,
                anchor_date
            FROM shifts
            WHERE id = ?
            """,
            (shift_id,)
        ).fetchone()
        
    if row is None:
        return None
        
    return dict(row)
    
    
def update_shift(
    shift_id: int,
    shift: models.ShiftCreate
) -> bool:
    """Update a shift and return whether a record was changed."""
    
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE shifts
            SET
                name = ?,
                start_time = ?,
                end_time = ?,
                length_hours = ?,
                cycle_length_days = ?,
                work_pattern = ?,
                anchor_date = ?
            WHERE id = ?
            """,
            (
                shift.name,
                shift.start_time.isoformat(),
                shift.end_time.isoformat(),
                shift.length_hours,
                shift.cycle_length_days,
                shift.work_pattern,
                shift.anchor_date.isoformat(),
                shift_id
            )
        )
        
        return cursor.rowcount > 0
        

# Employee operations
def add_employee(employee: models.EmployeeCreate) -> int | None:
    """Add an employee and return its generated database ID."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO employees (
                name,
                department_id,
                shift_id,
                active,
                vacation_hours,
                personal_hours,
                sick_hours
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                employee.name,
                employee.department_id,
                employee.shift_id,
                employee.active,
                employee.vacation_hours,
                employee.personal_hours,
                employee.sick_hours
            )
        )
        
        return cursor.lastrowid
        

def get_employees() -> list[dict]:
    """Return all employees from the database."""
    
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                name,
                department_id,
                shift_id,
                active,
                vacation_hours,
                personal_hours,
                sick_hours
            FROM employees
            ORDER BY name
            """
        ).fetchall()
        
    return [dict(row) for row in rows]

    
def get_employee(employee_id: int) -> dict | None:
    """Return one employee by ID, or None if it does not exist."""
    
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                name,
                department_id,
                shift_id,
                active,
                vacation_hours,
                personal_hours,
                sick_hours
            FROM employees
            WHERE id = ?
            """,
            (employee_id,)
        ).fetchone()
        
    if row is None:
        return None
        
    return dict(row)
    
    
def update_employee(
    employee_id: int,
    employee: models.EmployeeCreate
) -> bool:
    """Update an employee and return whether a record was changed."""
    
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE employees
            SET
                name = ?,
                department_id = ?,
                shift_id = ?,
                active = ?,
                vacation_hours = ?,
                personal_hours = ?,
                sick_hours = ?
            WHERE id = ?
            """,
            (
                employee.name,
                employee.department_id,
                employee.shift_id,
                employee.active,
                employee.vacation_hours,
                employee.personal_hours,
                employee.sick_hours,
                employee_id
            )
        )
        
        return cursor.rowcount > 0


# Time-off request operations
def add_time_off_request(
    time_off_request: models.TimeOffRequestCreate,
    hours_requested: float,
    created_at: datetime
) -> int | None:
    """Add a time-off request and return its generated database ID."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO time_off_requests (
                employee_id,
                start_datetime,
                end_datetime,
                leave_type,
                status,
                hours_requested,
                created_at,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                time_off_request.employee_id,
                time_off_request.start_datetime.isoformat(),
                time_off_request.end_datetime.isoformat(),
                time_off_request.leave_type,
                "pending",
                hours_requested,
                created_at.isoformat(),
                time_off_request.notes
            )
        )
        
        return cursor.lastrowid

        
def get_time_off_requests() -> list[dict]:
    """Return all time-off requests from the database."""
    
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                employee_id,
                start_datetime,
                end_datetime,
                leave_type,
                status,
                hours_requested,
                created_at,
                notes
            FROM time_off_requests
            ORDER BY employee_id
            """
        ).fetchall()
        
    return [dict(row) for row in rows]

    
def get_time_off_request(request_id: int) -> dict | None:
    """Return one time-off request by ID, or None if it does not exist."""
    
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                employee_id,
                start_datetime,
                end_datetime,
                leave_type,
                status,
                hours_requested,
                created_at,
                notes
            FROM time_off_requests
            WHERE id = ?
            """,
            (request_id,)
        ).fetchone()
        
    if row is None:
        return None
        
    return dict(row)
    
    
def update_time_off_request(
    request_id: int,
    time_off_request: models.TimeOffRequestCreate,
    hours_requested: float
) -> bool:
    """Update a time-off request and return whether a record was changed."""
    
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE time_off_requests
            SET
                employee_id = ?,
                start_datetime = ?,
                end_datetime = ?,
                leave_type = ?,
                hours_requested = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                time_off_request.employee_id,
                time_off_request.start_datetime.isoformat(),
                time_off_request.end_datetime.isoformat(),
                time_off_request.leave_type,
                hours_requested,
                time_off_request.notes,
                request_id
            )
        )
        
        return cursor.rowcount > 0
        
        
def update_time_off_request_status(
    request_id: int,
    status: str
) -> bool:
    """Update a time-off request status and return whether a record was changed."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE time_off_requests
            SET status = ?
            WHERE id = ?
            """,
            (
                status,
                request_id
            )
        )

        return cursor.rowcount > 0


def has_overlapping_time_off_request(
    employee_id: int,
    start_datetime: datetime,
    end_datetime: datetime
) -> bool:
    """Return whether an employee has an overlapping active request."""

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT 1
            FROM time_off_requests
            WHERE employee_id = ?
              AND status IN ('pending', 'approved')
              AND start_datetime < ?
              AND end_datetime > ?
            LIMIT 1
            """,
            (
                employee_id,
                end_datetime.isoformat(),
                start_datetime.isoformat()
            )
        ).fetchone()

    return row is not None


def approve_time_off_request(
    request_id: int,
    employee_id: int,
    balance_column: str,
    hours_requested: float
) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            f"""
            UPDATE employees
            SET {balance_column} = {balance_column} - ?
            WHERE id = ?
            """,
            (
                hours_requested,
                employee_id
            )
        )

        if cursor.rowcount == 0:
            return False

        cursor = connection.execute(
            """
            UPDATE time_off_requests
            SET status = 'approved'
            WHERE id = ?
              AND status = 'pending'
            """,
            (request_id,)
        )

        if cursor.rowcount == 0:
            raise RuntimeError("Request could not be approved.")

    return True
        
        
if __name__ == "__main__":
    create_database()