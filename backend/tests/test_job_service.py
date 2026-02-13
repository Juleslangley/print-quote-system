"""Minimal tests for JobService."""
import pytest
from unittest.mock import MagicMock

from app.services.job_service import generate_job_no, create_job
from app.models.job import Job


def test_generate_job_no_increments_sequence():
    db = MagicMock()
    row = MagicMock()
    row.next_val = 1
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = row
    db.flush = MagicMock()

    num = generate_job_no(db)
    assert num == "J0001"
    assert row.next_val == 2

    num2 = generate_job_no(db)
    assert num2 == "J0002"
    assert row.next_val == 3


def test_create_job_returns_id_and_job_no():
    db = MagicMock()
    seq_row = MagicMock()
    seq_row.next_val = 42
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = seq_row
    db.add = MagicMock()
    db.flush = MagicMock()

    job_id, job_no = create_job(db, customer_id=None, title="Test job")
    assert job_no == "J0042"
    assert len(job_id) == 36  # uuid string
    assert db.add.called
    added = db.add.call_args[0][0]
    assert isinstance(added, Job)
    assert added.job_no == "J0042"
    assert added.title == "Test job"
    assert added.status == "open"
