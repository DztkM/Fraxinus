<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth, SignInButton, SignUpButton, Show, UserButton } from '@clerk/vue'
import { downloadFile } from '../services/api'

const route = useRoute()
const router = useRouter()
const { getToken, isSignedIn } = useAuth()

const fileId = route.params.id as string
const status = ref<'initializing' | 'downloading' | 'success' | 'error'>('initializing')
const errorMsg = ref<string | null>(null)

const initiateDownload = async () => {
  if (!isSignedIn.value) return
  
  status.value = 'downloading'
  try {
    const token = await getToken.value()
    if (!token) throw new Error("No token available")
    
    await downloadFile(token, fileId)
    status.value = 'success'
  } catch (error: any) {
    status.value = 'error'
    errorMsg.value = error.message || 'Failed to download file'
    console.error(error)
  }
}

onMounted(() => {
  // We need to wait for clerk to initialize. 
  // We can watch for isSignedIn or just attempt if it's already true.
  if (isSignedIn.value) {
    initiateDownload()
  }
})

// Also trigger download if the user signs in while on this page
import { watch } from 'vue'
watch(isSignedIn, (newVal) => {
  if (newVal && status.value === 'initializing') {
    initiateDownload()
  }
})

const goHome = () => {
  router.push({ name: 'home' })
}
</script>

<template>
  <div class="download-page">
    <header class="app-header">
      <div class="logo">Fraxinus Storage</div>
      <div class="auth-controls">
        <Show when="signed-out">
          <div class="auth-buttons">
            <SignInButton mode="modal" class="btn btn-primary" />
            <SignUpButton mode="modal" class="btn btn-secondary" />
          </div>
        </Show>
        <Show when="signed-in">
          <UserButton />
        </Show>
      </div>
    </header>

    <main class="download-main">
      <div class="download-card">
        <h2>File Download</h2>
        
        <Show when="signed-out">
          <div class="status-box warning">
            <p>You must be signed in to download this file.</p>
          </div>
        </Show>
        
        <Show when="signed-in">
          <div v-if="status === 'initializing'" class="status-box info">
            <div class="spinner"></div>
            <p>Preparing...</p>
          </div>
          
          <div v-else-if="status === 'downloading'" class="status-box info">
            <div class="spinner"></div>
            <p>Requesting download link...</p>
          </div>
          
          <div v-else-if="status === 'success'" class="status-box success">
            <p>✅ Download started!</p>
            <p class="text-sm">If your download didn't start automatically, please check your browser settings.</p>
          </div>
          
          <div v-else-if="status === 'error'" class="status-box error">
            <p>❌ <strong>Error:</strong> {{ errorMsg }}</p>
          </div>
        </Show>
        
        <div class="actions">
          <button class="btn btn-primary" @click="goHome">Go to My Files</button>
          <button v-if="status === 'error'" class="btn btn-secondary" @click="initiateDownload">Try Again</button>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.download-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: var(--color-background-soft);
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background-color: var(--color-background);
  border-bottom: 1px solid var(--color-border);
}

.logo {
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--color-heading);
}

.auth-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.auth-buttons {
  display: flex;
  gap: 0.5rem;
}

.download-main {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 2rem;
}

.download-card {
  background-color: var(--color-background);
  padding: 2.5rem;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.1);
  max-width: 500px;
  width: 100%;
  text-align: center;
}

h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: var(--color-heading);
}

.status-box {
  padding: 1.5rem;
  border-radius: 6px;
  margin-bottom: 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.status-box.info {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #334155;
}

.status-box.success {
  background-color: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}

.status-box.error {
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.status-box.warning {
  background-color: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
}

.status-box p {
  margin: 0;
}

.text-sm {
  font-size: 0.875rem;
  opacity: 0.8;
  margin-top: 0.5rem !important;
}

.actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
}

.btn {
  padding: 0.6rem 1.25rem;
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: all 0.2s;
  font-family: inherit;
}

.btn-primary {
  background-color: #0f172a;
  color: white;
}

.btn-primary:hover {
  background-color: #334155;
}

.btn-secondary {
  background-color: transparent;
  border-color: #cbd5e1;
  color: #334155;
}

.btn-secondary:hover {
  background-color: #f1f5f9;
}

.spinner {
  border: 3px solid #e2e8f0;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  width: 30px;
  height: 30px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
