<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useAuth } from '@clerk/vue'
import { useRouter } from 'vue-router'
import QuotaInput from '../components/QuotaInput.vue'

const { getToken } = useAuth()
const router = useRouter()

interface UserQuota {
  user_id: string
  username?: string
  allocated_quota_bytes: number
  created_at: string
  updated_at: string
}

const quotas = ref<UserQuota[]>([])
const isLoading = ref(false)
const errorMsg = ref('')

// Form state
const targetUserId = ref('')
const newQuotaBytes = ref<number | null>(null)
const isSubmitting = ref(false)
const successMsg = ref('')

const showSetQuotaModal = ref(false)

const editingId = ref<string | null>(null)
const editQuotaBytes = ref<number | null>(null)

const clusterStorage = ref<{free_bytes: number, total_bytes: number} | null>(null)
const clusterStorageError = ref('')

const totalAllocated = computed(() => {
  return quotas.value.reduce((acc, q) => acc + (q.allocated_quota_bytes || 0), 0)
})

const availableToAllocate = computed(() => {
  if (!clusterStorage.value) return 0
  return Math.max(0, clusterStorage.value.total_bytes - totalAllocated.value)
})

const isStorageLow = computed(() => {
  if (!clusterStorage.value) return false
  return availableToAllocate.value < clusterStorage.value.total_bytes * 0.1
})

const API_URL = 'http://localhost:8000/v1/api/admin/quotas'

const fetchQuotas = async () => {
  isLoading.value = true
  errorMsg.value = ''
  try {
    const token = await getToken.value()
    const response = await fetch(API_URL, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.status === 403) {
      router.push('/dashboard')
      return
    }
    
    if (!response.ok) {
      throw new Error('Failed to fetch quotas')
    }
    quotas.value = await response.json()
  } catch (err: any) {
    errorMsg.value = err.message || 'An error occurred'
  } finally {
    isLoading.value = false
  }
}

const fetchClusterStorage = async () => {
  try {
    const token = await getToken.value()
    const response = await fetch('http://localhost:8000/v1/api/admin/cluster-storage', {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (response.ok) {
      clusterStorage.value = await response.json()
    } else {
      clusterStorageError.value = 'Failed to load cluster storage metrics.'
    }
  } catch (err) {
    clusterStorageError.value = 'Failed to connect to cluster storage API.'
  }
}

const setQuota = async () => {
  if (!targetUserId.value) return
  
  isSubmitting.value = true
  errorMsg.value = ''
  successMsg.value = ''
  
  try {
    const token = await getToken.value()
    if (newQuotaBytes.value === null) {
      throw new Error('Quota cannot be empty/unlimited.')
    }
    const quotaBytes = newQuotaBytes.value
    
    const response = await fetch(`${API_URL}/${targetUserId.value}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        allocated_quota_bytes: quotaBytes
      })
    })
    
    if (!response.ok) {
      if (response.status === 409) {
        throw new Error('Quota for this user already exists. Click the row in the table to edit it.')
      }
      const errData = await response.json().catch(() => ({}))
      throw new Error(errData.detail || 'Failed to create quota')
    }
    
    successMsg.value = `Quota for ${targetUserId.value} successfully created.`
    targetUserId.value = ''
    newQuotaBytes.value = null
    showSetQuotaModal.value = false
    
    await fetchQuotas()
  } catch (err: any) {
    errorMsg.value = err.message || 'An error occurred'
  } finally {
    isSubmitting.value = false
  }
}

const startEdit = (q: UserQuota) => {
  editingId.value = q.user_id
  editQuotaBytes.value = q.allocated_quota_bytes
}

const saveEdit = async (userId: string) => {
  isSubmitting.value = true
  errorMsg.value = ''
  successMsg.value = ''
  
  try {
    const token = await getToken.value()
    if (editQuotaBytes.value === null) {
      throw new Error('Quota cannot be empty/unlimited.')
    }
    const quotaBytes = editQuotaBytes.value
    
    const response = await fetch(`${API_URL}/${userId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        allocated_quota_bytes: quotaBytes
      })
    })
    
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}))
      throw new Error(errData.detail || 'Failed to update quota')
    }
    
    successMsg.value = `Quota for ${userId} successfully updated.`
    editingId.value = null
    
    await fetchQuotas()
  } catch (err: any) {
    errorMsg.value = err.message || 'An error occurred'
  } finally {
    isSubmitting.value = false
  }
}

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  const yyyy = date.getFullYear()
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const min = String(date.getMinutes()).padStart(2, '0')
  return `${yyyy}/${mm}/${dd} ${hh}:${min}`
}

const userSearchQuery = ref('')
const userSearchResults = ref<any[]>([])
const isSearchingUsers = ref(false)
const showUserDropdown = ref(false)
let searchTimeout: any = null

const onSearchInput = () => {
  showUserDropdown.value = true
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(searchUsers, 300)
}

const searchUsers = async () => {
  if (!userSearchQuery.value) {
    userSearchResults.value = []
    isSearchingUsers.value = false
    return
  }
  
  isSearchingUsers.value = true
  try {
    const token = await getToken.value()
    const response = await fetch(`http://localhost:8000/v1/api/admin/users?query=${encodeURIComponent(userSearchQuery.value)}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.ok) {
      userSearchResults.value = await response.json()
    }
  } catch (err) {
    console.error('Failed to search users', err)
  } finally {
    isSearchingUsers.value = false
  }
}

const selectUser = (user: any) => {
  targetUserId.value = user.id
  userSearchQuery.value = user.username || user.email
  showUserDropdown.value = false
}

const clearSelectedUser = () => {
  targetUserId.value = ''
  userSearchQuery.value = ''
  userSearchResults.value = []
}

onMounted(() => {
  fetchQuotas()
  fetchClusterStorage()
  
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement
    if (!target.closest('.relative-group')) {
      showUserDropdown.value = false
    }
  })
})
</script>

<template>
  <div class="admin-panel">
    <div class="header-section">
      <div class="header-content">
        <div>
          <p>Manage B2B storage quotas across the platform.</p>
        </div>
        <router-link to="/dashboard" class="btn btn-secondary">
          Back to Dashboard
        </router-link>
      </div>
    </div>

    <div v-if="errorMsg" class="error-banner">
      {{ errorMsg }}
    </div>
    <div v-if="successMsg" class="success-banner">
      {{ successMsg }}
    </div>

    <div v-if="clusterStorage" class="storage-overview-card card">
      <h2>Cluster Storage Overview</h2>
      
      <div v-if="isStorageLow" class="warning-banner">
        ⚠️ Warning: Less than 10% of physical cluster space is available for allocation.
      </div>
      
      <div class="storage-stats-grid">
        <div class="stat-box">
          <span class="stat-label">Total Cluster Capacity</span>
          <span class="stat-value">{{ formatBytes(clusterStorage.total_bytes) }}</span>
        </div>
        <div class="stat-box">
          <span class="stat-label">Total Allocated Quotas</span>
          <span class="stat-value">{{ formatBytes(totalAllocated) }}</span>
        </div>
        <div class="stat-box" :class="{'low-storage': isStorageLow}">
          <span class="stat-label">Available to Allocate</span>
          <span class="stat-value">{{ formatBytes(availableToAllocate) }}</span>
        </div>
      </div>
      
      <div class="progress-bar-container">
        <div 
          class="progress-bar-fill" 
          :class="{'progress-bar-warning': isStorageLow}"
          :style="{width: Math.min(100, (totalAllocated / clusterStorage.total_bytes) * 100) + '%'}"
        ></div>
      </div>
    </div>

    <!-- Modals -->
    <!-- Set Quota Modal -->
    <div v-if="showSetQuotaModal" class="modal-overlay" @click.self="showSetQuotaModal = false">
      <div class="modal-content card">
        <div class="modal-header">
          <h2>Set User Quota</h2>
          <button @click="showSetQuotaModal = false" class="close-btn" title="Close">&times;</button>
        </div>
        <p class="subtitle">Assign a new storage limit to a Clerk User ID.</p>
        
        <form @submit.prevent="setQuota">
          <div class="form-group relative-group">
            <label for="userSearch">Clerk User</label>
            <input 
              id="userSearch" 
              v-model="userSearchQuery" 
              @input="onSearchInput"
              @focus="showUserDropdown = true"
              type="text" 
              placeholder="Search by email or name..."
              autocomplete="off"
            >
            <div v-if="showUserDropdown && (isSearchingUsers || userSearchResults.length > 0 || userSearchQuery)" class="dropdown-menu">
              <div v-if="isSearchingUsers" class="dropdown-item empty-item">Searching...</div>
              <div v-else-if="userSearchResults.length === 0" class="dropdown-item empty-item">No users found</div>
              <div v-else 
                v-for="user in userSearchResults" 
                :key="user.id" 
                @click="selectUser(user)"
                class="dropdown-item"
              >
                <div class="user-info">
                  <span class="user-email">{{ user.username || 'No username' }}</span>
                  <span class="user-name">{{ user.email }} <template v-if="user.first_name || user.last_name">({{ user.first_name }} {{ user.last_name }})</template></span>
                </div>
                <code class="user-id-badge small-badge">{{ user.id }}</code>
              </div>
            </div>
            
            <div v-if="targetUserId" class="selected-user-info">
              Selected: <code class="user-id-badge">{{ targetUserId }}</code> 
              <button type="button" @click="clearSelectedUser" class="btn-text-danger">Clear</button>
            </div>
          </div>
          
          <div class="form-group">
            <label>Quota Size</label>
            <QuotaInput v-model="newQuotaBytes" :maxBytes="availableToAllocate" required />
          </div>
          
          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="showSetQuotaModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="isSubmitting || !targetUserId || newQuotaBytes === null">
              {{ isSubmitting ? 'Creating...' : 'Set Quota' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Main Content -->
    <div class="card">
      <div class="list-header">
        <h2>Configured Quotas</h2>
        <div class="header-actions">
          <button @click="fetchQuotas" class="btn btn-secondary btn-sm" :disabled="isLoading">
            ↻ Refresh
          </button>
          <button @click="showSetQuotaModal = true" class="btn btn-primary btn-sm">
            + Set User Quota
          </button>
        </div>
      </div>
        
        <div v-if="isLoading" class="loading-state">
          Loading quotas...
        </div>
        
        <div v-else-if="quotas.length === 0" class="empty-state">
          No quotas configured yet.
        </div>
        
        <div v-else class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Allocated Quota</th>
                <th>Last Updated</th>
                <th style="width: 150px"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in quotas" :key="q.user_id">
                <td>
                  <div class="user-info-cell">
                    <span class="user-username">{{ q.username || 'No username' }}</span>
                    <code class="user-id-badge small-badge">{{ q.user_id }}</code>
                  </div>
                </td>
                <td class="font-medium">
                  <div v-if="editingId === q.user_id" class="inline-edit">
                    <QuotaInput v-model="editQuotaBytes" :maxBytes="availableToAllocate + (q.allocated_quota_bytes || 0)" compact required />
                  </div>
                  <div v-else>
                    {{ q.allocated_quota_bytes === null ? 'Unlimited' : formatBytes(q.allocated_quota_bytes) }}
                  </div>
                </td>
                <td class="date-cell">{{ formatDate(q.updated_at) }}</td>
                <td>
                  <div v-if="editingId === q.user_id" style="display: flex; gap: 0.5rem;">
                    <button @click="saveEdit(q.user_id)" class="btn btn-primary btn-sm" :disabled="isSubmitting">Save</button>
                    <button @click="editingId = null" class="btn btn-secondary btn-sm" :disabled="isSubmitting">Cancel</button>
                  </div>
                  <div v-else>
                    <button @click="startEdit(q)" class="btn btn-secondary btn-sm">✎ Edit</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
  </div>
</template>

<style scoped>
.admin-panel {
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
}

.header-section {
  margin-bottom: 2rem;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.header-section h1 {
  font-size: 2rem;
  color: var(--color-heading);
  margin-bottom: 0.5rem;
}

.header-section p {
  color: var(--color-text-light, #64748b);
  font-size: 1.1rem;
}

.error-banner {
  background-color: #fef2f2;
  border-left: 4px solid #ef4444;
  color: #991b1b;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 2rem;
}

.success-banner {
  background-color: #f0fdf4;
  border-left: 4px solid #22c55e;
  color: #166534;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 2rem;
}

.header-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.modal-header h2 {
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  line-height: 1;
  color: var(--color-text-light, #64748b);
  cursor: pointer;
  padding: 0;
  margin-top: -0.25rem;
}

.close-btn:hover {
  color: var(--color-heading);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
}

.storage-overview-card {
  margin-bottom: 2rem;
}

.warning-banner {
  background-color: #fffbeb;
  border-left: 4px solid #f59e0b;
  color: #b45309;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
  font-weight: 500;
}

.storage-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

@media (max-width: 768px) {
  .storage-stats-grid {
    grid-template-columns: 1fr;
  }
}

.stat-box {
  background-color: var(--color-background-soft);
  padding: 1.25rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
}

.stat-box.low-storage .stat-value {
  color: #ef4444;
}

.stat-label {
  font-size: 0.9rem;
  color: var(--color-text-light, #64748b);
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--color-heading);
}

.progress-bar-container {
  height: 12px;
  background-color: var(--color-background-soft);
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.progress-bar-fill {
  height: 100%;
  background-color: #3b82f6;
  transition: width 0.5s ease;
}

.progress-bar-warning {
  background-color: #ef4444;
}

.card {
  background-color: var(--color-background);
  border-radius: 8px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  padding: 2rem;
  border: 1px solid var(--color-border);
}

.card h2 {
  font-size: 1.5rem;
  color: var(--color-heading);
  margin-bottom: 0.5rem;
}

.subtitle {
  color: var(--color-text-light, #64748b);
  margin-bottom: 1.5rem;
  font-size: 0.95rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  font-weight: 500;
  margin-bottom: 0.5rem;
  color: var(--color-heading);
}

.relative-group {
  position: relative;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  margin-top: 0.25rem;
  max-height: 250px;
  overflow-y: auto;
  z-index: 10;
}

.dropdown-item {
  padding: 0.75rem 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  border-bottom: 1px solid var(--color-border);
}

.dropdown-item:last-child {
  border-bottom: none;
}

.dropdown-item:hover {
  background-color: var(--color-background-mute, #f1f5f9);
}

.empty-item {
  color: var(--color-text-light, #64748b);
  cursor: default;
}

.empty-item:hover {
  background-color: transparent;
}

.user-info {
  display: flex;
  flex-direction: column;
}

.user-email {
  font-weight: 500;
  color: var(--color-heading);
}

.user-name {
  font-size: 0.85rem;
  color: var(--color-text-light, #64748b);
}

.small-badge {
  font-size: 0.75rem;
  padding: 0.15rem 0.35rem;
}

.selected-user-info {
  margin-top: 0.5rem;
  font-size: 0.9rem;
  color: var(--color-text-light, #64748b);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-text-danger {
  background: none;
  border: none;
  color: #ef4444;
  cursor: pointer;
  font-size: 0.85rem;
  padding: 0;
  text-decoration: underline;
}

.btn-text-danger:hover {
  color: #b91c1c;
}

input[type="text"],
input[type="number"] {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background-color: var(--color-background-soft);
  color: var(--color-text);
  font-size: 1rem;
  transition: border-color 0.2s, box-shadow 0.2s;
}

input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.list-header h2 {
  margin-bottom: 0;
}

.empty-state, .loading-state {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--color-text-light, #64748b);
  background-color: var(--color-background-soft);
  border-radius: 8px;
  border: 1px dashed var(--color-border);
}

.table-container {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 1rem;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}

.data-table th {
  font-weight: 600;
  color: var(--color-heading);
  background-color: var(--color-background-soft);
}

.data-table tr:hover td {
  background-color: var(--color-background-mute);
}

.font-medium {
  font-weight: 500;
  color: var(--color-heading);
}

.user-info-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
}

.user-username {
  font-weight: 500;
  color: var(--color-heading);
}

.user-id-badge {
  background-color: #e2e8f0;
  color: #334155;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.85rem;
}

.date-cell {
  color: var(--color-text-light, #64748b);
  font-size: 0.85rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  transition: all 0.2s;
  font-family: inherit;
  text-decoration: none;
  display: inline-block;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background-color: #0f172a;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #334155;
  transform: translateY(-1px);
}

.btn-secondary {
  background-color: transparent;
  border-color: #cbd5e1;
  color: #334155;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #f1f5f9;
}

.btn-sm {
  padding: 0.35rem 0.75rem;
  font-size: 0.85rem;
}

.inline-edit {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.small-input {
  padding: 0.35rem 0.5rem !important;
  font-size: 0.9rem !important;
  border-radius: 4px !important;
  width: 150px !important;
}

.clickable-cell {
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: background-color 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.clickable-cell:hover {
  background-color: var(--color-background-mute, #f1f5f9);
}

.edit-icon {
  opacity: 0;
  color: #94a3b8;
  font-size: 0.9rem;
  transition: opacity 0.2s;
}

.clickable-cell:hover .edit-icon {
  opacity: 1;
}
</style>
