from typing import Dict, Optional

from pydantic import BaseModel, Field


class ServiceStatus(BaseModel):
    """
    Individual server status
    """
    status: str = Field(...,description="The status of the service", examples=["healthy"])
    message: Optional[str] = Field(None,description="The message of the service", examples=["All systems are operational"])

class HealthResponse(BaseModel):
    """
    Overall health status
    """
    status: str = Field(...,description="Overall status", examples=["healthy"])
    version: str = Field(...,description="The version of the service", examples=["1.0.0"])
    environment: str = Field(...,description="The environment of the service", examples=["development"])
    service_name: str = Field(...,description="The name of the service", examples=["database"])
    services: Optional[Dict[str, ServiceStatus]] = Field(None,description="Individual service statuses")
