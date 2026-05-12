<script setup lang="ts">
const { currentUser, loadMe } = useAuth()

if (!currentUser.value) {
  await loadMe()
}

await navigateTo(currentUser.value ? '/showcase' : '/login')
</script>

<template>
  <div />
</template>
