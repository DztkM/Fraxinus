<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useAuth } from '@clerk/vue'
import QuotaInput from '../components/QuotaInput.vue'

const { getToken } = useAuth()

interface ApiKeyInfo {
  id: string
  name: string
  created_at: string
}

interface Namespace {
  id: string
  name: string
  quota_bytes: number | null
  used_bytes: number
  files_count: number
  created_at: string
  updated_at: string
  api_keys: ApiKeyInfo[]
}

interface QuotaInfo {
  allocated: number | null
  used: number
  is_admin: boolean
}

const namespaces = ref<Namespace[]>([])
const quota = ref<QuotaInfo | null>(null)
const isLoading = ref(false)
const errorMsg = ref('')

// Form state
const newName = ref('')
const newQuota = ref<number | null>(null)
const isCreating = ref(false)

const processingIds = ref<Record<string, boolean>>({})
const newKeyNames = ref<Record<string, string>>({})

// Result state
const createdApiKey = ref('')
const createdNamespace = ref<Namespace | null>(null)

const API_URL = 'http://localhost:8000/v1/api/dashboard/namespaces'
const API_KEY_URL = 'http://localhost:8000/v1/api/dashboard/api-key'

const fetchNamespaces = async () => {
  isLoading.value = true
  errorMsg.value = ''
  try {
    const token = await getToken.value()
    const response = await fetch(API_URL, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!response.ok) {
      throw new Error('Failed to fetch namespaces')
    }
    namespaces.value = await response.json()
  } catch (err: any) {
    errorMsg.value = err.message || 'An error occurred'
  } finally {
    isLoading.value = false
  }
}

const fetchQuota = async () => {
  try {
    const token = await getToken.value()
    const response = await fetch('http://localhost:8000/v1/api/dashboard/quota', {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (response.ok) {
      quota.value = await response.json()
    }
  } catch (err) {
    console.error('Failed to fetch quota', err)
  }
}

const getQuotaPercentage = () => {
  if (!quota.value || !quota.value.allocated) return 0;
  return Math.min(100, Math.round((quota.value.used / quota.value.allocated) * 100));
}

const availableNamespaceQuota = computed(() => {
  if (!quota.value || quota.value.allocated === null) return null;
  return Math.max(0, quota.value.allocated - quota.value.used);
})

const createNamespace = async () => {
  if (!newName.value) return
  isCreating.value = true
  errorMsg.value = ''
  createdApiKey.value = ''
  createdNamespace.value = null
  
  try {
    const token = await getToken.value()
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        name: newName.value,
        quota_bytes: newQuota.value
      })
    })
    
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}))
      throw new Error(errData.detail || 'Failed to create namespace')
    }
    
    const data = await response.json()
    createdNamespace.value = {
      id: data.id,
      name: data.name,
      quota_bytes: data.quota_bytes,
      used_bytes: data.used_bytes,
      files_count: data.files_count,
      created_at: data.created_at,
      updated_at: data.updated_at,
      api_keys: []
    }
    
    // Add to list and reset form
    namespaces.value.push(createdNamespace.value)
    newName.value = ''
    newQuota.value = null
  } catch (err: any) {
    errorMsg.value = err.message || 'An error occurred'
  } finally {
    isCreating.value = false
  }
}

const copyApiKey = async () => {
  if (!createdApiKey.value) return
  try {
    await navigator.clipboard.writeText(createdApiKey.value)
    alert('API Key copied to clipboard!')
  } catch (err) {
    console.error('Failed to copy', err)
  }
}

const formatBytes = (bytes: number | null) => {
  if (bytes === null) return 'Unlimited'
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString()
}

const createKey = async (nsId: string) => {
  const name = newKeyNames.value[nsId]
  if (!name) return
  
  processingIds.value[nsId] = true
  errorMsg.value = ''
  createdApiKey.value = ''
  
  try {
    const token = await getToken.value()
    const response = await fetch(API_KEY_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ name, namespace_id: nsId })
    })
    
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}))
      throw new Error(errData.detail || 'Failed to create API key')
    }
    
    const data = await response.json()
    createdApiKey.value = data.api_key
    
    // Update the namespace state locally
    const ns = namespaces.value.find(n => n.id === nsId)
    if (ns) {
      ns.api_keys.push({ id: data.id, name: data.name, created_at: data.created_at })
    }
    
    newKeyNames.value[nsId] = ''
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (err: any) {
    errorMsg.value = err.message || 'An error occurred'
  } finally {
    processingIds.value[nsId] = false
  }
}

const deleteKey = async (nsId: string, keyId: string) => {
  if (!confirm('Are you sure you want to delete this API key? Access using this key will be revoked immediately.')) return
  
  processingIds.value[keyId] = true
  errorMsg.value = ''
  
  try {
    const token = await getToken.value()
    const response = await fetch(`${API_KEY_URL}/${keyId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}))
      throw new Error(errData.detail || 'Failed to delete API key')
    }
    
    // Update the namespace state locally
    const ns = namespaces.value.find(n => n.id === nsId)
    if (ns) {
      ns.api_keys = ns.api_keys.filter(k => k.id !== keyId)
    }
  } catch (err: any) {
    errorMsg.value = err.message || 'An error occurred'
  } finally {
    processingIds.value[keyId] = false
  }
}

onMounted(() => {
  fetchNamespaces()
  fetchQuota()
})
</script>

<template>
  <div class="admin-panel">
    <div class="header-section">
      <div class="header-content">
        <div>
          <h1>B2B Integration</h1>
          <p>Manage your namespaces and API keys for backend-to-backend integration.</p>
        </div>
        <router-link v-if="quota?.is_admin" to="/admin" class="btn btn-primary admin-link">
          Admin Panel
        </router-link>
      </div>
      
      <div class="quota-container" v-if="quota">
        <div class="quota-header">
          <h3>Storage Quota</h3>
          <span>{{ formatBytes(quota.used) }} / {{ quota.allocated === null ? 'Unlimited' : formatBytes(quota.allocated) }}</span>
        </div>
        <div class="progress-bar" v-if="quota.allocated !== null">
          <div 
            class="progress" 
            :style="{ width: getQuotaPercentage() + '%' }" 
            :class="{ 'warning': getQuotaPercentage() > 80, 'danger': getQuotaPercentage() > 95 }"
          ></div>
        </div>
        <p v-if="quota.allocated === 0" class="warning-text" style="margin-top: 0.5rem;">
          No quota allocated. You cannot create namespaces or upload files. Please contact the administrator.
        </p>
      </div>
    </div>

    <div v-if="errorMsg" class="error-banner">
      {{ errorMsg }}
    </div>

    <div class="grid-layout">
      <!-- Create Section -->
      <div class="card create-card">
        <h2>Create Namespace</h2>
        <p class="subtitle">Create a new isolated environment for your integration.</p>
        
        <form @submit.prevent="createNamespace" class="create-form">
          <div class="form-group">
            <label for="name">Namespace Name</label>
            <input 
              id="name" 
              v-model="newName" 
              type="text" 
              required
              placeholder="e.g. Production App"
            >
          </div>
          
          <div class="form-group">
            <label>Storage Quota</label>
            <QuotaInput v-model="newQuota" :maxBytes="availableNamespaceQuota" required />
          </div>
          
          <button type="submit" class="btn btn-primary" :disabled="isCreating || !newName || newQuota === null || quota?.allocated === 0">
            {{ isCreating ? 'Creating...' : 'Create Namespace' }}
          </button>
        </form>

        <div v-if="createdApiKey" class="api-key-result">
          <div class="success-header">
            <span class="icon">✅</span>
            <h3>API Key Ready!</h3>
          </div>
          <p class="warning-text">
            <strong>IMPORTANT:</strong> Copy this API key now. You won't be able to see it again!
          </p>
          <div class="key-box">
            <code>{{ createdApiKey }}</code>
            <button @click="copyApiKey" class="btn btn-secondary btn-sm" title="Copy API Key">
              Copy
            </button>
          </div>
        </div>
      </div>

      <!-- List Section -->
      <div class="card list-card">
        <div class="list-header">
          <h2>Your Namespaces</h2>
          <button @click="fetchNamespaces" class="btn btn-secondary btn-sm" :disabled="isLoading">
            ↻ Refresh
          </button>
        </div>
        
        <div v-if="isLoading" class="loading-state">
          Loading namespaces...
        </div>
        
        <div v-else-if="namespaces.length === 0" class="empty-state">
          No namespaces found. Create one to get started.
        </div>
        
        <div v-else class="table-container">
          <table class="namespaces-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Limit</th>
                <th>Used</th>
                <th>Files</th>
                <th>Created At</th>
                <th>API Keys</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="ns in namespaces" :key="ns.id">
                <td>
                  <div class="font-medium">{{ ns.name }}</div>
                  <div class="date-cell">Created: {{ formatDate(ns.created_at) }}</div>
                </td>
                <td>{{ formatBytes(ns.quota_bytes) }}</td>
                <td>{{ formatBytes(ns.used_bytes) }}</td>
                <td>{{ ns.files_count }}</td>
                <td>
                  <div class="keys-container">
                    <div v-if="ns.api_keys.length > 0" class="keys-list">
                      <div v-for="key in ns.api_keys" :key="key.id" class="key-item">
                        <div class="key-info">
                          <span class="key-name">{{ key.name }}</span>
                          <span class="key-date">{{ formatDate(key.created_at) }}</span>
                        </div>
                        <button 
                          @click="deleteKey(ns.id, key.id)" 
                          class="btn btn-danger btn-sm" 
                          :disabled="processingIds[key.id]"
                          title="Revoke active API Key"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                    <div v-else class="no-keys-text">
                      No keys yet
                    </div>
                    <div class="add-key-form">
                      <input 
                        type="text" 
                        v-model="newKeyNames[ns.id]" 
                        placeholder="New key name" 
                        class="small-input"
                        @keyup.enter="createKey(ns.id)"
                      />
                      <button 
                        @click="createKey(ns.id)" 
                        class="btn btn-primary btn-sm" 
                        :disabled="processingIds[ns.id] || !newKeyNames[ns.id]"
                      >
                        Add
                      </button>
                    </div>
                  </div>
                </td>
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
  margin-bottom: 1.5rem;
}

.admin-link {
  text-decoration: none;
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

.quota-container {
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.quota-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.quota-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--color-heading);
}

.quota-header span {
  font-weight: 500;
  color: var(--color-heading);
}

.progress-bar {
  width: 100%;
  height: 12px;
  background-color: var(--color-background-mute);
  border-radius: 6px;
  overflow: hidden;
}

.progress {
  height: 100%;
  background-color: #10b981;
  transition: width 0.3s ease, background-color 0.3s ease;
}

.progress.warning {
  background-color: #f59e0b;
}

.progress.danger {
  background-color: #ef4444;
}

.error-banner {
  background-color: #fef2f2;
  border-left: 4px solid #ef4444;
  color: #991b1b;
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

.optional {
  font-weight: normal;
  color: #94a3b8;
  font-size: 0.85rem;
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

.api-key-result {
  margin-top: 2rem;
  padding: 1.5rem;
  background-color: #f0fdfa;
  border: 1px solid #5eead4;
  border-radius: 8px;
}

.success-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.success-header h3 {
  color: #0f766e;
  margin: 0;
  font-size: 1.2rem;
}

.warning-text {
  color: #991b1b;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.key-box {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #1e293b;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  gap: 1rem;
}

.key-box code {
  color: #a7f3d0;
  font-family: monospace;
  word-break: break-all;
  font-size: 1.1rem;
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

.namespaces-table {
  width: 100%;
  border-collapse: collapse;
}

.namespaces-table th,
.namespaces-table td {
  padding: 1rem;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
  vertical-align: top;
}

.namespaces-table th {
  font-weight: 600;
  color: var(--color-heading);
  background-color: var(--color-background-soft);
}

.namespaces-table tr:hover td {
  background-color: var(--color-background-mute);
}

.font-medium {
  font-weight: 500;
  color: var(--color-heading);
  margin-bottom: 0.25rem;
}

.date-cell {
  color: var(--color-text-light, #64748b);
  font-size: 0.85rem;
}

.keys-container {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.keys-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.key-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background-color: var(--color-background-soft);
  border-radius: 6px;
  border: 1px solid var(--color-border);
}

.key-info {
  display: flex;
  flex-direction: column;
}

.key-name {
  font-weight: 500;
  font-size: 0.95rem;
  color: var(--color-heading);
}

.key-date {
  font-size: 0.8rem;
  color: var(--color-text-light, #64748b);
}

.no-keys-text {
  font-size: 0.9rem;
  color: var(--color-text-light, #64748b);
  font-style: italic;
  padding: 0.5rem 0;
}

.add-key-form {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.small-input {
  padding: 0.35rem 0.5rem !important;
  font-size: 0.9rem !important;
  border-radius: 4px !important;
  flex: 1;
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

.btn-danger {
  background-color: transparent;
  border-color: #fca5a5;
  color: #ef4444;
}

.btn-danger:hover:not(:disabled) {
  background-color: #fef2f2;
}

.btn-sm {
  padding: 0.35rem 0.75rem;
  font-size: 0.85rem;
  width: auto;
}
</style>
