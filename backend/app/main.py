from fastapi import FastAPI
from app.routes import upload, analyze, report

app = FastAPI()

app.include_router(upload.router, prefix="/upload")
app.include_router(analyze.router, prefix="/analyze")
app.include_router(report.router, prefix="/report")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Intelli-Credit API Running"}