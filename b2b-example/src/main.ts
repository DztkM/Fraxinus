import './style.css'
import { api } from './api'

// Elements
const authSection = document.getElementById('auth-section')!;
const dashboardSection = document.getElementById('dashboard-section')!;
const authForm = document.getElementById('auth-form') as HTMLFormElement;
const authError = document.getElementById('auth-error')!;

const uploadForm = document.getElementById('upload-form') as HTMLFormElement;
const fileInput = document.getElementById('fileInput') as HTMLInputElement;
const fileMsg = document.querySelector('.file-msg')!;
const uploadBtn = document.getElementById('uploadBtn') as HTMLButtonElement;
const uploadProgressContainer = document.getElementById('upload-progress-container')!;
const uploadProgress = document.getElementById('upload-progress')!;
const uploadStatus = document.getElementById('upload-status')!;

const filesList = document.getElementById('filesList')!;
const refreshFilesBtn = document.getElementById('refreshFilesBtn')!;

// Events
authForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const apiKey = (document.getElementById('apiKey') as HTMLInputElement).value;
  const userId = (document.getElementById('userId') as HTMLInputElement).value;

  try {
    authError.classList.add('hidden');
    await api.authenticate(apiKey, userId);
    
    // Switch view
    authSection.classList.add('hidden');
    dashboardSection.classList.remove('hidden');
    
    loadFiles();
  } catch (error: any) {
    authError.textContent = error.message;
    authError.classList.remove('hidden');
  }
});

fileInput.addEventListener('change', () => {
  if (fileInput.files && fileInput.files.length > 0) {
    fileMsg.textContent = fileInput.files[0].name;
  } else {
    fileMsg.textContent = 'Drag & Drop or Click to choose a file';
  }
});

uploadForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!fileInput.files || fileInput.files.length === 0) return;

  const file = fileInput.files[0];
  uploadBtn.disabled = true;
  uploadProgressContainer.classList.remove('hidden');
  uploadStatus.textContent = 'Uploading: 0%';
  uploadProgress.style.width = '0%';
  uploadStatus.style.color = 'var(--text-muted)';

  try {
    await api.uploadFile(file, (percent) => {
      uploadProgress.style.width = `${percent}%`;
      uploadStatus.textContent = `Uploading: ${percent}%`;
    });
    
    uploadStatus.textContent = 'Upload complete!';
    uploadStatus.style.color = 'var(--success-color)';
    
    // Reset after 2s
    setTimeout(() => {
      uploadProgressContainer.classList.add('hidden');
      uploadBtn.disabled = false;
      fileInput.value = '';
      fileMsg.textContent = 'Drag & Drop or Click to choose a file';
      loadFiles();
    }, 2000);
    
  } catch (error: any) {
    console.error(error);
    uploadStatus.textContent = `Error: ${error.message}`;
    uploadStatus.style.color = 'var(--danger-color)';
    uploadBtn.disabled = false;
  }
});

refreshFilesBtn.addEventListener('click', loadFiles);

async function loadFiles() {
  try {
    const files = await api.listFiles();
    renderFiles(files);
  } catch (error) {
    console.error('Error loading files:', error);
  }
}

function renderFiles(files: any[]) {
  filesList.innerHTML = '';
  
  if (files.length === 0) {
    filesList.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-muted)">No files found</td></tr>';
    return;
  }

  files.forEach(file => {
    const tr = document.createElement('tr');
    
    // Name
    const tdName = document.createElement('td');
    tdName.textContent = file.original_name;
    
    // Status
    const tdStatus = document.createElement('td');
    const statusSpan = document.createElement('span');
    statusSpan.textContent = file.status;
    statusSpan.style.color = file.status === 'completed' ? 'var(--success-color)' : 'var(--text-muted)';
    tdStatus.appendChild(statusSpan);
    
    // Actions
    const tdActions = document.createElement('td');
    tdActions.style.display = 'flex';
    tdActions.style.gap = '8px';
    
    const dlBtn = document.createElement('button');
    dlBtn.textContent = 'Download';
    dlBtn.className = 'btn secondary small';
    dlBtn.onclick = () => downloadFile(file.id);
    
    const delBtn = document.createElement('button');
    delBtn.textContent = 'Delete';
    delBtn.className = 'btn secondary small';
    delBtn.style.backgroundColor = 'var(--danger-color, #dc3545)';
    delBtn.style.color = 'white';
    delBtn.onclick = () => deleteFile(file.id);
    
    tdActions.appendChild(dlBtn);
    tdActions.appendChild(delBtn);
    
    tr.appendChild(tdName);
    tr.appendChild(tdStatus);
    tr.appendChild(tdActions);
    
    filesList.appendChild(tr);
  });
}

async function downloadFile(fileId: string) {
  try {
    const res = await api.getDownloadUrl(fileId);
    if (res.url) {
      window.open(res.url, '_blank');
    }
  } catch (error) {
    console.error('Error downloading file:', error);
    alert('Failed to get download link');
  }
}

async function deleteFile(fileId: string) {
  if (!confirm('Are you sure you want to delete this file?')) return;
  try {
    await api.deleteFile(fileId);
    loadFiles();
  } catch (error) {
    console.error('Error deleting file:', error);
    alert('Failed to delete file');
  }
}
