# app.py
import streamlit as st
import io
import os
from datetime import datetime
import asyncio
import base64

# Import your existing MongoDB functions (adapted for Streamlit)
from database.mongodb_client_sync import (
    get_db, upload_file_to_mongodb_sync, download_file_from_mongodb_sync,
    create_file_record_sync, get_file_by_code_sync, increment_download_count_sync,
    generate_download_code, validate_file_size, format_file_size,
    check_database_connection_sync
)

# Page configuration
st.set_page_config(
    page_title="File Share Platform",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .upload-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    .download-section {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        border: 2px solid #e9ecef;
        margin: 1rem 0;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .error-box {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .code-display {
        font-family: monospace;
        font-size: 1.5rem;
        font-weight: bold;
        color: #007bff;
        text-align: center;
        padding: 1rem;
        background: white;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.title("📁 File Share Platform")
    st.markdown("Upload files and share them with generated download codes")
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Dashboard")
        
        # Health check
        if st.button("🔍 Check System Health"):
            with st.spinner("Checking system health..."):
                db_status = check_database_connection_sync()
                if db_status:
                    st.success("✅ Database: Connected")
                else:
                    st.error("❌ Database: Connection Failed")
        
        st.markdown("---")
        st.markdown("""
        ### How it works:
        1. **Upload** your file
        2. Get a unique **download code**
        3. Share the code with others
        4. **Download** using the code
        """)
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📤 Upload Files", "📥 Download Files", "👁️ Preview Files"])
    
    with tab1:
        upload_section()
    
    with tab2:
        download_section()
    
    with tab3:
        preview_section()

def upload_section():
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.header("📤 Upload Your File")
    st.markdown("Maximum file size: 100MB")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a file to upload",
        type=None,  # Accept all file types
        help="Select any file up to 100MB"
    )
    
    if uploaded_file is not None:
        # Display file info
        file_size = len(uploaded_file.getvalue())
        st.info(f"📄 **{uploaded_file.name}** ({format_file_size(file_size)})")
        
        # Validate file size
        if not validate_file_size(file_size):
            st.error("❌ File size exceeds 100MB limit!")
            return
        
        # Upload button
        if st.button("🚀 Upload File", type="primary"):
            try:
                with st.spinner("Uploading file to database..."):
                    # Get database connection
                    db = get_db()
                    
                    # Generate download code
                    download_code = generate_download_code()
                    
                    # Upload to MongoDB GridFS
                    file_id = upload_file_to_mongodb_sync(uploaded_file, download_code)
                    
                    # Create database record
                    file_record = create_file_record_sync(db, download_code, uploaded_file, file_id)
                    
                    # Success message
                    st.markdown('<div class="success-box">', unsafe_allow_html=True)
                    st.success("✅ File uploaded successfully!")
                    
                    # Display download code
                    st.markdown('<div class="code-display">', unsafe_allow_html=True)
                    st.markdown(f"**Download Code:** `{download_code}`")
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Copy button (using JavaScript)
                    st.markdown(f"""
                    <button onclick="navigator.clipboard.writeText('{download_code}')">
                        📋 Copy Code
                    </button>
                    """, unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # File details
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("File Name", uploaded_file.name)
                    with col2:
                        st.metric("File Size", format_file_size(file_size))
                    with col3:
                        st.metric("Download Code", download_code)
                        
            except Exception as e:
                st.markdown('<div class="error-box">', unsafe_allow_html=True)
                st.error(f"❌ Upload failed: {str(e)}")
                st.markdown('</div>', unsafe_allow_html=True)

def download_section():
    st.markdown('<div class="download-section">', unsafe_allow_html=True)
    st.header("📥 Download Files")
    st.markdown("Enter the download code to retrieve your file")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Download code input
    download_code = st.text_input(
        "Download Code",
        placeholder="Enter 8-character download code",
        max_chars=8,
        help="Enter the code you received when uploading the file"
    ).upper()
    
    if download_code and len(download_code) == 8:
        if st.button("📥 Download File", type="primary"):
            try:
                with st.spinner("Retrieving file from database..."):
                    # Get database connection
                    db = get_db()
                    
                    # Get file record
                    file_record = get_file_by_code_sync(db, download_code)
                    
                    if not file_record:
                        st.error("❌ Invalid download code! File not found.")
                        return
                    
                    # Download file from GridFS
                    file_content, filename = download_file_from_mongodb_sync(file_record["gridfs_id"])
                    
                    # Update download count
                    increment_download_count_sync(db, file_record["_id"])
                    
                    # Provide download
                    st.success("✅ File found! Click the button below to download.")
                    
                    # Download button
                    st.download_button(
                        label=f"💾 Download {filename}",
                        data=file_content,
                        file_name=filename,
                        mime=file_record.get("mime_type", "application/octet-stream")
                    )
                    
                    # File info
                    st.info(f"""
                    **File:** {filename}  
                    **Size:** {format_file_size(file_record['file_size'])}  
                    **Uploaded:** {file_record['upload_date'].strftime('%Y-%m-%d %H:%M:%S')}  
                    **Downloads:** {file_record['download_count'] + 1}
                    """)
                    
            except Exception as e:
                st.error(f"❌ Download failed: {str(e)}")
    
    elif download_code and len(download_code) != 8:
        st.warning("⚠️ Download code must be exactly 8 characters long")

def preview_section():
    st.header("👁️ File Preview")
    st.markdown("Preview file information without downloading")
    
    # Preview code input
    preview_code = st.text_input(
        "Preview Code",
        placeholder="Enter 8-character download code for preview",
        max_chars=8,
        key="preview_input"
    ).upper()
    
    if preview_code and len(preview_code) == 8:
        if st.button("👁️ Preview File", type="secondary"):
            try:
                with st.spinner("Loading file information..."):
                    # Get database connection
                    db = get_db()
                    
                    # Get file record
                    file_record = get_file_by_code_sync(db, preview_code)
                    
                    if not file_record:
                        st.error("❌ Invalid preview code! File not found.")
                        return
                    
                    # Display file information
                    st.success("✅ File found!")
                    
                    # File details in columns
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📄 File Information")
                        st.write(f"**Name:** {file_record['original_filename']}")
                        st.write(f"**Size:** {format_file_size(file_record['file_size'])}")
                        st.write(f"**Type:** {file_record.get('mime_type', 'Unknown')}")
                    
                    with col2:
                        st.subheader("📊 Statistics")
                        st.write(f"**Uploaded:** {file_record['upload_date'].strftime('%Y-%m-%d %H:%M:%S')}")
                        st.write(f"**Downloads:** {file_record['download_count']}")
                        st.write(f"**Status:** {'🟢 Active' if file_record.get('is_active', True) else '🔴 Inactive'}")
                    
                    # Show file type specific preview
                    mime_type = file_record.get('mime_type', '')
                    if mime_type.startswith('image/'):
                        st.info("🖼️ This is an image file")
                    elif mime_type.startswith('video/'):
                        st.info("🎥 This is a video file")
                    elif mime_type.startswith('audio/'):
                        st.info("🎵 This is an audio file")
                    elif 'pdf' in mime_type.lower():
                        st.info("📄 This is a PDF document")
                    elif mime_type.startswith('text/'):
                        st.info("📝 This is a text file")
                    else:
                        st.info("📁 Binary file")
                    
            except Exception as e:
                st.error(f"❌ Preview failed: {str(e)}")

if __name__ == "__main__":
    main()
