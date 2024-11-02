from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import boto3
from datetime import datetime
import os
import mimetypes
import smtplib
from email.mime.text import MIMEText
from pydantic import BaseModel

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS Configuration
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name=os.environ.get('AWS_REGION', 'ap-southeast-2')
)

# Configuration
BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
ALLOWED_EXTENSIONS = {'.epub', '.pdf', '.mobi', '.azw', '.azw3', '.doc', '.docx', '.zip'}

# Email Configuration
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
ADMIN_EMAIL = "nifzat@gmail.com"  # Your email to receive notifications

class UploadRequest(BaseModel):
    filename: str

def send_admin_notification(filename: str, filesize: int):
    try:
        print("Attempting to send email notification...")  # Debug log
        
        msg = MIMEText(f"""
        Hello,

        A new file has been uploaded to your S3 bucket:
        
        Filename: {filename}
        Size: {format_file_size(filesize)}
        Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        The file is available in your S3 bucket: {BUCKET_NAME}/uploads/{filename}
        
        Best regards,
        Blacx Upload System
        """)
        
        msg['Subject'] = f'Blacx: New File Upload - {filename}'
        msg['From'] = SMTP_USERNAME
        msg['To'] = ADMIN_EMAIL

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            print("Connecting to SMTP server...")  # Debug log
            server.starttls()
            print("Logging in to SMTP server...")  # Debug log
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            print("Sending email...")  # Debug log
            server.send_message(msg)
            print("Email sent successfully!")  # Debug log
            return True
    except Exception as e:
        print(f"Failed to send admin notification: {str(e)}")  # Error log
        return False

def format_file_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

@app.post("/generate-upload-url")
async def generate_upload_url(upload_request: UploadRequest):
    try:
        # Validate file extension
        _, file_extension = os.path.splitext(upload_request.filename.lower())
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Invalid file type")

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{upload_request.filename}"
        
        # Generate upload URL
        upload_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': f'uploads/{filename}',
                'ContentType': mimetypes.guess_type(upload_request.filename)[0],
            },
            ExpiresIn=86400  # 1 day
        )

        return JSONResponse({
            "upload_url": upload_url,
            "filename": filename
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/notify-upload")
async def notify_upload(data: dict):
    try:
        success = send_admin_notification(data['filename'], data['filesize'])
        if not success:
            raise Exception("Failed to send email notification")
        return {"status": "success"}
    except Exception as e:
        print(f"Error in notify_upload: {str(e)}")  # Error log
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    try:
        s3_client.list_buckets()
        return {
            "status": "healthy",
            "s3_connection": "ok",
            "bucket": BUCKET_NAME
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/")
async def root():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Blacx File Upload</title>
        <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary-color: #000000;
                --accent-color: #333333;
                --success-color: #4CAF50;
                --error-color: #f44336;
                --background-color: #ffffff;
            }

            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body { 
                font-family: 'Inter', sans-serif;
                background-color: #f5f5f5;
                color: var(--primary-color);
                line-height: 1.6;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .container {
                background: var(--background-color);
                max-width: 800px;
                width: 90%;
                padding: 40px;
                border-radius: 16px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                transform: translateY(20px);
                opacity: 0;
                animation: slideUp 0.5s ease forwards;
            }

            @keyframes slideUp {
                to {
                    transform: translateY(0);
                    opacity: 1;
                }
            }

            .logo {
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                font-weight: 600;
                color: var(--primary-color);
                letter-spacing: -1px;
            }

            .logo span {
                background: linear-gradient(45deg, #000, #333);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                animation: gradientMove 3s ease infinite;
            }

            @keyframes gradientMove {
                0%, 100% {
                    background-position: 0% 50%;
                }
                50% {
                    background-position: 100% 50%;
                }
            }

            .form-group {
                margin-bottom: 24px;
                opacity: 0;
                transform: translateY(10px);
                animation: fadeIn 0.5s ease forwards;
            }

            @keyframes fadeIn {
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            label {
                display: block;
                margin-bottom: 8px;
                font-weight: 500;
                color: var(--accent-color);
            }

            input {
                width: 100%;
                padding: 12px;
                border: 2px solid #eee;
                border-radius: 8px;
                font-size: 16px;
                transition: all 0.3s ease;
            }

            input:focus {
                border-color: var(--primary-color);
                outline: none;
                box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
            }

            .password-input {
                margin-top: 20px;
                margin-bottom: 20px;
            }

            .file-input-container {
                position: relative;
                padding: 30px;
                border: 2px dashed #ccc;
                border-radius: 8px;
                text-align: center;
                transition: all 0.3s ease;
                cursor: pointer;
            }

            .file-input-container.dragover {
                border-color: var(--primary-color);
                background: #f8f8f8;
            }

            .file-input-container input[type="file"] {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                opacity: 0;
                cursor: pointer;
            }

            .progress-container {
                margin: 20px 0;
                display: none;
            }

            .progress {
                height: 6px;
                background: #eee;
                border-radius: 3px;
                overflow: hidden;
                position: relative;
                margin: 8px 0;
            }

            .progress-bar {
                height: 100%;
                width: 0%;
                background: linear-gradient(90deg, #000, #333);
                background-size: 200% 100%;
                border-radius: 3px;
                transition: width 0.3s ease;
                animation: gradientMove 2s linear infinite;
            }

            button {
                background: var(--primary-color);
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s ease;
                width: 100%;
                margin-top: 20px;
            }

            button:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }

            button:disabled {
                background: #ccc;
                cursor: not-allowed;
                transform: none;
            }

            #status {
                margin-top: 20px;
                padding: 12px;
                border-radius: 8px;
                text-align: center;
                display: none;
            }

            #status.success {
                background: #e8f5e9;
                color: #2e7d32;
                display: block;
            }

            #status.error {
                background: #ffebee;
                color: #c62828;
                display: block;
            }

            .uploaded-files {
                margin-top: 20px;
                padding: 15px;
                background: #f8f8f8;
                border-radius: 8px;
                display: none;
            }

            .file-list {
                list-style: none;
            }

            .file-list li {
                padding: 8px 12px;
                margin: 4px 0;
                background: white;
                border-radius: 4px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .supported-formats {
                text-align: center;
                margin-top: 20px;
                font-size: 14px;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">
                <span>BLACX</span>
            </div>

            <div class="form-group">
                <div class="file-input-container" id="dropZone">
                    <input type="file" id="fileInput" multiple accept=".epub,.pdf,.mobi,.azw,.azw3,.doc,.docx,.zip">
                    <div>Drag and drop your files here or click to browse</div>
                    <div class="file-name"></div>
                </div>
            </div>

            <div class="password-input">
                <label for="passwordInput">Password:</label>
                <input type="password" id="passwordInput" placeholder="Enter password to upload">
            </div>

            <button onclick="checkPasswordAndUpload()" id="uploadButton">Upload Files</button>

            <div class="progress-container" id="progressContainer">
                <div id="currentFile"></div>
                <div class="progress">
                    <div class="progress-bar"></div>
                </div>
            </div>
            
            <div id="status"></div>

            <div class="uploaded-files">
                <h3>Uploaded Files:</h3>
                <ul class="file-list"></ul>
            </div>

            <div class="supported-formats">
                Supported formats: .epub, .pdf, .mobi, .azw, .azw3, .doc, .docx, .zip
            </div>
        </div>

        <script>
        const dropZone = document.getElementById('dropZone');
        const fileList = document.querySelector('.file-list');
        const uploadedFiles = document.querySelector('.uploaded-files');
        const progressContainer = document.getElementById('progressContainer');
        const currentFile = document.getElementById('currentFile');
        const progressBar = document.querySelector('.progress-bar');
        const status = document.getElementById('status');

        function formatBytes(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        async function uploadFile(file) {
            try {
                currentFile.textContent = `Uploading: ${file.name}`;
                progressContainer.style.display = 'block';
                progressBar.style.width = '0%';

                // Get upload URL
                const response = await axios.post('/generate-upload-url', {
                    filename: file.name
                });
                
                // Upload to S3
                await axios.put(response.data.upload_url, file, {
                    headers: {
                        'Content-Type': file.type
                    },
                    onUploadProgress: (progressEvent) => {
                        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                        progressBar.style.width = percent + '%';
                        currentFile.textContent = `Uploading ${file.name}: ${percent}%`;
                    }
                });

                // Notify admin
                await axios.post('/notify-upload', {
                    filename: response.data.filename,
                    filesize: file.size
                });

                // Add to completed list
                const li = document.createElement('li');
                li.innerHTML = `
                    <span>${file.name} (${formatBytes(file.size)})</span>
                    <span class="success">✓</span>
                `;
                fileList.appendChild(li);
                uploadedFiles.classList.add('show');

                return true;
            } catch (error) {
                status.textContent = 'Error: ' + (error.response?.data?.detail || error.message);
                status.className = 'status error';
                return false;
            }
        }

        async function checkPasswordAndUpload() {
            const password = document.getElementById('passwordInput').value;
            const files = document.getElementById('fileInput').files;
            
            if (password !== 'blacx123') {
                status.textContent = 'Incorrect password!';
                status.className = 'status error';
                status.style.display = 'block';
                return;
            }

            if (!files.length) {
                status.textContent = 'Please select files to upload';
                status.className = 'status error';
                status.style.display = 'block';
                return;
            }

            for (const file of Array.from(files)) {
                await uploadFile(file);
            }
            
            progressContainer.style.display = 'none';
            status.textContent = 'All uploads completed!';
            status.className = 'status success';
        }

        // File input change handler
        document.getElementById('fileInput').addEventListener('change', function(e) {
            const files = Array.from(e.target.files);
            document.querySelector('.file-name').textContent = 
                files.map(f => f.name).join(', ');
        });

        // Drag and drop handlers
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', async (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            const files = Array.from(e.dataTransfer.files);
            document.getElementById('fileInput').files = e.dataTransfer.files;
            document.querySelector('.file-name').textContent = 
                files.map(f => f.name).join(', ');
        });
        </script>
    </body>
    </html>
    """)