<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useAuth } from '@clerk/vue'
import { 
  fetchFiles, 
  uploadFile, 
  downloadFile,
  fetchFolderContents,
  createFolder,
  type FileItem,
  type FolderItem 
} from '../services/api'

const { getToken, isSignedIn } = useAuth()

type Tab = 'explorer' | 'all'
const activeTab = ref<Tab>('explorer')

// All files state
const allFiles = ref<FileItem[]>([])
const isLoadingAllFiles = ref(false)

// Explorer state
const explorerFolders = ref<FolderItem[]>([])
const explorerFiles = ref<FileItem[]>([])
const isLoadingExplorer = ref(false)
const currentFolderId = ref<string>('root')
const breadcrumbs = ref<{ id: string, name: string }[]>([
  { id: 'root', name: 'Root' }
])

// Create folder state
const isCreatingFolder = ref(false)
const newFolderName = ref('')

const errorMsg = ref<string | null>(null)

// Upload state
const isUploading = ref(false)
const uploadProgress = ref(0)
const fileInput = ref<HTMLInputElement | null>(null)

const loadAllFiles = async () => {
  if (!isSignedIn.value) return
  isLoadingAllFiles.value = true
  errorMsg.value = null
  
  try {
    const token = await getToken.value()
    if (!token) throw new Error("No token available")
    allFiles.value = await fetchFiles(token)
  } catch (error: any) {
    errorMsg.value = `Failed to load files: ${error.message}`
    console.error(error)
  } finally {
    isLoadingAllFiles.value = false
  }
}

const loadExplorer = async () => {
  if (!isSignedIn.value) return
  isLoadingExplorer.value = true
  errorMsg.value = null
  
  try {
    const token = await getToken.value()
    if (!token) throw new Error("No token available")
    
    const contents = await fetchFolderContents(token, currentFolderId.value)
    explorerFolders.value = contents.folders
    explorerFiles.value = contents.files
  } catch (error: any) {
    errorMsg.value = `Failed to load folder: ${error.message}`
    console.error(error)
  } finally {
    isLoadingExplorer.value = false
  }
}

const handleTabChange = (tab: Tab) => {
  activeTab.value = tab
  if (tab === 'all') {
    loadAllFiles()
  } else {
    loadExplorer()
  }
}

const navigateToFolder = (folderId: string, folderName: string) => {
  currentFolderId.value = folderId
  breadcrumbs.value.push({ id: folderId, name: folderName })
  loadExplorer()
}

const navigateToBreadcrumb = (index: number) => {
  if (index === breadcrumbs.value.length - 1) return // Already there
  const target = breadcrumbs.value[index]
  if (!target) return
  breadcrumbs.value = breadcrumbs.value.slice(0, index + 1)
  currentFolderId.value = target.id
  loadExplorer()
}

const handleCreateFolder = async () => {
  if (!newFolderName.value.trim()) {
    isCreatingFolder.value = false
    return
  }
  
  errorMsg.value = null
  try {
    const token = await getToken.value()
    if (!token) throw new Error("No token available")
    
    await createFolder(token, newFolderName.value.trim(), currentFolderId.value)
    newFolderName.value = ''
    isCreatingFolder.value = false
    await loadExplorer()
  } catch (error: any) {
    errorMsg.value = `Failed to create folder: ${error.message}`
    console.error(error)
  }
}

onMounted(() => {
  loadExplorer()
})

const handleFileSelect = async (event: Event) => {
  const target = event.target as HTMLInputElement
  if (!target.files || target.files.length === 0) return
  
  const file = target.files.item(0)
  if (!file) return
  await performUpload(file)
  
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
    
    const targetFolderId = activeTab.value === 'explorer' ? currentFolderId.value : 'root'
    
    await uploadFile(token, file, (progress) => {
      uploadProgress.value = progress
    }, targetFolderId)
    
    if (activeTab.value === 'all') {
      await loadAllFiles()
    } else {
      await loadExplorer()
    }
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
      <h2>Your Storage</h2>
      <div class="tabs">
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'explorer' }" 
          @click="handleTabChange('explorer')"
        >
          Explorer
        </button>
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'all' }" 
          @click="handleTabChange('all')"
        >
          All Uploads
        </button>
      </div>
      <button 
        @click="activeTab === 'all' ? loadAllFiles() : loadExplorer()" 
        :disabled="(activeTab === 'all' ? isLoadingAllFiles : isLoadingExplorer) || isUploading" 
        class="btn btn-icon" 
        title="Refresh"
      >
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
        <p class="upload-hint">
          Uploading to: {{ activeTab === 'explorer' ? breadcrumbs[breadcrumbs.length - 1]?.name : 'Root (All Files view)' }}
        </p>
      </div>
      
      <div v-else class="progress-content">
        <p>Uploading... {{ uploadProgress }}%</p>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" :style="{ width: `${uploadProgress}%` }"></div>
        </div>
      </div>
    </div>

    <!-- EXPLORER TAB -->
    <div v-if="activeTab === 'explorer'" class="file-list-container">
      
      <div class="explorer-toolbar">
        <div class="breadcrumbs">
          <span v-for="(crumb, index) in breadcrumbs" :key="crumb.id" class="breadcrumb-item">
            <a href="#" @click.prevent="navigateToBreadcrumb(index)">{{ crumb.name }}</a>
            <span v-if="index < breadcrumbs.length - 1" class="separator">/</span>
          </span>
        </div>
        
        <div class="folder-actions">
          <div v-if="isCreatingFolder" class="create-folder-inline">
            <input 
              v-model="newFolderName" 
              @keyup.enter="handleCreateFolder"
              @keyup.esc="isCreatingFolder = false"
              type="text" 
              placeholder="Folder name" 
              class="input-text"
              autofocus
            />
            <button @click="handleCreateFolder" class="btn btn-primary btn-sm">Create</button>
            <button @click="isCreatingFolder = false; newFolderName = ''" class="btn btn-secondary btn-sm">Cancel</button>
          </div>
          <button v-else @click="isCreatingFolder = true" class="btn btn-secondary btn-sm">
            + New Folder
          </button>
        </div>
      </div>

      <div v-if="isLoadingExplorer && explorerFolders.length === 0 && explorerFiles.length === 0" class="loading-state">
        <div class="spinner"></div>
        <p>Loading folder...</p>
      </div>
      
      <div v-else-if="explorerFolders.length === 0 && explorerFiles.length === 0" class="empty-state">
        <p>This folder is empty.</p>
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
          <!-- Folders -->
          <tr v-for="folder in explorerFolders" :key="'dir-'+folder.id" class="file-row folder-row" @click="navigateToFolder(folder.id, folder.name)">
            <td class="file-name">
              <span class="file-icon folder-icon">📁</span>
              {{ folder.name }}
            </td>
            <td><span class="status-badge active">Directory</span></td>
            <td>
              <div class="access-info">
                <span title="Set Access Level" class="access-badge set">{{ folder.set_access_level }}</span>
                <span class="access-arrow">→</span>
                <span title="Actual Access Level" class="access-badge actual">{{ folder.actual_access_level }}</span>
              </div>
            </td>
            <td class="date-col">{{ formatDate(folder.created_at) }}</td>
            <td class="actions-col"></td>
          </tr>
          
          <!-- Files -->
          <tr v-for="file in explorerFiles" :key="'file-'+file.id" class="file-row">
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
                @click.stop="triggerDownload(file.id)"
                :disabled="file.status !== 'completed'"
                title="Download"
              >
                ⬇️
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ALL UPLOADS TAB -->
    <div v-if="activeTab === 'all'" class="file-list-container">
      <div class="explorer-toolbar">
        <h3>All Files (Flat View)</h3>
      </div>

      <div v-if="isLoadingAllFiles && allFiles.length === 0" class="loading-state">
        <div class="spinner"></div>
        <p>Loading files...</p>
      </div>
      
      <div v-else-if="allFiles.length === 0" class="empty-state">
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
          <tr v-for="file in allFiles" :key="file.id" class="file-row">
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
                ⬇️
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

.tabs {
  display: flex;
  gap: 0.5rem;
  background-color: #e2e8f0;
  padding: 0.25rem;
  border-radius: 8px;
}

.tab-btn {
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn.active {
  background: white;
  color: #0f172a;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.tab-btn:hover:not(.active) {
  color: #334155;
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

.btn-primary {
  background-color: #0f172a;
  color: white;
  border-color: #0f172a;
}
.btn-primary:hover:not(:disabled) {
  background-color: #334155;
}
.btn-secondary {
  background-color: transparent;
}
.btn-sm {
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
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

.explorer-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background-color: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.explorer-toolbar h3 {
  margin: 0;
  font-size: 1rem;
  color: #334155;
  font-weight: 600;
}

.breadcrumbs {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #64748b;
}

.breadcrumb-item a {
  color: #3b82f6;
  text-decoration: none;
}
.breadcrumb-item a:hover {
  text-decoration: underline;
}
.separator {
  color: #cbd5e1;
}

.folder-actions {
  display: flex;
  align-items: center;
}

.create-folder-inline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.input-text {
  padding: 0.25rem 0.5rem;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 0.75rem;
  outline: none;
}
.input-text:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 1px #3b82f6;
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

.file-row {
  transition: background-color 0.15s;
}
.file-row:last-child td {
  border-bottom: none;
}

.file-row:hover {
  background-color: #f1f5f9;
}

.folder-row {
  cursor: pointer;
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

.status-badge.active,
.status-badge.completed {
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
  width: 80px;
}

.btn-action {
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
}
</style>
