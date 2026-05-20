from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
import datetime
from backend.core.database import Base

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    prompt = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    versions = relationship("DesignVersion", back_populates="project")

class DesignVersion(Base):
    __tablename__ = "design_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    version_num = Column(Integer)
    pcb_data = Column(JSON) # Stores placements/traces
    zip_path = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    project = relationship("Project", back_populates="versions")
