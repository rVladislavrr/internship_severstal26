from datetime import datetime

from pydantic import BaseModel, Field

class Subjects(BaseModel):
    length: float = Field(..., gt=0)
    weight: float = Field(..., gt=0)

class CreateSubjects(Subjects):
    pass

class ReadSubjects(Subjects):
    id: int = Field(..., ge=0)
    is_active: bool
    create_at: datetime
    delete_at: datetime | None = None

class UpdateSubjects(Subjects):
    pass