<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuth } from '@clerk/vue'
import { useRouter } from 'vue-router'

const { getToken } = useAuth()
const router = useRouter()

interface UserQuota {
  user_id: string
  allocated_quota_bytes: number
  created_at: string
  updated_at: string
}

const quotas = ref<UserQuota[]>([])
const isLoading = ref(false)
const errorMsg = ref('')

// Form state
const targetUserId = ref('')
const newQuotaMb = ref<number | null>(null)
const isSubmitting = ref(false)
const successMsg = ref('')

const editingId = ref<string | null>(null)
const editQuotaMb = ref<number | null>(null)

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

const setQuota = async () => {
  if (!targetUserId.value) return
  
  isSubmitting.value = true
  errorMsg.value = ''
  successMsg.value = ''
  
  try {
    const token = await getToken.value()
    const quotaBytes = newQuotaMb.value === null || newQuotaMb.value === '' ? null : newQuotaMb.value * 1024 * 1024
    
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
    newQuotaMb.value = null
    
    await fetchQuotas()
  } catch (err: any) {
    errorMsg.value = err.message || 'An error occurred'
  } finally {
    isSubmitting.value = false
  }
}

const startEdit = (q: UserQuota) => {
  editingId.value = q.user_id
  editQuotaMb.value = q.allocated_quota_bytes === null ? null : q.allocated_quota_bytes / (1024 * 1024)
}

const saveEdit = async (userId: string) => {
  isSubmitting.value = true
  errorMsg.value = ''
  successMsg.value = ''
  
  try {
    const token = await getToken.value()
    const quotaBytes = editQuotaMb.value === null || editQuotaMb.value === '' ? null : editQuotaMb.value * 1024 * 1024
    
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
  return new Date(dateString).toLocaleString()
}

onMounted(() => {
  fetchQuotas()
})
</script>

<template>
  <div class="admin-panel">
    <div class="header-section">
      <div class="header-content">
        <div>
          <h1>Admin Control Panel</h1>
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

    <div class="grid-layout">
      <!-- Set Quota Form -->
      <div class="card">
        <h2>Set User Quota</h2>
        <p class="subtitle">Assign a new storage limit to a Clerk User ID.</p>
        
        <form @submit.prevent="setQuota">
          <div class="form-group">
            <label for="userId">Clerk User ID</label>
            <input 
              id="userId" 
              v-model="targetUserId" 
              type="text" 
              required
              placeholder="e.g. user_2Pq..."
            >
          </div>
          
          <div class="form-group">
            <label for="quotaMb">Quota in Megabytes (MB)</label>
            <input 
              id="quotaMb" 
              v-model="newQuotaMb" 
              type="number" 
              min="0"
              placeholder="Leave empty for unlimited"
            >
          </div>
          
          <button type="submit" class="btn btn-primary" :disabled="isSubmitting || !targetUserId">
            {{ isSubmitting ? 'Creating...' : 'Set Quota' }}
          </button>
        </form>
      </div>

      <!-- Quota List -->
      <div class="card">
        <div class="list-header">
          <h2>Configured Quotas</h2>
          <button @click="fetchQuotas" class="btn btn-secondary btn-sm" :disabled="isLoading">
            ↻ Refresh
          </button>
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
                <th>User ID</th>
                <th>Allocated Quota</th>
                <th>Last Updated</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in quotas" :key="q.user_id">
                <td><code class="user-id-badge">{{ q.user_id }}</code></td>
                <td class="font-medium">
                  <div v-if="editingId === q.user_id" class="inline-edit">
                    <input 
                      type="number" 
                      v-model="editQuotaMb" 
                      placeholder="Empty for unlimited" 
                      min="0" 
                      class="small-input" 
                    />
                    <button @click="saveEdit(q.user_id)" class="btn btn-primary btn-sm" :disabled="isSubmitting">Save</button>
                    <button @click="editingId = null" class="btn btn-secondary btn-sm" :disabled="isSubmitting">Cancel</button>
                  </div>
                  <div v-else @click="startEdit(q)" class="clickable-cell" title="Click to edit">
                    {{ q.allocated_quota_bytes === null ? 'Unlimited' : formatBytes(q.allocated_quota_bytes) }}
                    <span class="edit-icon">✎</span>
                  </div>
                </td>
                <td class="date-cell">{{ formatDate(q.updated_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
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

.grid-layout {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 2rem;
}

@media (max-width: 900px) {
  .grid-layout {
    grid-template-columns: 1fr;
  }
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
