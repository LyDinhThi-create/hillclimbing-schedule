from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
from datetime import date, time, datetime

class ScheduleConfig(BaseModel):
    start_date: date
    end_date: date
    off_days: List[int] = Field(default=[5, 6], description="0=Monday, 6=Sunday")
    shifts: List[str] = Field(default=["Morning", "Afternoon"])
    shift_times: Dict[str, Dict[str, str]] = Field(
        default={
            "Morning": {"start": "07:30", "end": "11:30"},
            "Afternoon": {"start": "13:30", "end": "17:30"}
        }
    )
    break_time: int = Field(default=30, description="Minutes between exams")
    rooms: List[Dict[str, str]] = Field(default=[], description="List of rooms with name")
    min_students_per_room: Optional[int] = None
    max_students_per_room: Optional[int] = None

    @validator('end_date')
    def end_date_must_be_after_start_date(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v

class StudentData(BaseModel):
    student_id: str
    name: str
    subjects: Dict[str, int]  # subject_name: duration

class ScheduleResult(BaseModel):
    student_id: str
    student_name: str
    subject: str
    exam_date: date
    shift: str
    start_time: str
    end_time: str
    room: str

class UploadResponse(BaseModel):
    filename: str
    total_students: int
    subjects: List[str]

class ScheduleResponse(BaseModel):
    results: List[ScheduleResult]
    warnings: List[str]
