"""Real unit tests of the current backend rules and Pydantic validators."""

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app import main as gp

@pytest.mark.parametrize('password',["TestPass123!","Été-2026-pass"])
def test_password_hash_and_verify(password):
    encoded=gp.hash_password(password)
    assert encoded != password
    assert gp.verify_password(password,encoded)
    assert not gp.verify_password(password+"wrong",encoded)

def test_invalid_password_hash_is_rejected():
    assert not gp.verify_password('example','corrupt-hash')

def test_valid_intervention_transitions():
    assert 'DIAGNOSIS' in gp.TRANSITIONS['REQUESTED']
    assert 'REPAIR' in gp.TRANSITIONS['DIAGNOSIS']
    assert 'COMPLETED' in gp.TRANSITIONS['REPAIR']
    assert not gp.TRANSITIONS['COMPLETED']

def test_forbidden_direct_transition():
    assert 'COMPLETED' not in gp.TRANSITIONS['REQUESTED']

def test_part_quantity_cannot_be_zero_or_negative():
    for qty in [0,-1]:
        with pytest.raises(ValidationError):gp.UsePartIn(part_id=1,quantity=qty)

def test_bulk_parts_must_be_nonempty():
    with pytest.raises(ValidationError):gp.UsePartsIn(items=[])

def test_negative_stock_is_invalid():
    with pytest.raises(ValidationError):gp.PartIn(sku='FIL-001',name='Filtre huile',stock=-1,unit_price='10.00')

def test_end_before_start_is_rejected_by_schedule():
    from datetime import datetime,timezone
    now=datetime(2026,11,29,10,0,tzinfo=timezone.utc)
    with pytest.raises(HTTPException) as exc:
        gp.check_schedule(None,None,now,now)
    assert exc.value.status_code==422
