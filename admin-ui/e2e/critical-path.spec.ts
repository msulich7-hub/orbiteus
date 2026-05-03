import { expect, test } from "@playwright/test";

/**
 * 5 critical-path scenarios required by docs/35 §15.
 *
 * These tests run against a fully-up stack. CI typically launches
 * `docker compose up` before invoking `npx playwright test`. Locally:
 *
 *   docker compose up -d
 *   npm run e2e --workspace admin-ui
 *
 * Set credentials via env:
 *   E2E_LOGIN_EMAIL    (default admin@example.com)
 *   E2E_LOGIN_PASSWORD (default admin1234)
 */

const EMAIL = process.env.E2E_LOGIN_EMAIL ?? "admin@example.com";
const PASSWORD = process.env.E2E_LOGIN_PASSWORD ?? "admin1234";

test.describe("Orbiteus critical path", () => {
  test("welcome page loads without authentication", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /welcome/i })).toBeVisible();
  });

  test("login → dashboard renders CRM stats", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/email/i).fill(EMAIL);
    await page.getByLabel(/password/i).fill(PASSWORD);
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByText(/Dashboard/i)).toBeVisible();
  });

  test("create person via catch-all route", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/email/i).fill(EMAIL);
    await page.getByLabel(/password/i).fill(PASSWORD);
    await page.getByRole("button", { name: /sign in/i }).click();

    await page.goto("/crm/person/new");
    const stamp = Date.now();
    await page.getByLabel(/name/i).first().fill(`E2E Person ${stamp}`);
    await page.getByRole("button", { name: /save/i }).click();

    await expect(page).toHaveURL(/\/crm\/person\//);
    await expect(page.getByText(`E2E Person ${stamp}`)).toBeVisible();
  });

  test("kanban view loads for crm.lead", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/email/i).fill(EMAIL);
    await page.getByLabel(/password/i).fill(PASSWORD);
    await page.getByRole("button", { name: /sign in/i }).click();

    await page.goto("/crm/lead?view=kanban");
    // The kanban shows at least one stage column from bootstrap defaults.
    await expect(page.getByText(/New|Qualified|Won/i).first()).toBeVisible();
  });

  test("/api/health/live responds with status ok", async ({ request }) => {
    const res = await request.get("/api/health/live");
    expect(res.status()).toBe(200);
    const json = await res.json();
    expect(json.status).toBe("ok");
  });
});
