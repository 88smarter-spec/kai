import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  use: {
    baseURL: process.env.APP_URL || "http://127.0.0.1:5173",
    headless: true,
    launchOptions: { executablePath: process.env.CHROMIUM_PATH },
  },
  workers: 1,
  reporter: "list",
});
