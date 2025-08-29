# main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uuid
import os
from datetime import datetime, timedelta
from typing import Optional
import mimetypes
import io

# Import MongoDB database functions
from database.mongodb_client import (
    get_db, upload_file_to_mongodb, download_file_from_mongodb,
    create_file_record, get_file_by_code, increment_download_count,
    generate_download_code, validate_file_size, FileRecord,
    format_file_size
)

app = FastAPI(title="File Share Platform", version="1.0.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuration
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Root endpoint
@app.get("/")
async def read_root():
    return {"message": "File Share Platform API", "docs": "/docs"}

# Serve the HTML file
@app.get("/app")
async def serve_app():
    with open("static/index.html", "r") as f:
        html_content = f.read()
    return Response(content=html_content, media_type="text/html")

# API Routes
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), db = Depends(get_db)):
    """Upload file and return download code"""
    
    try:
        # Validate file size
        if not validate_file_size(file.size):
            return JSONResponse(
                status_code=413,
                content={
                    "success": False,
                    "detail": "File size exceeds 100MB limit",
                    "message": "File too large"
                }
            )
        
        # Generate unique download code
        download_code = generate_download_code()
        
        # Upload to MongoDB GridFS
        file_id = await upload_file_to_mongodb(file, download_code)
        
        # Create database record for metadata
        file_record = await create_file_record(db, download_code, file, file_id)
        
        # Return success response
        return {
            "success": True,
            "download_code": download_code,
            "filename": file.filename,
            "file_size": file.size,
            "message": "File uploaded successfully"
        }
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "detail": str(e),
                "message": "Upload failed"
            }
        )

@app.get("/api/preview/{download_code}")
async def preview_file(download_code: str, db = Depends(get_db)):
    """Get file preview/metadata"""
    
    try:
        # Get file record from database
        file_record = await get_file_by_code(db, download_code.upper())
        
        if not file_record:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "detail": "Invalid download code",
                    "message": "File not found"
                }
            )
        
        # Build preview data
        preview_data = {
            "success": True,
            "filename": file_record["original_filename"],
            "file_size": file_record["file_size"],
            "mime_type": file_record.get("mime_type", "application/octet-stream"),
            "upload_date": file_record["upload_date"].isoformat(),
            "download_count": file_record["download_count"]
        }
        
        return preview_data
        
    except Exception as e:
        print(f"Preview error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "detail": str(e),
                "message": "Preview failed"
            }
        )

@app.get("/api/download/{download_code}")
async def download_file(download_code: str, db = Depends(get_db)):
    """Download file using code"""
    
    try:
        # Get file record from database
        file_record = await get_file_by_code(db, download_code.upper())
        
        if not file_record:
            raise HTTPException(
                status_code=404, 
                detail="Invalid download code"
            )
        
        # Download file from MongoDB GridFS
        file_content, filename = await download_file_from_mongodb(file_record["gridfs_id"])
        
        # Update download count
        await increment_download_count(db, file_record["_id"])
        
        # Return file as streaming response
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=file_record.get("mime_type", "application/octet-stream"),
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Download error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Download failed: {str(e)}"
        )

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        from database.mongodb_client import check_database_connection
        
        db_ok = await check_database_connection()
        
        return {
            "status": "healthy" if db_ok else "degraded",
            "database": "ok" if db_ok else "error",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "detail": str(e)
            }
        )

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "detail": exc.detail,
            "message": "Request failed"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "detail": "Internal server error",
            "message": str(exc)
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
