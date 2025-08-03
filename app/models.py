from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False, unique=True)
    hashrate = Column(Integer, nullable=False)
    HB = Column(Integer, nullable=False)
    fans = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), 
                        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))

class Site(Base):
    __tablename__ = "sites"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    timeout = Column(Integer, default=20)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc),
                        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    subsections = relationship("Subsection", back_populates="site", cascade="all, delete-orphan")
    executions = relationship("Execution", back_populates="site", cascade="all, delete-orphan")
class Subsection(Base):
    __tablename__ = "subsections"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"))
    ip_ranges = Column(JSON, nullable=False, default=list)  # Зберігаємо як JSON масив
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc),
                        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    site = relationship("Site", back_populates="subsections")
    miners = relationship("SubsectionMiner", back_populates="subsection", cascade="all, delete-orphan")

class SubsectionMiner(Base):
    __tablename__ = "subsection_miners"
    
    id = Column(Integer, primary_key=True, index=True)
    model = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    subsection_id = Column(Integer, ForeignKey("subsections.id"))
    
    subsection = relationship("Subsection", back_populates="miners")

class Execution(Base):
    """Модель для збереження інформації про виконання сканування сайту."""
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"))
    status = Column(String, default="pending")
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Відношення
    site = relationship("Site", back_populates="executions")