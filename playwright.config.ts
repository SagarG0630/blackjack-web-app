// playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  timeout: 30000,
  testDir: 'e2e',
  use: {
    headless: true,
  },
  reporter: [['list']],
});
