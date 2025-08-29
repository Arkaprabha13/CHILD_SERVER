# database/supabase_client.py
import os
from datetime import datetime, timedelta
from typing import Optional
import uuid

# Supabase and database imports
from supabase import create_client, Client
from sqlalchemy import create_engine, Column, String, Integer, DateTime, BigInteger, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# FastAPI imports (needed for file operations)
from fastapi import HTTPException, UploadFile
import asyncio
import aiofiles
from io import BytesIO

# Environment setup
from dotenv import load_dotenv
load_dotenv()

# Supabase client setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# PostgreSQL connection for metadata using your provided credentials
DATABASE_URL = f"postgresql://{os.getenv('user', 'postgres.pgwdovfvaclqpcgeizib')}:{os.getenv('password')}@{os.getenv('host', 'aws-1-ap-southeast-1.pooler.supabase.com')}:{os.getenv('port', '5432')}/{os.getenv('dbname', 'postgres')}"

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# File record model
class FileRecord(Base):
    __tablename__ = "files"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    download_code = Column(String, unique=True, index=True, nullable=False)
    original_filename = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String, nullable=True)
    storage_path = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    download_count = Column(Integer, default=0, nullable=False)
    expiry_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

# Create tables
def create_tables():
    """Create database tables if they don't exist"""
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating tables: {e}")

# Initialize tables on import
create_tables()

# Database dependency
def get_db():
    """Database session dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Supabase Storage Operations
async def upload_file_to_supabase(file: UploadFile, file_path: str) -> dict:
    """Upload file to Supabase storage"""
    try:
        # Read file content
        file_content = await file.read()
        
        # Reset file pointer for potential reuse
        await file.seek(0)
        
        # Upload to Supabase storage
        response = supabase.storage.from_("files").upload(
            path=file_path,
            file=file_content,
            file_options={
                "content-type": file.content_type,
                "upsert": False  # Don't overwrite existing files
            }
        )
        
        if hasattr(response, 'error') and response.error:
            raise HTTPException(
                status_code=500, 
                detail=f"Supabase upload failed: {response.error.message}"
            )
        
        return {
            "success": True,
            "path": file_path,
            "size": len(file_content)
        }
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Upload failed: {str(e)}"
        )

async def download_file_from_supabase(file_path: str) -> bytes:
    """Download file from Supabase storage"""
    try:
        response = supabase.storage.from_("files").download(file_path)
        
        if not response:
            raise HTTPException(
                status_code=404, 
                detail="File not found in storage"
            )
        
        return response
        
    except Exception as e:
        print(f"Download error: {str(e)}")
        raise HTTPException(
            status_code=404, 
            detail=f"File download failed: {str(e)}"
        )

async def get_file_preview_url(file_path: str, expires_in: int = 3600) -> str:
    """Get a signed URL for file preview"""
    try:
        response = supabase.storage.from_("files").create_signed_url(
            path=file_path,
            expires_in=expires_in
        )
        
        if hasattr(response, 'error') and response.error:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create preview URL: {response.error.message}"
            )
        
        return response.get('signedURL', '')
        
    except Exception as e:
        print(f"Preview URL error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Preview URL generation failed: {str(e)}"
        )

async def delete_file_from_supabase(file_path: str) -> bool:
    """Delete file from Supabase storage"""
    try:
        response = supabase.storage.from_("files").remove([file_path])
        
        if hasattr(response, 'error') and response.error:
            raise HTTPException(
                status_code=500,
                detail=f"File deletion failed: {response.error.message}"
            )
        
        return True
        
    except Exception as e:
        print(f"Delete error: {str(e)}")
        return False

# Database helper functions
def create_file_record(db, download_code: str, file: UploadFile, file_path: str, expiry_days: int = 7) -> FileRecord:
    """Create a new file record in the database"""
    try:
        file_record = FileRecord(
            id=str(uuid.uuid4()),
            download_code=download_code,
            original_filename=file.filename,
            file_size=file.size,
            mime_type=file.content_type,
            storage_path=file_path,
            upload_date=datetime.utcnow(),
            download_count=0,
            expiry_date=datetime.utcnow() + timedelta(days=expiry_days) if expiry_days > 0 else None,
            is_active=True
        )
        
        db.add(file_record)
        db.commit()
        db.refresh(file_record)
        
        return file_record
        
    except Exception as e:
        db.rollback()
        print(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create file record: {str(e)}"
        )

def get_file_by_code(db, download_code: str) -> Optional[FileRecord]:
    """Get file record by download code"""
    try:
        return db.query(FileRecord).filter(
            FileRecord.download_code == download_code.upper(),
            FileRecord.is_active == True
        ).first()
        
    except Exception as e:
        print(f"Database query error: {str(e)}")
        return None

def increment_download_count(db, file_record: FileRecord) -> bool:
    """Increment download count for a file"""
    try:
        file_record.download_count += 1
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        print(f"Failed to update download count: {str(e)}")
        return False

def deactivate_file(db, file_record: FileRecord) -> bool:
    """Mark file as inactive (soft delete)"""
    try:
        file_record.is_active = False
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        print(f"Failed to deactivate file: {str(e)}")
        return False

def cleanup_expired_files(db) -> int:
    """Remove expired files from database and storage"""
    try:
        expired_files = db.query(FileRecord).filter(
            FileRecord.expiry_date <= datetime.utcnow(),
            FileRecord.is_active == True
        ).all()
        
        cleaned_count = 0
        for file_record in expired_files:
            # Delete from storage
            try:
                asyncio.create_task(delete_file_from_supabase(file_record.storage_path))
            except:
                pass  # Continue even if storage deletion fails
            
            # Mark as inactive in database
            file_record.is_active = False
            cleaned_count += 1
        
        db.commit()
        return cleaned_count
        
    except Exception as e:
        db.rollback()
        print(f"Cleanup error: {str(e)}")
        return 0

# Utility functions
def generate_download_code(length: int = 8) -> str:
    """Generate a unique download code"""
    return str(uuid.uuid4()).replace('-', '').upper()[:length]

def validate_file_size(file_size: int, max_size: int = 100 * 1024 * 1024) -> bool:
    """Validate file size (default 100MB limit)"""
    return file_size <= max_size

def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return filename.split('.')[-1].lower() if '.' in filename else ''

def is_image_file(mime_type: str) -> bool:
    """Check if file is an image"""
    return mime_type and mime_type.startswith('image/')

def is_text_file(mime_type: str) -> bool:
    """Check if file is a text file"""
    text_types = ['text/', 'application/json', 'application/xml']
    return mime_type and any(mime_type.startswith(t) for t in text_types)

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

# Health check function
async def check_database_connection() -> bool:
    """Check if database connection is working"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        print(f"Database health check failed: {str(e)}")
        return False

async def check_supabase_connection() -> bool:
    """Check if Supabase connection is working"""
    try:
        # Try to list buckets as a connection test
        buckets = supabase.storage.list_buckets()
        return True
    except Exception as e:
        print(f"Supabase health check failed: {str(e)}")
        return False

# Initialize storage bucket if it doesn't exist
def initialize_storage_bucket():
    """Create the files bucket if it doesn't exist"""
    try:
        # Try to get bucket info
        bucket_info = supabase.storage.get_bucket("files")
        if not bucket_info:
            # Create bucket if it doesn't exist
            supabase.storage.create_bucket("files", options={"public": False})
            print("Created 'files' storage bucket")
    except Exception as e:
        print(f"Storage bucket initialization: {str(e)}")

# Initialize on import
initialize_storage_bucket()

# Export main components
__all__ = [
    'FileRecord',
    'get_db',
    'upload_file_to_supabase',
    'download_file_from_supabase',
    'get_file_preview_url',
    'delete_file_from_supabase',
    'create_file_record',
    'get_file_by_code',
    'increment_download_count',
    'deactivate_file',
    'cleanup_expired_files',
    'generate_download_code',
    'validate_file_size',
    'format_file_size',
    'check_database_connection',
    'check_supabase_connection'
]
