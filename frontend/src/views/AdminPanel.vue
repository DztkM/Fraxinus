<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuth } from '@clerk/vue'

const { getToken } = useAuth()

interface Namespace {
  id: string
  name: string
  storage_quota_bytes: number | null
  created_at: string
  updated_at: string
}

const namespaces = ref<Namespace[]>([])
const isLoading = ref(false)
const errorMsg = ref('')

// Form state
const newName = ref('')
const newQuota = ref<number | null>(null)
const isCreating = ref(false)

// Result state
const createdApiKey = ref('')
const createdNamespace = ref<Namespace | null>(null)

const API_URL = 'http://localhost:8000/v1/api/admin/namespaces'

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
        storage_quota_bytes: newQuota.value
      })
    })
    
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}))
      throw new Error(errData.detail || 'Failed to create namespace')
    }
    
    const data = await response.json()
    createdApiKey.value = data.api_key
    createdNamespace.value = {
      id: data.id,
      name: data.name,
      storage_quota_bytes: data.storage_quota_bytes,
      created_at: data.created_at,
      updated_at: data.updated_at
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

onMounted(() => {
  fetchNamespaces()
})
</script>

<template>
  <div class="admin-panel">
    <div class="header-section">
      <h1>B2B Integration</h1>
      <p>Manage your namespaces and API keys for backend-to-backend integration.</p>
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
            <label for="quota">Storage Quota (Bytes) <span class="optional">(Optional)</span></label>
            <input 
              id="quota" 
              v-model="newQuota" 
              type="number" 
              min="0"
              placeholder="Leave empty for unlimited"
            >
          </div>
          
          <button type="submit" class="btn btn-primary" :disabled="isCreating || !newName">
            {{ isCreating ? 'Creating...' : 'Create Namespace' }}
          </button>
        </form>

        <div v-if="createdApiKey" class="api-key-result">
          <div class="success-header">
            <span class="icon">✅</span>
            <h3>Namespace Created!</h3>
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
                <th>Storage Quota</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="ns in namespaces" :key="ns.id">
                <td class="font-medium">{{ ns.name }}</td>
                <td>{{ formatBytes(ns.storage_quota_bytes) }}</td>
                <td class="date-cell">{{ formatDate(ns.created_at) }}</td>
                <td>
                  <div class="action-buttons">
                    <button class="btn btn-secondary btn-sm" disabled title="Manage API Keys (Coming soon)">
                      Keys
                    </button>
                    <button class="btn btn-danger btn-sm" disabled title="Delete Namespace (Coming soon)">
                      Delete
                    </button>
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
}

.date-cell {
  color: var(--color-text-light, #64748b);
  font-size: 0.9rem;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
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
  width: 100%;
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
