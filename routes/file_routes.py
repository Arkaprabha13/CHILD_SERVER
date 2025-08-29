# routes/file_routes.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
import io
from typing import Dict, Any

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload file and return download code"""
    
    # Validate file size
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    
    # Generate unique download code
    download_code = str(uuid.uuid4())[:8].upper()
    
    try:
        # For Supabase implementation
        file_path = f"{download_code}/{file.filename}"
        await upload_file_to_supabase(file, file_path)
        
        # Store metadata in PostgreSQL
        db = next(get_db())
        file_record = FileRecord(
            id=str(uuid.uuid4()),
            download_code=download_code,
            original_filename=file.filename,
            file_size=file.size,
            mime_type=file.content_type,
            storage_path=file_path
        )
        db.add(file_record)
        db.commit()
        
        return {
            "success": True,
            "download_code": download_code,
            "filename": file.filename,
            "file_size": file.size,
            "message": "File uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{download_code}")
async def download_file(download_code: str):
    """Download file using code"""
    
    try:
        # Get file metadata
        db = next(get_db())
        file_record = db.query(FileRecord).filter(
            FileRecord.download_code == download_code
        ).first()
        
        if not file_record:
            raise HTTPException(status_code=404, detail="Invalid download code")
        
        # Download from Supabase
        file_content = await download_file_from_supabase(file_record.storage_path)
        
        # Update download count
        file_record.download_count += 1
        db.commit()
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=file_record.mime_type,
            headers={
                "Content-Disposition": f"attachment; filename={file_record.original_filename}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preview/{download_code}")
async def preview_file(download_code: str):
    """Get file preview/metadata"""
    
    try:
        db = next(get_db())
        file_record = db.query(FileRecord).filter(
            FileRecord.download_code == download_code
        ).first()
        
        if not file_record:
            raise HTTPException(status_code=404, detail="Invalid download code")
        
        # Generate preview based on file type
        preview_data = {
            "filename": file_record.original_filename,
            "file_size": file_record.file_size,
            "mime_type": file_record.mime_type,
            "upload_date": file_record.upload_date.isoformat(),
            "download_count": file_record.download_count
        }
        
        # Add preview URL for images
        if file_record.mime_type.startswith('image/'):
            preview_data["preview_url"] = f"/api/preview-image/{download_code}"
        
        return preview_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Include router in main app
app.include_router(router, prefix="/api")
