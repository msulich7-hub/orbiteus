import { expect, test } from "@playwright/test";
import { demoPause, signIn } from "./helpers/auth";

/**
 * Cinematic CRM demo — one long flow for marketing / training videos.
 *
 * Playwright records video when run with project `crm-demo`:
 *   E2E_BASE_URL=http://localhost:3010 E2E_FULL_SUITE=1 E2E_DEMO_PAUSE_MS=1200 ^
 *     npx playwright test e2e/crm-demo-video.spec.ts --project=crm-demo
 *
 * Videos: admin-ui/test-results/.../video.webm
 */

test.describe("CRM product demo @demo", () => {
  test("full sales rep journey — dashboard to close", async ({ page }) => {
    test.setTimeout(180_000);
    test.skip(!process.env.E2E_FULL_SUITE, "Set E2E_FULL_SUITE=1");

    // 1. Login → Dashboard
    await signIn(page);
    await demoPause(page, 1500);
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await demoPause(page);

    // 2. Quick action — Pipeline Kanban
    await page.getByText("Pipeline Kanban").click();
    await expect(page).toHaveURL(/view=kanban/);
    await expect(page.getByTestId("crm-kanban-board")).toBeVisible({ timeout: 20_000 });
    await demoPause(page, 2000);

    // 3. Show metrics + rotting filter
    await expect(page.getByTestId("crm-kanban-metrics")).toBeVisible();
    await page.getByText("Rotting only", { exact: true }).click();
    await demoPause(page, 1500);
    await page.getByText("Rotting only", { exact: true }).click();
    await demoPause(page);

    // 4. Open deal drawer
    const card = page.locator('[data-testid^="crm-kanban-card-"]').first();
    await expect(card).toBeVisible();
    await card.locator(".mantine-Text-root").first().click();
    await demoPause(page, 2000);
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText("Deal details")).toBeVisible();
    await expect(dialog.getByText("Log activity")).toBeVisible();
    await demoPause(page);

    // 5. Close drawer — rotting queue
    await page.keyboard.press("Escape");
    await demoPause(page, 800);
    await page.goto("/crm/lead?filter=rotting");
    await expect(page.getByRole("heading", { name: /Rotting/i })).toBeVisible();
    await demoPause(page, 2000);

    // 6. Today's activities
    await page.goto("/crm/activity?filter=today");
    await expect(page.getByRole("heading", { name: /Today/i })).toBeVisible();
    await demoPause(page, 2000);

    // 7. Prospect inbox
    await page.goto("/crm/prospect?filter=inbox");
    await demoPause(page, 2000);

    // 8. Back to kanban — final hero shot
    await page.goto("/crm/lead?view=kanban");
    await expect(page.getByTestId("crm-kanban-board")).toBeVisible({ timeout: 15_000 });
    await page.evaluate(() => window.scrollTo(0, 0));
    await demoPause(page, 2500);
  });
});
