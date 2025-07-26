from sqlalchemy.orm import Session
from . import models, schemas
from typing import List, Optional

# Device CRUD
def get_device(db: Session, device_id: int):
    return db.query(models.Device).filter(models.Device.id == device_id).first()

def get_device_by_name(db: Session, name: str):
    return db.query(models.Device).filter(models.Device.name == name).first()

def get_devices(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Device).offset(skip).limit(limit).all()

def create_device(db: Session, device: schemas.DeviceCreate):
    db_device = models.Device(**device.model_dump())
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

def update_device(db: Session, device_id: int, device: schemas.DeviceCreate):
    db_device = get_device(db, device_id)
    if not db_device:
        return None
    
    for key, value in device.model_dump().items():
        setattr(db_device, key, value)
    
    db.commit()
    db.refresh(db_device)
    return db_device

def delete_device(db: Session, device_id: int):
    db_device = get_device(db, device_id)
    if db_device:
        db.delete(db_device)
        db.commit()
        return True
    return False

# Site CRUD
def get_site(db: Session, site_id: int):
    return db.query(models.Site).filter(models.Site.id == site_id).first()

def get_sites(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Site).offset(skip).limit(limit).all()

def create_site(db: Session, site: schemas.SiteCreate):
    site_data = site.model_dump(exclude={"subsections"})
    db_site = models.Site(**site_data)
    db.add(db_site)
    db.commit()
    db.refresh(db_site)
    
    # Create subsections if provided
    if site.subsections:
        for subsection_data in site.subsections:
            create_subsection(db, subsection_data, db_site.id)
    
    return db_site

def update_site(db: Session, site_id: int, site: schemas.SiteUpdate):
    db_site = get_site(db, site_id)
    if not db_site:
        return None
    
    update_data = site.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_site, key, value)
    
    db.commit()
    db.refresh(db_site)
    return db_site

def delete_site(db: Session, site_id: int):
    db_site = get_site(db, site_id)
    if db_site:
        db.delete(db_site)
        db.commit()
        return True
    return False

# Subsection CRUD
def get_subsection(db: Session, subsection_id: int):
    return db.query(models.Subsection).filter(models.Subsection.id == subsection_id).first()

def get_subsections_by_site(db: Session, site_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Subsection).filter(models.Subsection.site_id == site_id).offset(skip).limit(limit).all()

def create_subsection(db: Session, subsection: schemas.SubsectionCreate, site_id: int):
    # Extract miners to create them separately
    miners_data = subsection.miners
    
    # Create subsection without miners
    subsection_data = subsection.model_dump(exclude={"miners"})
    db_subsection = models.Subsection(**subsection_data, site_id=site_id)
    db.add(db_subsection)
    db.commit()
    db.refresh(db_subsection)
    
    # Create miners for this subsection
    for miner in miners_data:
        db_miner = models.SubsectionMiner(
            model=miner.model,
            quantity=miner.quantity,
            subsection_id=db_subsection.id
        )
        db.add(db_miner)
    
    db.commit()
    db.refresh(db_subsection)
    return db_subsection

def update_subsection(db: Session, subsection_id: int, subsection: schemas.SubsectionUpdate):
    db_subsection = get_subsection(db, subsection_id)
    if not db_subsection:
        return None
    
    # Update basic fields
    update_data = subsection.model_dump(exclude={"miners"}, exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_subsection, key, value)
    
    # Update miners if provided
    if subsection.miners is not None:
        # Delete existing miners
        db.query(models.SubsectionMiner).filter(
            models.SubsectionMiner.subsection_id == subsection_id
        ).delete()
        
        # Create new miners
        for miner in subsection.miners:
            db_miner = models.SubsectionMiner(
                model=miner.model,
                quantity=miner.quantity,
                subsection_id=subsection_id
            )
            db.add(db_miner)
    
    db.commit()
    db.refresh(db_subsection)
    return db_subsection

def delete_subsection(db: Session, subsection_id: int):
    db_subsection = get_subsection(db, subsection_id)
    if db_subsection:
        db.delete(db_subsection)
        db.commit()
        return True
    return False

# Helper function to generate run configuration
def generate_run_config(db: Session, site_id: int):
    site = get_site(db, site_id)
    if not site:
        return None
    
    # Get all devices to create models dictionary
    devices = get_devices(db)
    models_dict = {
        device.name: {
            "hashrate": device.hashrate,
            "HB": device.HB,
            "fans": device.fans
        } for device in devices
    }
    
    # Format subsections
    subsections_list = []
    for subsection in site.subsections:
        miners_list = [
            {"model": miner.model, "quantity": miner.quantity}
            for miner in subsection.miners
        ]
        
        subsections_list.append({
            "name": subsection.name,
            "ip_ranges": subsection.ip_ranges,
            "miners": miners_list
        })
    
    # Create run configuration
    run_config = {
        "username": site.username,
        "password": site.password,
        "timeout": site.timeout,
        "site_id": site.name,
        "subsections": subsections_list,
        "models": models_dict
    }
    
    return run_config
# db_device = models.Device(**device.model_dump())