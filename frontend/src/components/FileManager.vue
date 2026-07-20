<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuth } from '@clerk/vue'
import { fetchFiles, uploadFile, downloadFile, type FileItem } from '../services/api'

const { getToken, isSignedIn } = useAuth()

const files = ref<FileItem[]>([])
const isLoadingFiles = ref(false)
const errorMsg = ref<string | null>(null)

// Upload state
const isUploading = ref(false)
const uploadProgress = ref(0)
const fileInput = ref<HTMLInputElement | null>(null)

const loadFiles = async () => {
  if (!isSignedIn.value) return
  isLoadingFiles.value = true
  errorMsg.value = null
  
  try {
    const token = await getToken.value()
    if (!token) throw new Error("No token available")
    files.value = await fetchFiles(token)
  } catch (error: any) {
    errorMsg.value = `Failed to load files: ${error.message}`
    console.error(error)
  } finally {
    isLoadingFiles.value = false
  }
}

onMounted(() => {
  loadFiles()
})

const handleFileSelect = async (event: Event) => {
  const target = event.target as HTMLInputElement
  if (!target.files || target.files.length === 0) return
  
  const file = target.files.item(0)
  if (!file) return
  await performUpload(file)
  
  // Clear input
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const handleDrop = async (event: DragEvent) => {
  event.preventDefault()
  if (!event.dataTransfer?.files || event.dataTransfer.files.length === 0) return
  
  const file = event.dataTransfer.files.item(0)
  if (!file) return
  await performUpload(file)
}

const handleDragOver = (event: DragEvent) => {
  event.preventDefault()
}

const performUpload = async (file: File) => {
  errorMsg.value = null
  isUploading.value = true
  uploadProgress.value = 0
  
  try {
    const token = await getToken.value()
    if (!token) throw new Error("No token available")
    
    await uploadFile(token, file, (progress) => {
      uploadProgress.value = progress
    })
    
    // Refresh file list after upload
    await loadFiles()
  } catch (error: any) {
    errorMsg.value = `Upload failed: ${error.message}`
    console.error(error)
  } finally {
    isUploading.value = false
    uploadProgress.value = 0
  }
}

const triggerDownload = async (fileId: string) => {
  errorMsg.value = null
  try {
    const token = await getToken.value()
    if (!token) throw new Error("No token available")
    
    await downloadFile(token, fileId)
  } catch (error: any) {
    errorMsg.value = `Download failed: ${error.message}`
    console.error(error)
  }
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}
</script>

<template>
  <div class="file-manager">
    <div class="manager-header">
      <h2>Your Files</h2>
      <button @click="loadFiles" :disabled="isLoadingFiles || isUploading" class="btn btn-icon" title="Refresh">
        ↻ Refresh
      </button>
    </div>
    
    <div v-if="errorMsg" class="error-banner">
      {{ errorMsg }}
    </div>

    <div 
      class="upload-area" 
      :class="{ 'uploading': isUploading }"
      @drop="handleDrop" 
      @dragover="handleDragOver"
      @click="fileInput?.click()"
    >
      <input 
        type="file" 
        ref="fileInput" 
        style="display: none" 
        @change="handleFileSelect"
      />
      
      <div v-if="!isUploading" class="upload-content">
        <span class="upload-icon">☁️</span>
        <p><strong>Click to upload</strong> or drag and drop</p>
        <p class="upload-hint">Supports any file type</p>
      </div>
      
      <div v-else class="progress-content">
        <p>Uploading... {{ uploadProgress }}%</p>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" :style="{ width: `${uploadProgress}%` }"></div>
        </div>
      </div>
    </div>

    <div class="file-list-container">
      <div v-if="isLoadingFiles && files.length === 0" class="loading-state">
        <div class="spinner"></div>
        <p>Loading files...</p>
      </div>
      
      <div v-else-if="files.length === 0" class="empty-state">
        <p>No files uploaded yet.</p>
      </div>
      
      <table v-else class="file-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Status</th>
            <th>Access Level</th>
            <th>Created At</th>
            <th class="actions-col">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="file in files" :key="file.id" class="file-row">
            <td class="file-name">
              <span class="file-icon">📄</span>
              {{ file.original_name }}
            </td>
            <td>
              <span class="status-badge" :class="file.status.toLowerCase()">
                {{ file.status }}
              </span>
            </td>
            <td>
              <div class="access-info">
                <span title="Set Access Level" class="access-badge set">{{ file.set_access_level }}</span>
                <span class="access-arrow">→</span>
                <span title="Actual Access Level" class="access-badge actual">{{ file.actual_access_level }}</span>
              </div>
            </td>
            <td class="date-col">{{ formatDate(file.created_at) }}</td>
            <td class="actions-col">
              <button 
                class="btn btn-action" 
                @click="triggerDownload(file.id)"
                :disabled="file.status !== 'completed'"
                title="Download"
              >
                ⬇️ Download
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.file-manager {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  width: 100%;
}

.manager-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.manager-header h2 {
  font-size: 1.5rem;
  color: var(--color-heading);
  margin: 0;
}

.btn {
  padding: 0.5rem 1rem;
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.2s ease;
  background-color: white;
  color: #334155;
  border-color: #cbd5e1;
}

.btn:hover:not(:disabled) {
  background-color: #f1f5f9;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-banner {
  background-color: #fef2f2;
  border-left: 4px solid #ef4444;
  color: #991b1b;
  padding: 1rem;
  border-radius: 4px;
  font-size: 0.875rem;
}

.upload-area {
  border: 2px dashed #cbd5e1;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  background-color: #f8fafc;
  cursor: pointer;
  transition: all 0.2s ease;
}

.upload-area:hover:not(.uploading) {
  border-color: #94a3b8;
  background-color: #f1f5f9;
}

.upload-area.uploading {
  cursor: default;
  border-style: solid;
  border-color: #e2e8f0;
}

.upload-icon {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
  display: block;
}

.upload-hint {
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 0.25rem;
}

.progress-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  align-items: center;
}

.progress-bar-bg {
  width: 100%;
  max-width: 300px;
  height: 8px;
  background-color: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background-color: #3b82f6;
  transition: width 0.3s ease;
}

.file-list-container {
  background-color: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.loading-state, .empty-state {
  padding: 3rem;
  text-align: center;
  color: #64748b;
}

.spinner {
  border: 3px solid #f3f3f3;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.file-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.file-table th {
  background-color: #f8fafc;
  padding: 0.75rem 1.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid #e2e8f0;
}

.file-table td {
  padding: 1rem 1.5rem;
  font-size: 0.875rem;
  color: #334155;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: middle;
}

.file-row:last-child td {
  border-bottom: none;
}

.file-row:hover {
  background-color: #f8fafc;
}

.file-name {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 500;
  color: #0f172a;
}

.file-icon {
  font-size: 1.25rem;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  background-color: #f1f5f9;
  color: #475569;
}

.status-badge.active {
  background-color: #dcfce7;
  color: #166534;
}

.status-badge.uploading {
  background-color: #dbeafe;
  color: #1e40af;
}

.access-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.access-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.access-badge.set {
  background-color: #e0e7ff;
  color: #3730a3;
}

.access-badge.actual {
  background-color: #ede9fe;
  color: #5b21b6;
}

.access-arrow {
  color: #94a3b8;
  font-size: 0.875rem;
}

.date-col {
  color: #64748b;
  white-space: nowrap;
}

.actions-col {
  text-align: right;
  width: 120px;
}

.btn-action {
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
}
</style>
