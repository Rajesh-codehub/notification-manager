from datetime import datetime
from typing import List, Literal
import csv
import io

from fastapi.responses import StreamingResponse

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    select,
    Boolean,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from fastapi import FastAPI, Depends, HTTPException


from sqlalchemy.orm import Session
from typing import Optional


# ============================================================
# Database setup
# ============================================================

import os

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================
# Database models
# ============================================================
class NotificationDB(Base):
    __tablename__ = "notifications"

    db_id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(255), nullable=False, index=True) # <-- ADD THIS
    notification_id = Column(Integer, nullable=False, index=True)
    package_name = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    sub_text = Column(Text, nullable=False, default="")
    post_time = Column(BigInteger, nullable=False, index=True)
    tag = Column(String(255), nullable=False, default="")


from pydantic import BaseModel
from typing import Optional

class DeviceRegisterSchema(BaseModel):
    device_id: str
    device_name: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None

class Device(Base):
    __tablename__ = "devices"

    device_id = Column(String, primary_key=True, index=True)
    device_name = Column(String, nullable=True)
    model = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    status = Column(String, default="active")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)



# Create all tables automatically
Base.metadata.create_all(bind=engine)


# ============================================================
# FastAPI application
# ============================================================

app = FastAPI(
    title="Notification and Device Access Manager",
    version="1.0.0",
)




# ============================================================
# Notification schemas
# ============================================================

class NotificationCreate(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=255)
    packageName: str = Field(..., max_length=255)
    title: str = Field(..., max_length=255)
    text: str
    subText: str = ""
    postTime: int
    id: int
    tag: str = ""


class NotificationResponse(NotificationCreate):
    dbId: int


# ============================================================
# Device schemas
# ============================================================

class RegisterDeviceRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=255)


class UpdateStatusRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=255)
    status: Literal["active", "inactive"]


# ============================================================
# Helper functions
# ============================================================

def notification_to_response(notification: NotificationDB) -> dict:
    return {
        "dbId": notification.db_id,
        "device_id": notification.device_id,
        "packageName": notification.package_name,
        "title": notification.title,
        "text": notification.text,
        "subText": notification.sub_text,
        "postTime": notification.post_time,
        "id": notification.notification_id,
        "tag": notification.tag,
    }

# ============================================================
# Notification APIs
# ============================================================

@app.post(
    "/notifications",
    response_model=NotificationResponse,
    status_code=201,
)
def create_notification(
    payload: NotificationCreate,
    db: Session = Depends(get_db),
):
    new_notification = NotificationDB(
    device_id=payload.device_id,
    notification_id=payload.id,
    package_name=payload.packageName,
    title=payload.title,
    text=payload.text,
    sub_text=payload.subText,
    post_time=payload.postTime,
    tag=payload.tag,
)

    db.add(new_notification)
    db.commit()
    db.refresh(new_notification)

    return notification_to_response(new_notification)




# Updated GET to accept device_id query param
@app.get("/notifications", response_model=List[NotificationResponse])
def get_notifications(
    device_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = select(NotificationDB).order_by(NotificationDB.post_time.desc())
    if device_id:
        query = query.where(NotificationDB.device_id == device_id)

    notifications = db.scalars(query).all()
    return [notification_to_response(n) for n in notifications]


@app.get("/notifications/export")
def export_notifications_csv(
    device_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(NotificationDB)

    if device_id:
        query = query.filter(
            NotificationDB.device_id == device_id
        )

    notifications = (
        query
        .order_by(NotificationDB.post_time.desc())
        .all()
    )

    output = io.StringIO()

    writer = csv.writer(output)

    # CSV Header
    writer.writerow([
        "db_id",
        "device_id",
        "notification_id",
        "package_name",
        "title",
        "text",
        "sub_text",
        "post_time",
        "tag",
    ])

    # CSV Data
    for notification in notifications:

        writer.writerow([
            notification.db_id,
            notification.device_id,
            notification.notification_id,
            notification.package_name,
            notification.title,
            notification.text,
            notification.sub_text,
            notification.post_time,
            notification.tag,
        ])

    output.seek(0)

    if device_id:
        filename = f"notifications_{device_id}.csv"
    else:
        filename = "notifications_all.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        },
    )


@app.get(
    "/notifications/{db_id}",
    response_model=NotificationResponse,
)
def get_notification(
    db_id: int,
    db: Session = Depends(get_db),
):
    notification = db.get(NotificationDB, db_id)

    if notification is None:
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    return notification_to_response(notification)




@app.post("/api/register", status_code=201)
def register_device(payload: DeviceRegisterSchema, db: Session = Depends(get_db)):
    db_device = db.query(Device).filter(Device.device_id == payload.device_id).first()
    
    if not db_device:
        new_device = Device(
            device_id=payload.device_id,
            device_name=payload.device_name,
            model=payload.model,
            manufacturer=payload.manufacturer,
            status="active",
            is_active=True
        )
        db.add(new_device)
        db.commit()
        db.refresh(new_device)
        return {"message": "Device registered successfully", "device": new_device}
    
    # Optional: Update device_name if it already exists
    db_device.device_name = payload.device_name
    db.commit()
    return {"message": "Device already registered", "device": db_device}


@app.put("/api/update-status")
def update_device_status(
    payload: UpdateStatusRequest,
    db: Session = Depends(get_db),
):
    db_device = (
        db.query(Device)
        .filter(Device.device_id == payload.device_id)
        .first()
    )

    if not db_device:
        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    db_device.status = payload.status

    db.commit()
    db.refresh(db_device)

    return {
        "message": "Status updated successfully",
        "device_id": db_device.device_id,
        "status": db_device.status,
    }


@app.get("/api/devices")
def get_all_devices(
    db: Session = Depends(get_db),
):
    devices = (
        db.query(Device)
        .order_by(Device.created_at.desc())
        .all()
    )

    return {
        "count": len(devices),
        "devices": [
            {
                "device_id": device.device_id,
                "device_name": device.device_name,
                "model": device.model,
                "manufacturer": device.manufacturer,
                "status": device.status,
                "is_active": device.is_active if device.is_active is not None else (device.status == "active"),
                "created_at": device.created_at,
            }
            for device in devices
        ],
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}



# Updated DELETE to clear per device or all
@app.delete("/notifications")
def delete_notifications(
    device_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(NotificationDB)
    if device_id:
        query = query.filter(NotificationDB.device_id == device_id)
    
    deleted_count = query.delete(synchronize_session=False)
    db.commit()

    return {"message": "Notifications deleted", "deleted_count": deleted_count}


@app.get("/api/validate/{device_id}")
def validate_device(
    device_id: str,
    db: Session = Depends(get_db),
):
    db_device = (
        db.query(Device)
        .filter(Device.device_id == device_id)
        .first()
    )

    if not db_device:
        raise HTTPException(
            status_code=404,
            detail="Device not registered",
        )

    return {
        "device_id": db_device.device_id,
        "is_active": db_device.status == "active",
        "status": db_device.status,
        "created_at": db_device.created_at,
    }


