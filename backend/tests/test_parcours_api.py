"""API tests against a disposable SQLite database, never the Docker production DB."""
from datetime import datetime,timedelta,timezone
from sqlalchemy import select
from app import main as gp

def test_health(environment):
    client,*_=environment
    assert client.get('/api/health').json()['status']=='ok'

def test_client_cannot_create_intervention(scenario):
    client,tokens,users,mid,vid,pid=scenario
    r=client.post('/api/interventions',headers=tokens['CLIENT'],json={"vehicle_id":vid,"mechanic_id":mid,"description":"Vidange"})
    assert r.status_code==403

def test_client_cannot_create_part(scenario):
    client,tokens,users,mid,vid,pid=scenario
    r=client.post('/api/parts',headers=tokens['CLIENT'],json={"sku":"HUI-002","name":"Huile moteur","stock":10,"unit_price":"30.00"})
    assert r.status_code==403

def test_appointment_acceptance_updates_client_status(scenario):
    client,tokens,users,mid,vid,pid=scenario
    now=datetime(2026,11,28,10,0,tzinfo=timezone.utc)
    rdv=client.post('/api/appointments',headers=tokens['CLIENT'],json={"vehicle_id":vid,"mechanic_id":mid,"starts_at":now.isoformat(),"ends_at":(now+timedelta(hours=1)).isoformat(),"reason":"Vidange moteur"})
    assert rdv.status_code==201,rdv.text
    aid=rdv.json()['id']
    assert rdv.json()['status']=='PENDING'
    denied=client.patch(f'/api/appointments/{aid}/accept',headers=tokens['CLIENT'])
    assert denied.status_code==403
    accepted=client.patch(f'/api/appointments/{aid}/accept',headers=tokens['MECANICIEN'])
    assert accepted.status_code==200,accepted.text
    assert accepted.json()['status']=='PLANNED'
    assert client.patch(f'/api/appointments/{aid}/accept',headers=tokens['MECANICIEN']).status_code==409
    visible=client.get('/api/appointments',headers=tokens['CLIENT'])
    assert visible.status_code==200
    assert next(x for x in visible.json() if x['id']==aid)['status']=='PLANNED'

def test_bulk_part_deduction_and_insufficient_stock_atomic(scenario):
    client,tokens,users,mid,vid,pid=scenario
    inter=client.post('/api/interventions',headers=tokens['ADMIN'],json={"vehicle_id":vid,"mechanic_id":mid,"description":"Vidange","labor_cost":"40.00"})
    assert inter.status_code==201,inter.text
    iid=inter.json()['id']
    for status,diagnosis in [('DIAGNOSIS',None),('REPAIR','Filtre usé')]:
        payload={"status":status}
        if diagnosis:payload['diagnosis']=diagnosis
        r=client.patch(f'/api/interventions/{iid}/status',headers=tokens['MECANICIEN'],json=payload)
        assert r.status_code==200,r.text
    second=client.post('/api/parts',headers=tokens['ADMIN'],json={"sku":"HUI-002","name":"Huile moteur","stock":5,"unit_price":"95.00"})
    assert second.status_code==201,second.text
    pid2=second.json()['id']
    path=f'/api/interventions/{iid}/parts/bulk'
    failed=client.post(path,headers=tokens['MECANICIEN'],json={"items":[{"part_id":pid,"quantity":2},{"part_id":pid2,"quantity":6}]})
    assert failed.status_code==409,failed.text
    with gp.SessionLocal() as db:
        assert db.get(gp.Part,pid).stock==20
        assert db.get(gp.Part,pid2).stock==5
    success=client.post(path,headers=tokens['MECANICIEN'],json={"items":[{"part_id":pid,"quantity":2},{"part_id":pid2,"quantity":1}]})
    assert success.status_code==201,success.text
    with gp.SessionLocal() as db:
        assert db.get(gp.Part,pid).stock==18
        assert db.get(gp.Part,pid2).stock==4
    dashboard=client.get('/api/dashboard',headers=tokens['ADMIN'])
    assert dashboard.status_code==200
    assert dashboard.json()['parts_low_stock']==1
    assert dashboard.json()['stock_alerts'][0]['level']=='FAIBLE'
    assert client.post(path,headers=tokens['MECANICIEN'],json={"items":[{"part_id":pid,"quantity":1}]}).status_code==409

def test_unauthed_user_is_rejected(environment):
    client,*_=environment
    assert client.get('/api/vehicles').status_code==401

def test_client_only_sees_own_vehicles(scenario):
    client,tokens,users,mid,vid,pid=scenario
    r=client.get('/api/vehicles',headers=tokens['CLIENT'])
    assert r.status_code==200
    assert {x['id'] for x in r.json()}=={vid}
