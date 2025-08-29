# database/mongodb_client.py
import os
from datetime import datetime, timedelta
from typing import Optional
import uuid
import asyncio

# MongoDB imports
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
import gridfs
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

# FastAPI imports
from fastapi import HTTPException, UploadFile

# Environment setup
from dotenv import load_dotenv
load_dotenv()

# MongoDB configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "file_share")

print(f"MongoDB URL: {MONGODB_URL}")
print(f"Database: {DATABASE_NAME}")

# Initialize MongoDB client
client = AsyncIOMotorClient(MONGODB_URL)
database = client[DATABASE_NAME]

# Collections
files_collection = database.files
download_codes_collection = database.download_codes

# GridFS for file storage
gridfs_bucket = AsyncIOMotorGridFSBucket(database)

print("✅ MongoDB client initialized successfully")

# Database dependency
async def get_db():
    """Database dependency for FastAPI"""
    return database

# File operations
async def upload_file_to_mongodb(file: UploadFile, download_code: str) -> ObjectId:
    """Upload file to MongoDB GridFS"""
    try:
        # Read file content
        file_content = await file.read()
        await file.seek(0)  # Reset file pointer
        
        # Upload to GridFS with metadata
        file_id = await gridfs_bucket.upload_from_stream(
            file.filename,
            file_content,
            metadata={
                "content_type": file.content_type,
                "download_code": download_code,
                "upload_date": datetime.utcnow(),
                "original_size": len(file_content)
            }
        )
        
        print(f"✅ File uploaded to GridFS with ID: {file_id}")
        return file_id
        
    except Exception as e:
        print(f"MongoDB upload error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"File upload failed: {str(e)}"
        )

async def download_file_from_mongodb(gridfs_id: ObjectId) -> tuple:
    """Download file from MongoDB GridFS"""
    try:
        # Open download stream
        grid_out = await gridfs_bucket.open_download_stream(gridfs_id)
        
        # Read file content
        file_content = await grid_out.read()
        filename = grid_out.filename
        
        return file_content, filename
        
    except Exception as e:
        print(f"MongoDB download error: {str(e)}")
        raise HTTPException(
            status_code=404, 
            detail=f"File download failed: {str(e)}"
        )

async def create_file_record(db, download_code: str, file: UploadFile, gridfs_id: ObjectId) -> dict:
    """Create file metadata record in MongoDB"""
    try:
        file_record = {
            "_id": ObjectId(),
            "download_code": download_code.upper(),
            "original_filename": file.filename,
            "file_size": file.size,
            "mime_type": file.content_type,
            "gridfs_id": gridfs_id,
            "upload_date": datetime.utcnow(),
            "download_count": 0,
            "expiry_date": datetime.utcnow() + timedelta(days=7),
            "is_active": True
        }
        
        # Insert into files collection
        result = await files_collection.insert_one(file_record)
        
        print(f"✅ File record created with ID: {result.inserted_id}")
        return file_record
        
    except Exception as e:
        print(f"Database record creation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create file record: {str(e)}"
        )

async def get_file_by_code(db, download_code: str) -> Optional[dict]:
    """Get file record by download code"""
    try:
        file_record = await files_collection.find_one({
            "download_code": download_code.upper(),
            "is_active": True
        })
        
        return file_record
        
    except Exception as e:
        print(f"Database query error: {str(e)}")
        return None

async def increment_download_count(db, file_id: ObjectId) -> bool:
    """Increment download count for a file"""
    try:
        result = await files_collection.update_one(
            {"_id": file_id},
            {"$inc": {"download_count": 1}}
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        print(f"Failed to update download count: {str(e)}")
        return False

# Utility functions
def generate_download_code(length: int = 8) -> str:
    """Generate a unique download code"""
    return str(uuid.uuid4()).replace('-', '').upper()[:length]

def validate_file_size(file_size: int, max_size: int = 100 * 1024 * 1024) -> bool:
    """Validate file size (default 100MB limit)"""
    return file_size <= max_size

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
        # Simple ping to test connection
        await database.command("ping")
        return True
    except Exception as e:
        print(f"Database health check failed: {str(e)}")
        return False

# Cleanup function
async def cleanup_expired_files() -> int:
    """Remove expired files from database and GridFS"""
    try:
        # Find expired files
        expired_files = files_collection.find({
            "expiry_date": {"$lte": datetime.utcnow()},
            "is_active": True
        })
        
        cleaned_count = 0
        async for file_record in expired_files:
            try:
                # Delete from GridFS
                await gridfs_bucket.delete(file_record["gridfs_id"])
                
                # Mark as inactive in database
                await files_collection.update_one(
                    {"_id": file_record["_id"]},
                    {"$set": {"is_active": False}}
                )
                
                cleaned_count += 1
                
            except Exception as e:
                print(f"Error cleaning up file {file_record['_id']}: {e}")
                continue
        
        print(f"✅ Cleaned up {cleaned_count} expired files")
        return cleaned_count
        
    except Exception as e:
        print(f"Cleanup error: {str(e)}")
        return 0

# File record model (for type hinting)
class FileRecord:
    def __init__(self, download_code: str, original_filename: str, 
                 file_size: int, mime_type: str, gridfs_id: ObjectId):
        self.download_code = download_code
        self.original_filename = original_filename
        self.file_size = file_size
        self.mime_type = mime_type
        self.gridfs_id = gridfs_id
        self.upload_date = datetime.utcnow()
        self.download_count = 0
        self.expiry_date = datetime.utcnow() + timedelta(days=7)
        self.is_active = True

# Export main components
__all__ = [
    'get_db',
    'upload_file_to_mongodb',
    'download_file_from_mongodb',
    'create_file_record',
    'get_file_by_code',
    'increment_download_count',
    'generate_download_code',
    'validate_file_size',
    'format_file_size',
    'check_database_connection',
    'cleanup_expired_files',
    'FileRecord'
]
