# database/mongodb_client_sync.py
import os
from datetime import datetime, timedelta
from typing import Optional
import uuid

# MongoDB imports (synchronous)
from pymongo import MongoClient
import gridfs
from bson import ObjectId

# Environment setup
from dotenv import load_dotenv
load_dotenv()

# MongoDB configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "file_share")

print(f"MongoDB URL: {MONGODB_URL}")
print(f"Database: {DATABASE_NAME}")

# Initialize MongoDB client (synchronous)
client = MongoClient(MONGODB_URL)
database = client[DATABASE_NAME]

# Collections
files_collection = database.files

# GridFS for file storage
gridfs_bucket = gridfs.GridFS(database)

print("✅ MongoDB client initialized successfully")

# Database dependency
def get_db():
    """Database dependency for Streamlit"""
    return database

# File operations (synchronous versions)
def upload_file_to_mongodb_sync(file, download_code: str) -> ObjectId:
    """Upload file to MongoDB GridFS (synchronous)"""
    try:
        # Read file content
        file_content = file.getvalue()
        
        # Upload to GridFS with metadata
        file_id = gridfs_bucket.put(
            file_content,
            filename=file.name,
            content_type=file.type,
            download_code=download_code,
            upload_date=datetime.utcnow(),
            original_size=len(file_content)
        )
        
        print(f"✅ File uploaded to GridFS with ID: {file_id}")
        return file_id
        
    except Exception as e:
        print(f"MongoDB upload error: {str(e)}")
        raise Exception(f"File upload failed: {str(e)}")

def download_file_from_mongodb_sync(gridfs_id: ObjectId) -> tuple:
    """Download file from MongoDB GridFS (synchronous)"""
    try:
        # Get file from GridFS
        grid_out = gridfs_bucket.get(gridfs_id)
        
        # Read file content
        file_content = grid_out.read()
        filename = grid_out.filename
        
        return file_content, filename
        
    except Exception as e:
        print(f"MongoDB download error: {str(e)}")
        raise Exception(f"File download failed: {str(e)}")

def create_file_record_sync(db, download_code: str, file, gridfs_id: ObjectId) -> dict:
    """Create file metadata record in MongoDB (synchronous)"""
    try:
        file_record = {
            "_id": ObjectId(),
            "download_code": download_code.upper(),
            "original_filename": file.name,
            "file_size": len(file.getvalue()),
            "mime_type": file.type,
            "gridfs_id": gridfs_id,
            "upload_date": datetime.utcnow(),
            "download_count": 0,
            "expiry_date": datetime.utcnow() + timedelta(days=7),
            "is_active": True
        }
        
        # Insert into files collection
        result = files_collection.insert_one(file_record)
        
        print(f"✅ File record created with ID: {result.inserted_id}")
        return file_record
        
    except Exception as e:
        print(f"Database record creation error: {str(e)}")
        raise Exception(f"Failed to create file record: {str(e)}")

def get_file_by_code_sync(db, download_code: str) -> Optional[dict]:
    """Get file record by download code (synchronous)"""
    try:
        file_record = files_collection.find_one({
            "download_code": download_code.upper(),
            "is_active": True
        })
        
        return file_record
        
    except Exception as e:
        print(f"Database query error: {str(e)}")
        return None

def increment_download_count_sync(db, file_id: ObjectId) -> bool:
    """Increment download count for a file (synchronous)"""
    try:
        result = files_collection.update_one(
            {"_id": file_id},
            {"$inc": {"download_count": 1}}
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        print(f"Failed to update download count: {str(e)}")
        return False

# Utility functions (same as before)
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
def check_database_connection_sync() -> bool:
    """Check if database connection is working (synchronous)"""
    try:
        # Simple ping to test connection
        database.command("ping")
        return True
    except Exception as e:
        print(f"Database health check failed: {str(e)}")
        return False
