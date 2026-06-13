from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api.deps import assert_modify, assert_view, can_modify, can_view


def user(role: str, id: str = "u1", department: str | None = None):
    return SimpleNamespace(role=role, id=id, department=department)


ADMIN = user("admin", id="admin-1")
RADIOLOGIST = user("radiologist", id="rad-1", department="radiology")
CHIEF = user("chief_physician", id="chief-1", department="radiology")


# ── can_view ──────────────────────────────────────────────────────────────────

def test_admin_views_everything():
    assert can_view("someone-else", "oncology", ADMIN)
    assert can_view(None, None, ADMIN)


def test_owner_views_own_resource():
    assert can_view("rad-1", "radiology", RADIOLOGIST)


def test_radiologist_cannot_view_others():
    assert not can_view("rad-2", "radiology", RADIOLOGIST)


def test_chief_views_same_department():
    assert can_view("rad-1", "radiology", CHIEF)


def test_chief_cannot_view_other_department():
    assert not can_view("onc-1", "oncology", CHIEF)


def test_chief_without_department_info_denied():
    assert not can_view("rad-1", None, CHIEF)
    chief_no_dept = user("chief_physician", id="chief-2", department=None)
    assert not can_view("rad-1", "radiology", chief_no_dept)


def test_ownerless_resource_hidden_from_non_admin():
    assert not can_view(None, None, RADIOLOGIST)


# ── can_modify ────────────────────────────────────────────────────────────────

def test_admin_modifies_everything():
    assert can_modify("someone-else", ADMIN)


def test_owner_modifies_own_resource():
    assert can_modify("rad-1", RADIOLOGIST)


def test_chief_cannot_modify_department_resources():
    # chiefs may view department work, but not alter it
    assert not can_modify("rad-1", CHIEF)


# ── assert helpers ────────────────────────────────────────────────────────────

def test_assert_view_raises_404_not_403():
    with pytest.raises(HTTPException) as exc:
        assert_view("rad-2", "oncology", RADIOLOGIST)
    assert exc.value.status_code == 404  # don't leak existence


def test_assert_modify_raises_403():
    with pytest.raises(HTTPException) as exc:
        assert_modify("rad-2", RADIOLOGIST)
    assert exc.value.status_code == 403
