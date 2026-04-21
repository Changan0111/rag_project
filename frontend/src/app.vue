<template>
  <router-view />
</template>

<script setup>
</script>

<style>
html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

body {
  background: linear-gradient(135deg, #0a0f1c 0%, #1a1f3c 50%, #0d1025 100%);
  min-height: 100vh;
  position: relative;
}

body::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background:
    radial-gradient(ellipse at 20% 20%, rgba(90, 139, 255, 0.15) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 80%, rgba(118, 75, 162, 0.12) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 50%, rgba(91, 139, 255, 0.08) 0%, transparent 70%);
  pointer-events: none;
  z-index: 0;
}

body::after {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image:
    radial-gradient(circle at 25% 25%, rgba(90, 139, 255, 0.03) 1px, transparent 1px),
    radial-gradient(circle at 75% 75%, rgba(118, 75, 162, 0.03) 1px, transparent 1px);
  background-size: 60px 60px, 80px 80px;
  pointer-events: none;
  z-index: 0;
  animation: gridMove 20s linear infinite;
}

@keyframes gridMove {
  0% {
    transform: translate(0, 0);
  }
  100% {
    transform: translate(-60px, -60px);
  }
}
</style>
