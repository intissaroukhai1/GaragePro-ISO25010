"""GaragePro REST API: role-controlled workshop management."""
from __future__ import annotations
from contextlib import asynccontextmanager
import hashlib
import base64
import binascii
import io
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import jwt
from PIL import Image, UnidentifiedImageError
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, LargeBinary, UniqueConstraint, create_engine, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./garagepro.db')
JWT_SECRET = os.getenv('JWT_SECRET', 'development-only-change-this-secret-before-production')
JWT_ALGORITHM = 'HS256'
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(20), default='CLIENT')
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Vehicle(Base):
    __tablename__ = 'vehicles'
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    plate: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    brand: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(100))
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner: Mapped[User] = relationship()

class VehiclePhoto(Base):
    __tablename__ = 'vehicle_photos'
    vehicle_id: Mapped[int] = mapped_column(ForeignKey('vehicles.id', ondelete='CASCADE'), primary_key=True)
    content_type: Mapped[str] = mapped_column(String(30), default='image/jpeg')
    image_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

class VehiclePhotoInput(BaseModel):
    image: str  # data:image/jpeg;base64,... (3 MB max after compression)


class Mechanic(Base):
    __tablename__ = 'mechanics'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True)
    specialty: Mapped[str] = mapped_column(String(120), default='Général')
    user: Mapped[User] = relationship()

class Part(Base):
    __tablename__ = 'parts'
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)

class Appointment(Base):
    __tablename__ = 'appointments'
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey('vehicles.id'))
    mechanic_id: Mapped[int | None] = mapped_column(ForeignKey('mechanics.id'), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default='PENDING')
    vehicle: Mapped[Vehicle] = relationship()
    mechanic: Mapped[Mechanic | None] = relationship()

class Intervention(Base):
    __tablename__ = 'interventions'
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey('vehicles.id'))
    mechanic_id: Mapped[int | None] = mapped_column(ForeignKey('mechanics.id'), nullable=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey('appointments.id'), nullable=True, unique=True)
    description: Mapped[str] = mapped_column(Text)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default='REQUESTED', index=True)
    labor_cost: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    vehicle: Mapped[Vehicle] = relationship()
    mechanic: Mapped[Mechanic | None] = relationship()

class PartUsage(Base):
    __tablename__ = 'part_usages'
    __table_args__ = (UniqueConstraint('intervention_id','part_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    intervention_id: Mapped[int] = mapped_column(ForeignKey('interventions.id'))
    part_id: Mapped[int] = mapped_column(ForeignKey('parts.id'))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12,2))
    part: Mapped[Part] = relationship()

class WorkReport(Base):
    __tablename__ = 'work_reports'
    id: Mapped[int] = mapped_column(primary_key=True)
    intervention_id: Mapped[int] = mapped_column(ForeignKey('interventions.id'), unique=True)
    mechanic_id: Mapped[int] = mapped_column(ForeignKey('mechanics.id'))
    work_done: Mapped[str] = mapped_column(Text)
    observations: Mapped[str] = mapped_column(Text, default='')
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Invoice(Base):
    __tablename__ = 'invoices'
    id: Mapped[int] = mapped_column(primary_key=True)
    intervention_id: Mapped[int] = mapped_column(ForeignKey('interventions.id'), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2))
    status: Mapped[str] = mapped_column(String(20), default='UNPAID')
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    intervention: Mapped[Intervention] = relationship()

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    action: Mapped[str] = mapped_column(String(100))
    resource: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
class Register(Input):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
class Login(Input):
    email: EmailStr
    password: str
class UserCreate(Register):
    role: str = 'CLIENT'
class VehicleIn(Input):
    owner_id: int | None = None
    plate: str = Field(min_length=3, max_length=40)
    brand: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    year: int | None = Field(default=None, ge=1900, le=2100)
class MechanicIn(Input):
    user_id: int
    specialty: str = Field(default='Général', max_length=120)
class PartIn(Input):
    sku: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=160)
    stock: int = Field(ge=0)
    unit_price: Decimal = Field(ge=0, decimal_places=2)
class AppointmentIn(Input):
    vehicle_id: int
    mechanic_id: int | None = None
    starts_at: datetime
    ends_at: datetime
    reason: str = Field(min_length=3)
class AppointmentDecisionIn(Input):
    decision: str

class InterventionIn(Input):
    vehicle_id: int
    mechanic_id: int | None = None
    appointment_id: int | None = None
    description: str = Field(min_length=3)
    labor_cost: Decimal = Field(default=Decimal(0), ge=0)
class TransitionIn(Input):
    status: str
    diagnosis: str | None = None
class UsePartIn(Input):
    part_id: int
    quantity: int = Field(gt=0)
class UsePartsIn(Input):
    items: list[UsePartIn] = Field(min_length=1, max_length=50)
class WorkReportIn(Input):
    work_done: str = Field(min_length=5, max_length=4000)
    observations: str = Field(default='', max_length=4000)

class InvoiceIn(Input):
    status: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    startup()
    yield

app = FastAPI(title='GaragePro API', version='1.0.0', description='Gestion de garage automobile et interventions', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173,http://localhost:3000').split(','), allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

def startup():
    Base.metadata.create_all(engine)
    if os.getenv('SEED_DEMO', 'true').lower() == 'true':
        with SessionLocal() as db:
            if db.scalar(select(func.count()).select_from(User)) == 0:
                users = [('Administrateur','admin@gmail.com','ADMIN'),('Mécanicien Demo','mecanicien@gmail.com','MECANICIEN'),('Client Demo','client@gmail.com','CLIENT')]
                for name, email, role in users:
                    db.add(User(name=name, email=email, password_hash=hash_password(os.getenv('DEMO_PASSWORD','Demo12345!')), role=role))
                db.flush()
                mech = db.scalar(select(User).where(User.role == 'MECANICIEN'))
                db.add(Mechanic(user_id=mech.id, specialty='Mécanique générale'))
                db.commit()

def db_session():
    with SessionLocal() as db:
        yield db

bearer = HTTPBearer(auto_error=False)
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),390000).hex()
    return f'pbkdf2_sha256${salt}${digest}'
def verify_password(password: str, encoded: str) -> bool:
    try:
        _,salt,digest=encoded.split('$')
        computed=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),390000).hex()
        return hmac.compare_digest(computed,digest)
    except (ValueError, TypeError):
        return False

def current_user(credentials: HTTPAuthorizationCredentials | None=Depends(bearer), db: Session=Depends(db_session)) -> User:
    if not credentials: raise HTTPException(401,'Authentification requise')
    try:
        payload=jwt.decode(credentials.credentials,JWT_SECRET,algorithms=[JWT_ALGORITHM])
        uid=int(payload['sub'])
    except (jwt.PyJWTError,ValueError,KeyError):
        raise HTTPException(401,'Token invalide')
    user=db.get(User,uid)
    if user is None or not user.active: raise HTTPException(401,'Compte inactif ou inexistant')
    return user

def require(*roles):
    def dep(user: User=Depends(current_user)):
        if user.role not in roles: raise HTTPException(403,'Accès refusé')
        return user
    return dep

def audit(db: Session, user: User, action: str, obj: str, obj_id: int | None):
    db.add(AuditLog(user_id=user.id, action=action, resource=obj, resource_id=obj_id))

def get_or_404(db: Session, cls: Any, id: int):
    obj=db.get(cls,id)
    if obj is None: raise HTTPException(404,f'{cls.__name__} introuvable')
    return obj

def save(db: Session, user: User, action: str, obj: Any):
    try:
        db.flush()
        audit(db,user,action,obj.__tablename__,obj.id)
        db.commit()
        db.refresh(obj)
        return obj
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'Conflit : doublon ou contrainte de base de données')

def serialize(o: Any):
    return {c.name: (str(getattr(o,c.name)) if isinstance(getattr(o,c.name),Decimal) else getattr(o,c.name)) for c in o.__table__.columns}

def owned_vehicle(db:Session,vehicle_id:int,user:User):
    v=get_or_404(db,Vehicle,vehicle_id)
    if user.role=='CLIENT' and v.owner_id!=user.id: raise HTTPException(403,'Véhicule non autorisé')
    return v

def can_access_intervention(db:Session,i:Intervention,user:User):
    if user.role=='CLIENT': owned_vehicle(db,i.vehicle_id,user)
    if user.role=='MECANICIEN':
        mechanic=db.scalar(select(Mechanic).where(Mechanic.user_id==user.id))
        if mechanic is None or i.mechanic_id!=mechanic.id: raise HTTPException(403,'Intervention non affectée')

@app.get('/api/health')
def health(): return {'status':'ok','service':'garagepro'}

@app.post('/api/auth/register',status_code=201)
def register(data:Register,db:Session=Depends(db_session)):
    if db.scalar(select(User).where(User.email==data.email.lower())): raise HTTPException(409,'Email déjà utilisé')
    u=User(name=data.name,email=data.email.lower(),password_hash=hash_password(data.password),role='CLIENT')
    db.add(u)
    try: db.commit();db.refresh(u)
    except IntegrityError: db.rollback();raise HTTPException(409,'Email déjà utilisé')
    return {'id':u.id,'email':u.email,'role':u.role}

@app.post('/api/auth/login')
def login(data:Login,db:Session=Depends(db_session)):
    u=db.scalar(select(User).where(User.email==data.email.lower()))
    if not u or not u.active or not verify_password(data.password,u.password_hash): raise HTTPException(401,'Identifiants invalides')
    token=jwt.encode({'sub':str(u.id),'exp':datetime.now(timezone.utc)+timedelta(hours=8)},JWT_SECRET,algorithm=JWT_ALGORITHM)
    return {'access_token':token,'token_type':'bearer','user':{'id':u.id,'name':u.name,'email':u.email,'role':u.role}}

@app.get('/api/auth/me')
def me(user:User=Depends(current_user)): return {'id':user.id,'name':user.name,'email':user.email,'role':user.role}

@app.get('/api/users')
def users(db:Session=Depends(db_session),user:User=Depends(require('ADMIN'))):
    return [{'id':u.id,'name':u.name,'email':u.email,'role':u.role,'active':u.active} for u in db.scalars(select(User).order_by(User.id)).all()]

@app.post('/api/users',status_code=201)
def create_user(data:UserCreate,db:Session=Depends(db_session),user:User=Depends(require('ADMIN'))):
    if data.role not in ('ADMIN','MECANICIEN','CLIENT'): raise HTTPException(422,'Rôle invalide')
    obj=User(name=data.name,email=data.email.lower(),password_hash=hash_password(data.password),role=data.role)
    db.add(obj);save(db,user,'CREATE',obj)
    return {'id':obj.id,'name':obj.name,'email':obj.email,'role':obj.role}

def mechanic_visible_vehicle_ids(db: Session, mechanic: Mechanic | None):
    """Administrator-created vehicles are garage-wide; client vehicles require a confirmed booking.

    Existing vehicles are recognized by their CREATE audit event. No migration or database reset.
    """
    admin_created = (select(AuditLog.resource_id)
        .join(User, AuditLog.user_id == User.id)
        .where(AuditLog.resource == 'vehicles', AuditLog.action == 'CREATE', User.role == 'ADMIN'))
    if mechanic is None:
        return admin_created
    accepted = (select(Appointment.vehicle_id)
        .where(Appointment.mechanic_id == mechanic.id, Appointment.status == 'PLANNED'))
    assigned = select(Intervention.vehicle_id).where(Intervention.mechanic_id == mechanic.id)
    return admin_created.union(accepted, assigned)

@app.get('/api/vehicles')
def vehicles(q:str='',db:Session=Depends(db_session),user:User=Depends(current_user)):
    stmt=select(Vehicle)
    if user.role=='CLIENT':stmt=stmt.where(Vehicle.owner_id==user.id)
    elif user.role=='MECANICIEN':
        m=db.scalar(select(Mechanic).where(Mechanic.user_id==user.id))
        stmt=stmt.where(Vehicle.id.in_(mechanic_visible_vehicle_ids(db, m)))
    if q:stmt=stmt.where(or_(Vehicle.plate.ilike(f'%{q}%'),Vehicle.brand.ilike(f'%{q}%'),Vehicle.model.ilike(f'%{q}%')))
    return [serialize(o) for o in db.scalars(stmt.order_by(Vehicle.id.desc())).all()]

@app.post('/api/vehicles',status_code=201)
def create_vehicle(data:VehicleIn,db:Session=Depends(db_session),user:User=Depends(current_user)):
    if user.role=='MECANICIEN':raise HTTPException(403,'Accès refusé')
    owner_id=user.id if user.role=='CLIENT' else data.owner_id
    if owner_id is None:raise HTTPException(422,'owner_id requis pour admin')
    owner=get_or_404(db,User,owner_id)
    if owner.role!='CLIENT':raise HTTPException(422,'Propriétaire doit être CLIENT')
    obj=Vehicle(owner_id=owner_id,plate=data.plate.upper(),brand=data.brand,model=data.model,year=data.year)
    db.add(obj);save(db,user,'CREATE',obj);return serialize(obj)

@app.put('/api/vehicles/{id}')
def update_vehicle(id:int,data:VehicleIn,db:Session=Depends(db_session),user:User=Depends(current_user)):
    if user.role=='MECANICIEN':raise HTTPException(403,'Accès refusé')
    obj=owned_vehicle(db,id,user)
    if user.role=='ADMIN' and data.owner_id:
        owner=get_or_404(db,User,data.owner_id)
        if owner.role!='CLIENT':raise HTTPException(422,'Propriétaire invalide')
        obj.owner_id=data.owner_id
    obj.plate=data.plate.upper();obj.brand=data.brand;obj.model=data.model;obj.year=data.year
    save(db,user,'UPDATE',obj);return serialize(obj)

@app.delete('/api/vehicles/{id}')
def delete_vehicle(id:int,db:Session=Depends(db_session),user:User=Depends(current_user)):
    if user.role=='MECANICIEN':raise HTTPException(403,'Accès refusé')
    obj=owned_vehicle(db,id,user)
    if db.scalar(select(func.count()).select_from(Intervention).where(Intervention.vehicle_id==id)) or db.scalar(select(func.count()).select_from(Appointment).where(Appointment.vehicle_id==id)):
        raise HTTPException(409,'Véhicule lié à des interventions/rendez-vous')
    photo=db.get(VehiclePhoto,id)
    if photo: db.delete(photo)
    audit(db,user,'DELETE','vehicles',id);db.delete(obj);db.commit();return {'deleted':True}

def check_vehicle_photo_access(db: Session, vehicle_id: int, user: User) -> None:
    vehicle = get_or_404(db, Vehicle, vehicle_id)
    if user.role == 'CLIENT' and vehicle.owner_id != user.id:
        raise HTTPException(403, 'Photo du véhicule non autorisée')
    if user.role == 'MECANICIEN':
        mech = db.scalar(select(Mechanic).where(Mechanic.user_id == user.id))
        allowed = db.scalar(select(Vehicle.id).where(
            Vehicle.id == vehicle_id,
            Vehicle.id.in_(mechanic_visible_vehicle_ids(db, mech))
        )) is not None
        if not allowed:
            raise HTTPException(403, 'Photo du véhicule non autorisée')

@app.get('/api/vehicles/{id}/photo')
def get_vehicle_photo(id: int, db: Session = Depends(db_session), user: User = Depends(current_user)):
    check_vehicle_photo_access(db, id, user)
    photo = db.get(VehiclePhoto, id)
    if not photo:
        raise HTTPException(404, 'Aucune photo pour ce véhicule')
    return {'image': f'data:{photo.content_type};base64,' + base64.b64encode(photo.image_bytes).decode('ascii')}

@app.put('/api/vehicles/{id}/photo')
def set_vehicle_photo(id: int, payload: VehiclePhotoInput, db: Session = Depends(db_session), user: User = Depends(current_user)):
    if user.role == 'MECANICIEN':
        raise HTTPException(403, 'Accès refusé')
    check_vehicle_photo_access(db, id, user)
    try:
        header, encoded = payload.image.split(',', 1)
        if header not in ('data:image/jpeg;base64', 'data:image/png;base64', 'data:image/webp;base64'):
            raise ValueError('Format non pris en charge')
        if len(encoded) > 16_100_000:
            raise ValueError('Image trop volumineuse')
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 12_000_000:
            raise ValueError('Image trop volumineuse (12 Mo max avant compression)')
        img = Image.open(io.BytesIO(raw))
        img.verify()
        img = Image.open(io.BytesIO(raw))
        if img.format not in ('JPEG', 'PNG', 'WEBP'):
            raise ValueError('Format non pris en charge')
        if img.width * img.height > 35_000_000:
            raise ValueError('Dimensions trop grandes')
        img.thumbnail((1200, 900))
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        buff = io.BytesIO()
        img.save(buff, format='JPEG', quality=82, optimize=True)
        if buff.tell() > 3_000_000:
            buff = io.BytesIO()
            img.thumbnail((1000, 750))
            img.save(buff, format='JPEG', quality=65, optimize=True)
        if buff.tell() > 3_000_000:
            raise ValueError('Photo toujours trop volumineuse après compression')
    except (ValueError, binascii.Error, OSError, UnidentifiedImageError) as exc:
        raise HTTPException(422, f'Image invalide : {exc}') from exc
    photo = db.get(VehiclePhoto, id)
    if photo is None:
        photo = VehiclePhoto(vehicle_id=id, content_type='image/jpeg', image_bytes=buff.getvalue())
        db.add(photo)
    else:
        photo.image_bytes = buff.getvalue()
        photo.content_type = 'image/jpeg'
    audit(db, user, 'UPDATE_PHOTO', 'vehicles', id)
    db.commit()
    return {'updated': True}

@app.delete('/api/vehicles/{id}/photo')
def delete_vehicle_photo(id: int, db: Session = Depends(db_session), user: User = Depends(current_user)):
    if user.role == 'MECANICIEN':
        raise HTTPException(403, 'Accès refusé')
    check_vehicle_photo_access(db, id, user)
    photo = db.get(VehiclePhoto, id)
    if photo:
        db.delete(photo)
        audit(db, user, 'DELETE_PHOTO', 'vehicles', id)
        db.commit()
    return {'deleted': True}

@app.get('/api/mechanics')
def mechanics(db:Session=Depends(db_session),user:User=Depends(current_user)):
    return [{**serialize(o),'name':o.user.name} for o in db.scalars(select(Mechanic)).all()]

@app.post('/api/mechanics',status_code=201)
def create_mechanic(data:MechanicIn,db:Session=Depends(db_session),user:User=Depends(require('ADMIN'))):
    u=get_or_404(db,User,data.user_id)
    if u.role!='MECANICIEN':raise HTTPException(422,'Utilisateur non mécanicien')
    obj=Mechanic(**data.model_dump());db.add(obj);save(db,user,'CREATE',obj);return serialize(obj)

@app.put('/api/mechanics/{id}')
def update_mechanic(id:int,data:MechanicIn,db:Session=Depends(db_session),user:User=Depends(require('ADMIN'))):
    obj=get_or_404(db,Mechanic,id)
    if get_or_404(db,User,data.user_id).role!='MECANICIEN':raise HTTPException(422,'Rôle invalide')
    obj.user_id=data.user_id;obj.specialty=data.specialty;save(db,user,'UPDATE',obj);return serialize(obj)

@app.delete('/api/mechanics/{id}')
def delete_mechanic(id:int,db:Session=Depends(db_session),user:User=Depends(require('ADMIN'))):
    obj=get_or_404(db,Mechanic,id)
    if db.scalar(select(func.count()).select_from(Intervention).where(Intervention.mechanic_id==id)) or db.scalar(select(func.count()).select_from(Appointment).where(Appointment.mechanic_id==id)):
        raise HTTPException(409,'Mécanicien lié à des interventions/rendez-vous')
    audit(db,user,'DELETE','mechanics',id);db.delete(obj);db.commit();return {'deleted':True}

@app.get('/api/parts')
def parts(q:str='',db:Session=Depends(db_session),user:User=Depends(require('ADMIN','MECANICIEN'))):
    stmt=select(Part)
    if q:stmt=stmt.where(or_(Part.name.ilike(f'%{q}%'),Part.sku.ilike(f'%{q}%')))
    return [serialize(o) for o in db.scalars(stmt.order_by(Part.id.desc())).all()]

@app.post('/api/parts',status_code=201)
def create_part(data:PartIn,db:Session=Depends(db_session),user:User=Depends(require('ADMIN'))):
    obj=Part(**data.model_dump());db.add(obj);save(db,user,'CREATE',obj);return serialize(obj)

@app.put('/api/parts/{id}')
def update_part(id:int,data:PartIn,db:Session=Depends(db_session),user:User=Depends(require('ADMIN'))):
    obj=get_or_404(db,Part,id)
    for key,value in data.model_dump().items(): setattr(obj,key,value)
    save(db,user,'UPDATE',obj);return serialize(obj)

@app.delete('/api/parts/{id}')
def delete_part(id:int,db:Session=Depends(db_session),user:User=Depends(require('ADMIN'))):
    obj=get_or_404(db,Part,id)
    if db.scalar(select(func.count()).select_from(PartUsage).where(PartUsage.part_id==id)):raise HTTPException(409,'Pièce déjà utilisée')
    audit(db,user,'DELETE','parts',id);db.delete(obj);db.commit();return {'deleted':True}

def check_schedule(db:Session,mechanic_id:int | None,start:datetime,end:datetime,exclude:int | None=None):
    if end<=start:raise HTTPException(422,'La fin doit être après le début')
    if mechanic_id:
        stmt=select(Appointment).where(Appointment.mechanic_id==mechanic_id,Appointment.status=='PLANNED',Appointment.starts_at<end,Appointment.ends_at>start)
        if exclude:stmt=stmt.where(Appointment.id!=exclude)
        if db.scalar(stmt):raise HTTPException(409,'Conflit de planning mécanicien')

@app.get('/api/appointments')
def appointments(db:Session=Depends(db_session),user:User=Depends(current_user)):
    stmt=select(Appointment).join(Vehicle)
    if user.role=='CLIENT':stmt=stmt.where(Vehicle.owner_id==user.id)
    elif user.role=='MECANICIEN':
        m=db.scalar(select(Mechanic).where(Mechanic.user_id==user.id))
        stmt=stmt.where(Appointment.mechanic_id==(m.id if m else -1))
    return [serialize(o) for o in db.scalars(stmt.order_by(Appointment.starts_at.desc())).all()]

@app.post('/api/appointments',status_code=201)
def create_appointment(data:AppointmentIn,db:Session=Depends(db_session),user:User=Depends(current_user)):
    if user.role=='MECANICIEN':raise HTTPException(403,'Accès refusé')
    owned_vehicle(db,data.vehicle_id,user)
    if data.mechanic_id is None: raise HTTPException(422,'Choisissez un mécanicien pour demander un rendez-vous')
    get_or_404(db,Mechanic,data.mechanic_id)
    if data.ends_at <= data.starts_at: raise HTTPException(422,'La fin doit être après le début')
    # A new appointment awaits the assigned mechanic's acceptance.
    obj=Appointment(**data.model_dump(),status='PENDING');db.add(obj);save(db,user,'CREATE',obj);return serialize(obj)

@app.put('/api/appointments/{id}')
def update_appointment(id:int,data:AppointmentIn,db:Session=Depends(db_session),user:User=Depends(current_user)):
    if user.role=='MECANICIEN':raise HTTPException(403,'Accès refusé')
    obj=get_or_404(db,Appointment,id)
    owned_vehicle(db,obj.vehicle_id,user);owned_vehicle(db,data.vehicle_id,user)
    if obj.status!='PENDING':raise HTTPException(409,'Seuls les rendez-vous en attente sont modifiables')
    if data.mechanic_id is None: raise HTTPException(422,'Choisissez un mécanicien pour demander un rendez-vous')
    get_or_404(db,Mechanic,data.mechanic_id)
    if data.ends_at <= data.starts_at: raise HTTPException(422,'La fin doit être après le début')
    for key,value in data.model_dump().items():setattr(obj,key,value)
    save(db,user,'UPDATE',obj);return serialize(obj)

@app.delete('/api/appointments/{id}')
def delete_appointment(id:int,db:Session=Depends(db_session),user:User=Depends(current_user)):
    if user.role=='MECANICIEN':raise HTTPException(403,'Accès refusé')
    obj=get_or_404(db,Appointment,id);owned_vehicle(db,obj.vehicle_id,user)
    if obj.status not in ('PENDING','REJECTED'):raise HTTPException(409,'Rendez-vous confirmé non supprimable')
    if db.scalar(select(Intervention).where(Intervention.appointment_id==id)):raise HTTPException(409,'Rendez-vous utilisé')
    audit(db,user,'DELETE','appointments',id);db.delete(obj);db.commit();return {'deleted':True}

@app.patch('/api/appointments/{id}/accept')
def accept_appointment(id:int,db:Session=Depends(db_session),user:User=Depends(require('MECANICIEN'))):
    # Serialize decisions for the same mechanic to prevent simultaneous double-bookings.
    mechanic=db.scalar(select(Mechanic).where(Mechanic.user_id==user.id).with_for_update())
    if mechanic is None: raise HTTPException(403,'Profil mécanicien introuvable')
    obj=db.scalar(select(Appointment).where(Appointment.id==id).with_for_update())
    if obj is None: raise HTTPException(404,'Rendez-vous introuvable')
    if obj.mechanic_id!=mechanic.id: raise HTTPException(403,'Ce rendez-vous ne vous est pas affecté')
    if obj.status!='PENDING': raise HTTPException(409,'Seul un rendez-vous en attente peut être accepté')
    check_schedule(db,mechanic.id,obj.starts_at,obj.ends_at,obj.id)
    obj.status='PLANNED'
    save(db,user,'ACCEPT_APPOINTMENT',obj)
    return serialize(obj)

@app.get('/api/interventions')
def interventions(q:str='',status:str='',db:Session=Depends(db_session),user:User=Depends(current_user)):
    stmt=select(Intervention).join(Vehicle)
    if user.role=='CLIENT':stmt=stmt.where(Vehicle.owner_id==user.id)
    elif user.role=='MECANICIEN':
        m=db.scalar(select(Mechanic).where(Mechanic.user_id==user.id))
        stmt=stmt.where(Intervention.mechanic_id==(m.id if m else -1))
    if status:stmt=stmt.where(Intervention.status==status)
    if q:stmt=stmt.where(or_(Intervention.description.ilike(f'%{q}%'),Vehicle.plate.ilike(f'%{q}%')))
    return [serialize(o) for o in db.scalars(stmt.order_by(Intervention.id.desc())).all()]

@app.post('/api/interventions',status_code=201)
def create_intervention(data:InterventionIn,db:Session=Depends(db_session),user:User=Depends(require('ADMIN'))):
    get_or_404(db,Vehicle,data.vehicle_id)
    if data.mechanic_id:get_or_404(db,Mechanic,data.mechanic_id)
    if data.appointment_id:
        a=get_or_404(db,Appointment,data.appointment_id)
        if a.vehicle_id!=data.vehicle_id:raise HTTPException(422,'Véhicule différent du rendez-vous')
    obj=Intervention(**data.model_dump());db.add(obj);save(db,user,'CREATE',obj);return serialize(obj)

@app.put('/api/interventions/{id}')
def update_intervention(id:int,data:InterventionIn,db:Session=Depends(db_session),user:User=Depends(require('ADMIN'))):
    obj=get_or_404(db,Intervention,id)
    if obj.status in ('COMPLETED','CANCELLED'):raise HTTPException(409,'Intervention clôturée')
    get_or_404(db,Vehicle,data.vehicle_id)
    if data.mechanic_id:get_or_404(db,Mechanic,data.mechanic_id)
    if data.appointment_id:
        a=get_or_404(db,Appointment,data.appointment_id)
        if a.vehicle_id!=data.vehicle_id:raise HTTPException(422,'Véhicule différent du rendez-vous')
    for key,value in data.model_dump().items():setattr(obj,key,value)
    save(db,user,'UPDATE',obj);return serialize(obj)

@app.delete('/api/interventions/{id}')
def delete_intervention(id:int,db:Session=Depends(db_session),user:User=Depends(require('ADMIN'))):
    obj=get_or_404(db,Intervention,id)
    if obj.status!='REQUESTED':raise HTTPException(409,'Seules les demandes sont supprimables')
    if db.scalar(select(PartUsage).where(PartUsage.intervention_id==id)) or db.scalar(select(Invoice).where(Invoice.intervention_id==id)):
        raise HTTPException(409,'Intervention liée à des pièces/facture')
    audit(db,user,'DELETE','interventions',id);db.delete(obj);db.commit();return {'deleted':True}

TRANSITIONS={'REQUESTED':{'DIAGNOSIS','CANCELLED'},'DIAGNOSIS':{'REPAIR','CANCELLED'},'REPAIR':{'COMPLETED'},'COMPLETED':set(),'CANCELLED':set()}
@app.patch('/api/interventions/{id}/status')
def transition(id:int,data:TransitionIn,db:Session=Depends(db_session),user:User=Depends(require('ADMIN','MECANICIEN'))):
    obj=get_or_404(db,Intervention,id)
    if user.role=='MECANICIEN':can_access_intervention(db,obj,user)
    if data.status not in TRANSITIONS[obj.status]:raise HTTPException(409,'Transition non autorisée')
    if data.status=='REPAIR' and not (data.diagnosis or obj.diagnosis):raise HTTPException(422,'Diagnostic obligatoire avant réparation')
    if data.status=='COMPLETED' and not obj.diagnosis:raise HTTPException(422,'Diagnostic manquant')
    if data.diagnosis:obj.diagnosis=data.diagnosis
    obj.status=data.status
    save(db,user,'TRANSITION',obj);return serialize(obj)

@app.get('/api/interventions/{id}/parts')
def intervention_parts(id:int,db:Session=Depends(db_session),user:User=Depends(current_user)):
    obj=get_or_404(db,Intervention,id)
    if user.role!='ADMIN':can_access_intervention(db,obj,user)
    return [{**serialize(u),'part_name':u.part.name} for u in db.scalars(select(PartUsage).where(PartUsage.intervention_id==id)).all()]

@app.post('/api/interventions/{id}/parts',status_code=201)
def use_part(id:int,data:UsePartIn,db:Session=Depends(db_session),user:User=Depends(require('ADMIN','MECANICIEN'))):
    obj=get_or_404(db,Intervention,id)
    if user.role=='MECANICIEN':can_access_intervention(db,obj,user)
    if obj.status!='REPAIR':raise HTTPException(409,'Pièces consommables uniquement en réparation')
    # Database row lock on PostgreSQL; stock movement and audit in a single transaction.
    part=db.scalar(select(Part).where(Part.id==data.part_id).with_for_update())
    if not part:raise HTTPException(404,'Pièce introuvable')
    if db.scalar(select(PartUsage).where(PartUsage.intervention_id==id,PartUsage.part_id==data.part_id)):
        raise HTTPException(409,'Pièce déjà utilisée : modifier la quantité n’est pas autorisé')
    if part.stock<data.quantity:raise HTTPException(409,'Stock insuffisant')
    part.stock-=data.quantity
    usage=PartUsage(intervention_id=id,part_id=part.id,quantity=data.quantity,unit_price=part.unit_price)
    db.add(usage)
    save(db,user,'CONSUME_PART',usage)
    return serialize(usage)

@app.post('/api/interventions/{id}/parts/bulk', status_code=201)
def use_parts_bulk(id:int, data:UsePartsIn, db:Session=Depends(db_session), user:User=Depends(require('ADMIN','MECANICIEN'))):
    """Consume multiple distinct parts atomically; reject the entire request on any error."""
    intervention=get_or_404(db, Intervention, id)
    if user.role=='MECANICIEN':can_access_intervention(db, intervention, user)
    if intervention.status!='REPAIR':
        raise HTTPException(409, 'Pièces consommables uniquement en réparation')
    ids=[item.part_id for item in data.items]
    if len(ids)!=len(set(ids)):
        raise HTTPException(422, 'Choisissez chaque pièce une seule fois')
    # Sorted locking prevents deadlocks for simultaneous orders using the same parts.
    selected=db.scalars(select(Part).where(Part.id.in_(ids)).order_by(Part.id).with_for_update()).all()
    by_id={part.id:part for part in selected}
    if len(by_id)!=len(ids):raise HTTPException(404, 'Une ou plusieurs pièces sont introuvables')
    already_used=set(db.scalars(select(PartUsage.part_id).where(PartUsage.intervention_id==id, PartUsage.part_id.in_(ids))).all())
    if already_used:raise HTTPException(409, 'Une des pièces a déjà été utilisée dans cette intervention')
    for item in data.items:
        part=by_id[item.part_id]
        if part.stock<item.quantity:
            raise HTTPException(409, f'Stock insuffisant pour {part.name} (disponible : {part.stock})')
    usages=[]
    for item in data.items:
        part=by_id[item.part_id]
        part.stock-=item.quantity
        usage=PartUsage(intervention_id=id, part_id=part.id, quantity=item.quantity, unit_price=part.unit_price)
        db.add(usage)
        usages.append(usage)
    try:
        db.flush()
        for usage in usages:audit(db,user,'CONSUME_PART',usage.__tablename__,usage.id)
        db.commit()
        return [serialize(usage) for usage in usages]
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'Conflit : une pièce a déjà été enregistrée')

@app.get('/api/interventions/{id}/report')
def get_work_report(id:int,db:Session=Depends(db_session),user:User=Depends(current_user)):
    obj=get_or_404(db,Intervention,id)
    if user.role!='ADMIN':can_access_intervention(db,obj,user)
    report=db.scalar(select(WorkReport).where(WorkReport.intervention_id==id))
    if report is None:raise HTTPException(404,'Compte rendu non encore saisi')
    return serialize(report)

@app.put('/api/interventions/{id}/report')
def upsert_work_report(id:int,data:WorkReportIn,db:Session=Depends(db_session),user:User=Depends(require('MECANICIEN'))):
    obj=get_or_404(db,Intervention,id)
    can_access_intervention(db,obj,user)
    if obj.status not in ('DIAGNOSIS','REPAIR','COMPLETED'):
        raise HTTPException(409,'Le compte rendu nécessite un diagnostic démarré')
    mechanic=db.scalar(select(Mechanic).where(Mechanic.user_id==user.id))
    report=db.scalar(select(WorkReport).where(WorkReport.intervention_id==id))
    if report is None:
        report=WorkReport(intervention_id=id,mechanic_id=mechanic.id,work_done=data.work_done,observations=data.observations)
        db.add(report)
    else:
        report.work_done=data.work_done
        report.observations=data.observations
        report.updated_at=datetime.now(timezone.utc)
    save(db,user,'WORK_REPORT',report)
    return serialize(report)

@app.get('/api/invoices')
def invoices(db:Session=Depends(db_session),user:User=Depends(current_user)):
    stmt=select(Invoice).join(Intervention).join(Vehicle)
    if user.role=='CLIENT':stmt=stmt.where(Vehicle.owner_id==user.id)
    elif user.role=='MECANICIEN':
        m=db.scalar(select(Mechanic).where(Mechanic.user_id==user.id))
        stmt=stmt.where(Intervention.mechanic_id==(m.id if m else -1))
    return [serialize(o) for o in db.scalars(stmt.order_by(Invoice.id.desc())).all()]

@app.post('/api/invoices/{intervention_id}',status_code=201)
def create_invoice(intervention_id:int,db:Session=Depends(db_session),user:User=Depends(require('ADMIN'))):
    obj=get_or_404(db,Intervention,intervention_id)
    if obj.status!='COMPLETED':raise HTTPException(409,'Réparation non terminée')
    if db.scalar(select(Invoice).where(Invoice.intervention_id==intervention_id)):raise HTTPException(409,'Facture déjà créée')
    total=Decimal(obj.labor_cost)+sum((u.unit_price*u.quantity for u in db.scalars(select(PartUsage).where(PartUsage.intervention_id==intervention_id))),Decimal(0))
    inv=Invoice(intervention_id=intervention_id,amount=total)
    db.add(inv);save(db,user,'CREATE',inv);return serialize(inv)

@app.patch('/api/invoices/{id}')
def update_invoice(id:int,data:InvoiceIn,db:Session=Depends(db_session),user:User=Depends(require('ADMIN'))):
    obj=get_or_404(db,Invoice,id)
    if obj.status!='UNPAID' or data.status!='PAID':raise HTTPException(409,'Transition facture non autorisée')
    obj.status='PAID';save(db,user,'MARK_PAID',obj);return serialize(obj)

@app.get('/api/dashboard')
def dashboard(db:Session=Depends(db_session),user:User=Depends(current_user)):
    if user.role=='CLIENT':
        owner_ids=select(Vehicle.id).where(Vehicle.owner_id==user.id)
        return {'vehicles':db.scalar(select(func.count()).select_from(Vehicle).where(Vehicle.owner_id==user.id)),
                'interventions':db.scalar(select(func.count()).select_from(Intervention).where(Intervention.vehicle_id.in_(owner_ids))),
                'completed':db.scalar(select(func.count()).select_from(Intervention).where(Intervention.vehicle_id.in_(owner_ids),Intervention.status=='COMPLETED'))}
    stmt=select(Intervention)
    if user.role=='MECANICIEN':
        m=db.scalar(select(Mechanic).where(Mechanic.user_id==user.id))
        stmt=stmt.where(Intervention.mechanic_id==(m.id if m else -1))
    ints=db.scalars(stmt).all()
    result={'interventions':len(ints),'requested':sum(i.status=='REQUESTED' for i in ints),'in_repair':sum(i.status=='REPAIR' for i in ints),'completed':sum(i.status=='COMPLETED' for i in ints),
            'by_status':{s:sum(i.status==s for i in ints) for s in TRANSITIONS}}
    if user.role=='ADMIN':
        result.update({'vehicles':db.scalar(select(func.count()).select_from(Vehicle)),'clients':db.scalar(select(func.count()).select_from(User).where(User.role=='CLIENT')),
                       'parts_low_stock':db.scalar(select(func.count()).select_from(Part).where(Part.stock>0, Part.stock<=5)),
                       'parts_out_of_stock':db.scalar(select(func.count()).select_from(Part).where(Part.stock==0)),
                       'stock_alerts':[{'id':p.id,'sku':p.sku,'name':p.name,'stock':p.stock,'level':'RUPTURE' if p.stock==0 else 'FAIBLE'} for p in db.scalars(select(Part).where(Part.stock<=5).order_by(Part.stock.asc(),Part.name.asc())).all()],
                       'revenue':str(db.scalar(select(func.coalesce(func.sum(Invoice.amount),0)).where(Invoice.status=='PAID')) or 0)})
    return result

@app.get('/api/audit')
def audit_logs(limit:int=Query(100,ge=1,le=500),db:Session=Depends(db_session),user:User=Depends(require('ADMIN'))):
    return [serialize(o) for o in db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)).all()]
