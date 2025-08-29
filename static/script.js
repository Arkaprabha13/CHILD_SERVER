// static/script.js
class FileShareApp {
    constructor() {
        this.initializeElements();
        this.attachEventListeners();
        this.API_BASE = 'http://127.0.0.1:8000/api';
    }

    initializeElements() {
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        this.fileInfo = document.getElementById('fileInfo');
        this.progressBar = document.getElementById('progressBar');
        this.fileDetails = document.getElementById('fileDetails');
        this.uploadResult = document.getElementById('uploadResult');
        this.downloadCode = document.getElementById('downloadCode');
        this.copyBtn = document.getElementById('copyBtn');
        this.newUploadBtn = document.getElementById('newUploadBtn');
        this.codeInput = document.getElementById('codeInput');
        this.previewBtn = document.getElementById('previewBtn');
        this.downloadBtn = document.getElementById('downloadBtn');
        this.filePreview = document.getElementById('filePreview');
        this.previewContent = document.getElementById('previewContent');
    }

    attachEventListeners() {
        // Upload area events
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
        this.uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
        this.uploadArea.addEventListener('dragleave', this.handleDragLeave.bind(this));
        this.uploadArea.addEventListener('drop', this.handleDrop.bind(this));
        
        // File input change
        this.fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        
        // Button events
        this.copyBtn.addEventListener('click', this.copyCode.bind(this));
        this.newUploadBtn.addEventListener('click', this.resetUpload.bind(this));
        this.previewBtn.addEventListener('click', this.previewFile.bind(this));
        this.downloadBtn.addEventListener('click', this.downloadFile.bind(this));
        
        // Code input formatting
        this.codeInput.addEventListener('input', this.formatCodeInput.bind(this));
    }

    handleDragOver(e) {
        e.preventDefault();
        this.uploadArea.classList.add('dragover');
    }

    handleDragLeave(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.processFile(file);
        }
    }

    processFile(file) {
        // Validate file size (100MB limit)
        const maxSize = 100 * 1024 * 1024;
        if (file.size > maxSize) {
            alert('File size exceeds 100MB limit');
            return;
        }

        // Show file info
        this.showFileInfo(file);
        this.uploadFile(file);
    }

    showFileInfo(file) {
        this.uploadArea.style.display = 'none';
        this.fileInfo.style.display = 'block';
        
        const sizeStr = this.formatFileSize(file.size);
        this.fileDetails.innerHTML = `
            <div class="file-item">
                <i class="fas fa-file"></i>
                <span class="file-name">${file.name}</span>
                <span class="file-size">${sizeStr}</span>
            </div>
        `;
    }

    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            // Animate progress
            this.animateProgress();

            const response = await fetch(`${this.API_BASE}/upload`, {
                method: 'POST',
                body: formData
                // Don't set Content-Type header for FormData
            });

            // Check if response is ok
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            // Safe JSON parsing
            const text = await response.text();
            if (!text.trim()) {
                throw new Error('Empty response from server');
            }

            const result = JSON.parse(text);

            if (result.success) {
                this.showUploadSuccess(result);
            } else {
                throw new Error(result.detail || result.message || 'Upload failed');
            }

        } catch (error) {
            console.error('Upload error:', error);
            this.showUploadError(error.message);
        }
    }

    animateProgress() {
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 30;
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
            }
            this.progressBar.style.width = progress + '%';
        }, 200);
    }

    showUploadSuccess(result) {
        this.fileInfo.style.display = 'none';
        this.uploadResult.style.display = 'block';
        this.downloadCode.textContent = result.download_code;
    }

    showUploadError(message) {
        alert(`Upload Error: ${message}`);
        this.resetUpload();
    }

    copyCode() {
        const code = this.downloadCode.textContent;
        navigator.clipboard.writeText(code).then(() => {
            this.copyBtn.innerHTML = '<i class="fas fa-check"></i>';
            setTimeout(() => {
                this.copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
            }, 2000);
        });
    }

    resetUpload() {
        this.uploadArea.style.display = 'block';
        this.fileInfo.style.display = 'none';
        this.uploadResult.style.display = 'none';
        this.progressBar.style.width = '0%';
        this.fileInput.value = '';
    }

    formatCodeInput(e) {
        let value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
        e.target.value = value;
    }

    async previewFile() {
        const code = this.codeInput.value.trim();
        if (!code) {
            alert('Please enter a download code');
            return;
        }

        try {
            const response = await fetch(`${this.API_BASE}/preview/${code}`);
            
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const text = await response.text();
            const data = text ? JSON.parse(text) : {};

            if (data.success !== false) {
                this.showPreview(data);
            } else {
                throw new Error(data.detail || data.message || 'Preview failed');
            }

        } catch (error) {
            console.error('Preview error:', error);
            alert(`Preview Error: ${error.message}`);
        }
    }

    showPreview(data) {
        this.filePreview.style.display = 'block';
        
        let previewHtml = `
            <div class="file-meta">
                <h4><i class="fas fa-file"></i> ${data.filename}</h4>
                <p><strong>Size:</strong> ${this.formatFileSize(data.file_size)}</p>
                <p><strong>Type:</strong> ${data.mime_type}</p>
                <p><strong>Uploaded:</strong> ${new Date(data.upload_date).toLocaleString()}</p>
                <p><strong>Downloads:</strong> ${data.download_count}</p>
            </div>
        `;

        if (data.preview_url && data.mime_type.startsWith('image/')) {
            previewHtml += `<img src="${data.preview_url}" class="preview-image" alt="Preview">`;
        }

        this.previewContent.innerHTML = previewHtml;
    }

    async downloadFile() {
        const code = this.codeInput.value.trim();
        if (!code) {
            alert('Please enter a download code');
            return;
        }

        try {
            const response = await fetch(`${this.API_BASE}/download/${code}`);
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = this.getFilenameFromHeaders(response) || 'download';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                const text = await response.text();
                const error = text ? JSON.parse(text) : {};
                throw new Error(error.detail || error.message || 'Download failed');
            }

        } catch (error) {
            console.error('Download error:', error);
            alert(`Download Error: ${error.message}`);
        }
    }

    getFilenameFromHeaders(response) {
        const disposition = response.headers.get('content-disposition');
        if (disposition) {
            const match = disposition.match(/filename="(.+)"/);
            return match ? match[1] : null;
        }
        return null;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new FileShareApp();
});
