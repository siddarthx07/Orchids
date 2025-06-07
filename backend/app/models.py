"""
Data models for the website cloning API
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, HttpUrl, Field


class CloneRequestModel(BaseModel):
    """Request model for website cloning"""
    url: str = Field(..., description="URL of website to clone")
    options: Optional[Dict[str, Any]] = Field(
        default={},
        description="Optional configuration parameters for cloning"
    )


class CloneResponseModel(BaseModel):
    """Response model for website cloning"""
    request_id: str = Field(..., description="Unique ID for this cloning request")
    status: str = Field(..., description="Status of the cloning request")
    url: str = Field(..., description="Original URL that was cloned")


class CloneResultModel(BaseModel):
    """Model for the result of a cloning operation"""
    request_id: str = Field(..., description="Unique ID for this cloning request")
    status: str = Field(..., description="Status of the cloning process")
    url: str = Field(..., description="Original URL that was cloned")
    cloned_html: Optional[str] = Field(None, description="The cloned HTML content")
    error: Optional[str] = Field(None, description="Error message if cloning failed")
    metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="Metadata about the cloning process"
    )
