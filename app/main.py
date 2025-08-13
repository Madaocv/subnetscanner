# app/main.py
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
import datetime
import logging

# Налаштування логування
import os

# Create logs directory if it doesn't exist
os.makedirs('/app/logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from . import models, schemas, crud
from .database import engine, SessionLocal, get_db
from .run_scan import run_scan
# Create database tables
# ONE-TIME: Recreate tables to apply unique constraint
# models.Base.metadata.drop_all(bind=engine)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Site and Device Management API")

@app.on_event("startup")
async def startup_event():
    """Create database tables on startup"""
    # Only create tables if they don't exist (preserves data)
    # models.Base.metadata.drop_all(bind=engine)  # DISABLED: Don't delete data
    models.Base.metadata.create_all(bind=engine)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sites endpoints
@app.post("/sites/", response_model=schemas.Site, status_code=status.HTTP_201_CREATED)
def create_site(site: schemas.SiteCreate, db: Session = Depends(get_db)):
    return crud.create_site(db=db, site=site)

@app.get("/sites/", response_model=List[schemas.Site])
def read_sites(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve a list of sites with pagination support.

    Args:
        skip (int): Number of records to skip for pagination.
        limit (int): Maximum number of records to return.
        db (Session): Database session dependency.

    Returns:
        List[schemas.Site]: List of site objects.
    """
    # Fetch sites from the database with the specified skip and limit
    sites = crud.get_sites(db, skip=skip, limit=limit)
    return sites

def orm_to_dict(orm_model):
    """Конвертує ORM модель у словник, видаляючи службові атрибути SQLAlchemy"""
    result = {}
    for key, value in orm_model.__dict__.items():
        if not key.startswith('_'):
            result[key] = value
    return result

@app.get("/sites/{site_id}", response_model=schemas.Site)
def read_site(site_id: int, db: Session = Depends(get_db)):
    db_site = crud.get_site(db, site_id=site_id)
    if db_site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Get the latest execution for this site
    latest_execution = crud.get_latest_site_execution(db, site_id=site_id)
    
    # Create Pydantic model from ORM object using from_orm method
    response_data = schemas.Site.model_validate(db_site, from_attributes=True)
    
    # Add the latest execution to the response data
    if latest_execution:
        response_data.latest_execution = schemas.Execution.model_validate(
            latest_execution, from_attributes=True
        )
    
    return response_data

@app.put("/sites/{site_id}", response_model=schemas.Site)
def update_site(site_id: int, site: schemas.SiteUpdate, db: Session = Depends(get_db)):
    db_site = crud.update_site(db, site_id=site_id, site=site)
    if db_site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return db_site

@app.delete("/sites/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(site_id: int, db: Session = Depends(get_db)):
    success = crud.delete_site(db, site_id=site_id)
    if not success:
        raise HTTPException(status_code=404, detail="Site not found")
    return None

# Device models endpoints
@app.post("/devices/", response_model=schemas.Device, status_code=status.HTTP_201_CREATED)
def create_device(device: schemas.DeviceCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_device(db=db, device=device)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, 
            detail=f"Device with name '{device.name}' already exists"
        )

@app.get("/devices/", response_model=List[schemas.Device])
def read_devices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    devices = crud.get_devices(db, skip=skip, limit=limit)
    return devices

@app.get("/devices/{device_id}", response_model=schemas.Device)
def read_device(device_id: int, db: Session = Depends(get_db)):
    db_device = crud.get_device(db, device_id=device_id)
    if db_device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return db_device

@app.put("/devices/{device_id}", response_model=schemas.Device)
def update_device(device_id: int, device: schemas.DeviceUpdate, db: Session = Depends(get_db)):
    try:
        db_device = crud.update_device(db, device_id=device_id, device=device)
        if db_device is None:
            raise HTTPException(status_code=404, detail="Device not found")
        return db_device
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, 
            detail=f"Device with name '{device.name}' already exists"
        )

@app.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(device_id: int, db: Session = Depends(get_db)):
    success = crud.delete_device(db, device_id=device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    return None

# Start execution endpoint
@app.post("/sites/{site_id}/execute", response_model=schemas.Execution)
def start_execution(site_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Check if site exists
    db_site = crud.get_site(db, site_id=site_id)
    if db_site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Create execution record with "running" status
    execution = crud.create_execution(db, site_id=site_id)
    
    # Start the background task for scanning - pass site_id instead of site object
    background_tasks.add_task(run_scan, site_id, execution.id, logger)
    
    return execution

@app.get("/executions/", response_model=List[schemas.Execution])
def read_executions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    executions = crud.get_executions(db, skip=skip, limit=limit)
    return executions

@app.get("/executions/{execution_id}", response_model=schemas.Execution)
def read_execution(execution_id: int, db: Session = Depends(get_db)):
    db_execution = crud.get_execution(db, execution_id=execution_id)
    if db_execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return db_execution

@app.get("/sites/{site_id}/executions", response_model=List[schemas.Execution])
def read_site_executions(site_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # Check if site exists
    db_site = crud.get_site(db, site_id=site_id)
    if db_site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    
    executions = crud.get_site_executions(db, site_id=site_id, skip=skip, limit=limit)
    return executions

@app.post("/sites/{site_id}/subsections", response_model=schemas.Subsection)
def create_subsection_for_site(
    site_id: int,
    subsection: schemas.SubsectionCreate,
    db: Session = Depends(get_db)
):
    # Перевіряємо, чи існує сайт
    db_site = crud.get_site(db, site_id=site_id)
    if db_site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Створюємо підрозділ
    return crud.create_subsection(db=db, subsection=subsection, site_id=site_id)