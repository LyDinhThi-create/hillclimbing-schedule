from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from backend.routers import schedule
import os

app = FastAPI(title="Exam Scheduling System")

# Mount static files
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# Templates
templates = Jinja2Templates(directory="backend/templates")

# Include routers
app.include_router(schedule.router)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
