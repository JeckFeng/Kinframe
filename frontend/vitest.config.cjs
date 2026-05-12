const path = require('path')

/** @type {import('vitest').UserConfig} */
module.exports = {
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
