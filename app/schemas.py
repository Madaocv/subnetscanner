from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

class Execution(BaseModel):
    """Схема для відповіді на запит виконання сканування."""
    success: bool = Field(..., description="Чи успішно запущено сканування")
    message: str = Field(..., description="Повідомлення про результат")
    task_id: Optional[str] = Field(None, description="Ідентифікатор завдання (якщо запущено асинхронно)")
    details: Optional[Dict[str, Any]] = Field(None, description="Додаткові деталі виконання")

    class Config:
        from_attributes = True

# Device schemas
class DeviceCreate(BaseModel):
    name: str = Field(..., description="Device model name")
    hashrate: int = Field(..., description="Hashrate of the device")
    HB: int = Field(..., description="Number of hash boards")
    fans: int = Field(..., description="Number of fans")

class DeviceUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Device model name")
    hashrate: Optional[int] = Field(None, description="Hashrate of the device")
    HB: Optional[int] = Field(None, description="Number of hash boards")
    fans: Optional[int] = Field(None, description="Number of fans")

class Device(BaseModel):
    id: int = Field(..., description="Unique identifier")
    name: str = Field(..., description="Device model name")
    hashrate: int = Field(..., description="Hashrate of the device")
    HB: int = Field(..., description="Number of hash boards")
    fans: int = Field(..., description="Number of fans")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True

# Miner schemas
class MinerCreate(BaseModel):
    model: str = Field(..., description="Device model name")
    quantity: int = Field(..., description="Number of devices")

class MinerUpdate(BaseModel):
    model: Optional[str] = Field(None, description="Device model name")
    quantity: Optional[int] = Field(None, description="Number of devices")

class Miner(BaseModel):
    id: int = Field(..., description="Unique identifier")
    model: str = Field(..., description="Device model name")
    quantity: int = Field(..., description="Number of devices")
    subsection_id: int = Field(..., description="ID of the parent subsection")

    class Config:
        from_attributes = True

# Subsection schemas
class SubsectionCreate(BaseModel):
    name: str = Field(..., description="Subsection name")
    ip_ranges: List[str] = Field(..., description="List of IP CIDR ranges")
    miners: List[MinerCreate] = Field(..., description="List of miners in this subsection")

class SubsectionUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Subsection name")
    ip_ranges: Optional[List[str]] = Field(None, description="List of IP CIDR ranges")
    miners: Optional[List[MinerCreate]] = Field(None, description="List of miners in this subsection")

class Subsection(BaseModel):
    id: int = Field(..., description="Unique identifier")
    name: str = Field(..., description="Subsection name")
    ip_ranges: List[str] = Field(..., description="List of IP CIDR ranges")
    site_id: int = Field(..., description="ID of the parent site")
    miners: List[Miner] = Field(..., description="List of miners in this subsection")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True

# Site schemas
class SiteCreate(BaseModel):
    name: str = Field(..., description="Site name")
    username: str = Field(..., description="Username for site access")
    password: str = Field(..., description="Password for site access")
    timeout: int = Field(20, description="Connection timeout in seconds")
    subsections: List[SubsectionCreate] = Field([], description="List of subsections in this site")

class SiteUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Site name")
    username: Optional[str] = Field(None, description="Username for site access")
    password: Optional[str] = Field(None, description="Password for site access")
    timeout: Optional[int] = Field(None, description="Connection timeout in seconds")

class Site(BaseModel):
    id: int = Field(..., description="Unique identifier")
    name: str = Field(..., description="Site name")
    username: str = Field(..., description="Username for site access")
    password: str = Field(..., description="Password for site access")
    timeout: int = Field(..., description="Connection timeout in seconds")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    subsections: List[Subsection] = Field(..., description="List of subsections in this site")
    latest_execution: Optional[Execution] = None
    
    class Config:
        from_attributes = True

# Schema for run configuration
class DeviceConfig(BaseModel):
    hashrate: int = Field(..., description="Hashrate of the device")
    HB: int = Field(..., description="Number of hash boards")
    fans: int = Field(..., description="Number of fans")

class RunConfig(BaseModel):
    username: str = Field(..., description="Username for site access")
    password: str = Field(..., description="Password for site access")
    timeout: int = Field(..., description="Connection timeout in seconds")
    site_id: str = Field(..., description="Site identifier")
    subsections: List[Dict[str, Any]] = Field(..., description="List of subsections with their configuration")
    models: Dict[str, DeviceConfig] = Field(..., description="Dictionary of device models and their specifications")
