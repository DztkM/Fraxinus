<script setup lang="ts">
import { ref } from 'vue'
import { Show, SignInButton, SignUpButton, UserButton, useAuth } from '@clerk/vue'
import FileManager from './components/FileManager.vue'

const { getToken, isLoaded, isSignedIn } = useAuth()
const authCheckResult = ref<string | null>(null)
const isLoading = ref(false)

const checkAuth = async () => {
  isLoading.value = true
  authCheckResult.value = null
  
  try {
    const token = await getToken.value()
    const response = await fetch('http://localhost:8000/v1/api/check_auth', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      authCheckResult.value = `Success: ${JSON.stringify(data)}`
    } else {
      authCheckResult.value = `Error: ${response.status} ${response.statusText}`
    }
  } catch (error: any) {
    authCheckResult.value = `Request failed: ${error.message}`
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="app-container">
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

    <main class="app-main">
      <Show when="signed-in">
        <FileManager />
      </Show>
      
      <Show when="signed-out">
        <div class="content-card">
          <h1>Welcome to Fraxinus Storage</h1>
          <p>This is the frontend for the internal file gateway. Use the controls above to sign in or sign up.</p>
          
          <div class="auth-check-section">
            <h2>Test Authentication</h2>
            <p>Click the button below to send a request to the backend with your Clerk token.</p>
            
            <button @click="checkAuth" :disabled="isLoading" class="btn btn-primary">
              {{ isLoading ? 'Checking...' : 'Check Auth' }}
            </button>
            
            <div v-if="authCheckResult" class="result-box" :class="{ 'error': authCheckResult.startsWith('Error') || authCheckResult.startsWith('Request') }">
              {{ authCheckResult }}
            </div>
          </div>
        </div>
      </Show>
    </main>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background-color: var(--color-background);
  border-bottom: 1px solid var(--color-border);
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
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

.btn {
  padding: 0.5rem 1rem;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
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
}

.btn-secondary {
  background-color: transparent;
  border-color: #cbd5e1;
  color: #334155;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #f1f5f9;
}

.app-main {
  flex: 1;
  padding: 2rem;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  background-color: var(--color-background-soft);
}

.content-card {
  background-color: var(--color-background);
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.1);
  max-width: 600px;
  width: 100%;
}

h1 {
  margin-bottom: 1rem;
  color: var(--color-heading);
  font-size: 1.75rem;
}

p {
  margin-bottom: 1.5rem;
  color: var(--color-text);
}

.auth-check-section {
  margin-top: 2.5rem;
  padding-top: 2rem;
  border-top: 1px solid var(--color-border);
}

.auth-check-section h2 {
  margin-bottom: 1rem;
  font-size: 1.25rem;
  color: var(--color-heading);
}

.result-box {
  margin-top: 1.5rem;
  padding: 1rem;
  background-color: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 4px;
  color: #166534;
  word-break: break-all;
  font-family: monospace;
}

.result-box.error {
  background-color: #fef2f2;
  border-color: #fecaca;
  color: #991b1b;
}

.warning-text {
  margin-top: 1rem;
  color: #b45309;
  font-size: 0.875rem;
}
</style>
