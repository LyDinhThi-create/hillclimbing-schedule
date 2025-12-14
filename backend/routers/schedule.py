from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from typing import List
import pandas as pd
from io import BytesIO
from backend.models.schema import StudentData, ScheduleConfig, ScheduleResult, UploadResponse, ScheduleResponse
from backend.services.scheduler import parse_excel, HillClimbingScheduler

router = APIRouter(prefix="/api", tags=["schedule"])

# In-memory storage for demo purposes
# In a real app, use a database or Redis
uploaded_students: List[StudentData] = []

@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls', '.json')):
        raise HTTPException(status_code=400, detail="Invalid file format")
    
    content = await file.read()
    
    global uploaded_students
    
    if file.filename.endswith('.json'):
        from backend.services.scheduler import parse_json
        uploaded_students = parse_json(content)
    else:
        uploaded_students = parse_excel(content)
    
    subjects = set()
    for s in uploaded_students:
        subjects.update(s.subjects.keys())
        
    return UploadResponse(
        filename=file.filename,
        total_students=len(uploaded_students),
        subjects=list(subjects)
    )

@router.post("/schedule", response_model=ScheduleResponse)
async def create_schedule(config: ScheduleConfig):
    global uploaded_students
    if not uploaded_students:
        raise HTTPException(status_code=400, detail="No student data uploaded")
        
    scheduler = HillClimbingScheduler(config, uploaded_students)
    try:
        results, warnings = scheduler.schedule()
        return ScheduleResponse(results=results, warnings=warnings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/excel")
async def export_excel():
    # Placeholder for export logic
    # In a real app, this would generate a file and return FileResponse
    return {"message": "Export to Excel not implemented in this demo"}

@router.get("/export/pdf")
async def export_pdf():
    # Placeholder for export logic
    return {"message": "Export to PDF not implemented in this demo"}
