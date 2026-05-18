const path = require('path')
const vue = require('@vitejs/plugin-vue')

/** @type {import('vitest').UserConfig} */
module.exports = {
  plugins: [vue()],
  test: {
    environment: 'happy-dom',
    include: ['tests/**/*.test.ts'],
  },
  resolve: {
    alias: {
      '~': path.resolve(__dirname),
    },
  },
}
