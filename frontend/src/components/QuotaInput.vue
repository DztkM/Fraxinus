<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'

const props = defineProps<{
  modelValue: number | null
  maxBytes?: number | null
  compact?: boolean
  required?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: number | null): void
}>()

const MULTIPLIERS: Record<string, number> = {
  'MB': 1024 * 1024,
  'GB': 1024 * 1024 * 1024,
  'TB': 1024 * 1024 * 1024 * 1024
}

const displayValue = ref<number | ''>('')
const unit = ref<string>('GB')
const sliderValue = ref<number>(0)

const sliderMax = computed(() => {
  if (props.maxBytes !== undefined && props.maxBytes !== null) {
    const calculatedMax = Math.floor(props.maxBytes / MULTIPLIERS[unit.value])
    return Math.min(1024, Math.max(0, calculatedMax))
  }
  return 1024
})

let isInternalUpdate = false

const updateFromModelValue = (bytes: number | null) => {
  isInternalUpdate = true
  if (bytes === null) {
    displayValue.value = ''
    sliderValue.value = 0
    unit.value = 'GB'
  } else {
    // Determine best unit
    if (bytes >= MULTIPLIERS['TB'] && bytes % MULTIPLIERS['TB'] === 0) {
      unit.value = 'TB'
      displayValue.value = bytes / MULTIPLIERS['TB']
    } else if (bytes >= MULTIPLIERS['GB'] && bytes % MULTIPLIERS['GB'] === 0) {
      unit.value = 'GB'
      displayValue.value = bytes / MULTIPLIERS['GB']
    } else {
      unit.value = 'MB'
      displayValue.value = Math.max(0, bytes / MULTIPLIERS['MB'])
    }
    sliderValue.value = Math.min(sliderMax.value, Number(displayValue.value))
  }
  isInternalUpdate = false
}

const emitUpdate = () => {
  if (isInternalUpdate) return
  if (displayValue.value === '' || displayValue.value === null) {
    emit('update:modelValue', null)
  } else {
    const bytes = Number(displayValue.value) * MULTIPLIERS[unit.value]
    emit('update:modelValue', Math.floor(bytes))
  }
}

const onDisplayValueChange = () => {
  sliderValue.value = Math.min(sliderMax.value, Number(displayValue.value) || 0)
  emitUpdate()
}

const onSliderChange = () => {
  displayValue.value = sliderValue.value
  emitUpdate()
}

const onUnitChange = () => {
  emitUpdate()
}

watch(() => props.modelValue, (newVal) => {
  if (!isInternalUpdate) {
    updateFromModelValue(newVal)
  }
})

onMounted(() => {
  updateFromModelValue(props.modelValue)
})
</script>

<template>
  <div class="quota-input-wrapper" :class="{ 'is-compact': compact }">
    <div class="quota-controls">
      <input 
        type="number" 
        v-model="displayValue" 
        @input="onDisplayValueChange"
        min="0"
        :placeholder="required ? 'Quota required' : 'Enter quota'"
        :required="required"
        class="quota-number-input"
      />
      <select v-model="unit" @change="onUnitChange" class="quota-unit-select">
        <option value="MB">MB</option>
        <option value="GB">GB</option>
        <option value="TB">TB</option>
      </select>
    </div>
    
    <div v-if="!compact" class="slider-container">
      <input 
        type="range" 
        v-model.number="sliderValue" 
        @input="onSliderChange"
        min="0" 
        :max="sliderMax" 
        step="1"
        class="quota-slider"
      />
      <div class="slider-labels">
        <span>0 {{ unit }}</span>
        <span>{{ sliderMax }} {{ unit }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.quota-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
}

.quota-input-wrapper.is-compact {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}

.quota-controls {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.quota-number-input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  background-color: var(--color-background-soft, #f8fafc);
  color: var(--color-text, #334155);
  font-size: 1rem;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.is-compact .quota-number-input {
  padding: 0.35rem 0.5rem;
  font-size: 0.9rem;
  width: 100px;
  flex: none;
}

.quota-number-input:focus, .quota-unit-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.quota-unit-select {
  padding: 0.75rem 0.5rem;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  background-color: var(--color-background-soft, #f8fafc);
  color: var(--color-text, #334155);
  font-size: 1rem;
  cursor: pointer;
  width: 80px;
}

.is-compact .quota-unit-select {
  padding: 0.35rem 0.5rem;
  font-size: 0.9rem;
  width: 65px;
}

.slider-container {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0 0.25rem;
}

.quota-slider {
  width: 100%;
  accent-color: #3b82f6;
  cursor: pointer;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: var(--color-text-light, #64748b);
}
</style>
