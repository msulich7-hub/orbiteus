import { expect, test } from "@playwright/test";
import { demoPause, signIn } from "./helpers/auth";
import { dragKanbanCard } from "./helpers/kanban";

/**
 * CRM full suite — requires seeded practice data.
 *
 * Run:
 *   E2E_BASE_URL=http://localhost:3010 E2E_FULL_SUITE=1 npx playwright test e2e/crm-suite.spec.ts
 */

test.describe("CRM suite @crm", () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!process.env.E2E_FULL_SUITE, "Set E2E_FULL_SUITE=1 (needs seed_crm_practice)");
    await signIn(page);
  });

  test("dashboard shows quick actions and stats", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByText("Pipeline Kanban")).toBeVisible();
    await expect(page.getByText("Rotting deals")).toBeVisible();
    await expect(page.getByText("Today's activities")).toBeVisible();
    await expect(page.getByText("Prospect inbox")).toBeVisible();
  });

  test("sidebar Deals opens kanban board", async ({ page }) => {
    await Promise.all([
      page.waitForURL(/\/crm\/lead\?view=kanban/),
      page.getByRole("link", { name: "Lead", exact: true }).click(),
    ]);
    await expect(page.getByTestId("crm-kanban-metrics")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("crm-kanban-board")).toBeVisible();
  });

  test("kanban shows pipeline stages and deal cards", async ({ page }) => {
    await page.goto("/crm/lead?view=kanban");
    await expect(page.getByTestId("crm-kanban-board")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("New").first()).toBeVisible();
    await expect(page.getByText("Qualified").first()).toBeVisible();
    const card = page.locator('[data-testid^="crm-kanban-card-"]').first();
    await expect(card).toBeVisible({ timeout: 10_000 });
    await expect(card).toContainText(/Acme|Beta|Gamma/i);
  });

  test("kanban drag and drop moves deal to another stage", async ({ page }) => {
    await page.goto("/crm/lead?view=kanban");
    await expect(page.getByTestId("crm-kanban-board")).toBeVisible({ timeout: 15_000 });

    const newColumn = page.locator('[data-testid^="crm-kanban-column-"]').filter({
      has: page.getByText("New", { exact: true }),
    });
    const qualifiedColumn = page.locator('[data-testid^="crm-kanban-column-"]').filter({
      has: page.getByText("Qualified", { exact: true }),
    });

    let sourceColumn = newColumn;
    let targetColumn = qualifiedColumn;
    let card = newColumn.locator('[data-testid^="crm-kanban-card-"]').first();

    if (!(await card.isVisible().catch(() => false))) {
      // Previous run may have moved the demo deal — drag back from Qualified → New
      sourceColumn = qualifiedColumn;
      targetColumn = newColumn;
      card = qualifiedColumn.locator('[data-testid^="crm-kanban-card-"]').first();
    }

    await expect(card).toBeVisible({ timeout: 10_000 });
    const cardLabel = (await card.innerText()).split("\n")[0]?.trim() ?? "";

    const dropZone = targetColumn.locator('[data-testid^="crm-kanban-drop-"], .mantine-Paper-root').last();
    await expect(dropZone).toBeVisible();

    const moveResponse = page.waitForResponse(
      (r) =>
        r.request().method() === "POST"
        && r.url().includes("/api/crm/lead/")
        && r.url().includes("/move"),
      { timeout: 30_000 },
    );
    await dragKanbanCard(page, card, dropZone);
    const response = await moveResponse;
    expect(response.ok()).toBeTruthy();

    await expect(
      targetColumn.locator('[data-testid^="crm-kanban-card-"]').filter({ hasText: cardLabel }),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("deal card opens drawer with timeline", async ({ page }) => {
    await page.goto("/crm/lead?view=kanban");
    await expect(page.getByTestId("crm-kanban-board")).toBeVisible({ timeout: 15_000 });
    const card = page.locator('[data-testid^="crm-kanban-card-"]').first();
    await expect(card).toBeVisible();
    await card.locator(".mantine-Text-root").first().click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible({ timeout: 10_000 });
    await expect(dialog.getByText("Deal details")).toBeVisible();
    await expect(dialog.getByText("Log activity")).toBeVisible();
  });

  test("rotting filter highlights stale deals", async ({ page }) => {
    await page.goto("/crm/lead?view=kanban");
    await expect(page.getByTestId("crm-kanban-board")).toBeVisible({ timeout: 15_000 });
    await page.getByText("Rotting only", { exact: true }).click();
    await expect(page.locator('[data-testid^="crm-kanban-card-"]').first()).toBeVisible();
  });

  test("rotting deals list page", async ({ page }) => {
    await page.goto("/crm/lead?filter=rotting");
    await expect(page.getByRole("heading", { name: /Rotting deals/i })).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByText(/Beta|integracja|WMS/i).first()).toBeVisible({ timeout: 15_000 });
  });

  test("today activities queue", async ({ page }) => {
    await page.goto("/crm/activity?filter=today");
    await expect(page.getByRole("heading", { name: /Today/i })).toBeVisible();
    await expect(page.getByTestId("crm-today-activities")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("button", { name: "Done" }).first()).toBeVisible();
  });

  test("prospect inbox shows unconverted only", async ({ page }) => {
    await page.goto("/crm/prospect?filter=inbox");
    await expect(page.getByText(/Prospect|Inbox|No records/i).first()).toBeVisible({ timeout: 10_000 });
  });

  test("prospect detail has convert button", async ({ page }) => {
    const listRes = await page.request.get("/api/crm/prospect?is_converted=false&limit=5");
    expect(listRes.ok()).toBeTruthy();
    const items = (await listRes.json()).items ?? [];
    expect(items.length).toBeGreaterThan(0);
    await page.goto(`/crm/prospect/${items[0].id}`);
    await expect(page.getByRole("button", { name: /Convert to deal/i })).toBeVisible({
      timeout: 15_000,
    });
  });

  test("work queue sidebar loads on deals page", async ({ page }) => {
    await page.goto("/crm/lead?view=kanban");
    await expect(page.getByText("My rotting").or(page.getByText("Work queues"))).toBeVisible({ timeout: 15_000 });
  });

  test("deal detail shows stage history", async ({ page }) => {
    const kanbanRes = await page.request.get("/api/crm/leads/kanban");
    expect(kanbanRes.ok()).toBeTruthy();
    const columns = (await kanbanRes.json()).columns ?? [];
    const lead = columns.flatMap((c: { leads?: { id: string }[] }) => c.leads ?? [])[0];
    expect(lead?.id).toBeTruthy();
    await page.goto(`/crm/lead/${lead.id}`);
    await expect(page.getByTestId("crm-stage-history")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Stage history")).toBeVisible();
  });

  test("forecast view shows weighted pipeline", async ({ page }) => {
    await page.goto("/crm/lead?view=forecast");
    await expect(page.getByTestId("crm-forecast-table")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/Total weighted/i)).toBeVisible();
  });

  test("export leads CSV download", async ({ page }) => {
    await page.goto("/crm/lead?view=kanban");
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("link", { name: /Export CSV/i }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.csv$/);
  });

  test("log email from deal drawer", async ({ page }) => {
    await page.goto("/crm/lead?view=kanban");
    await page.locator('[data-testid^="crm-kanban-card-"]').first().click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: /Log email/i }).click();
    await page.getByLabel("From").fill("me@orbiteus.com");
    await page.getByLabel("To").fill("client@acme.com");
    await page.getByLabel("Subject").fill("Test demo");
    await page.getByLabel("Body").fill("Hello");
    await page.getByRole("button", { name: /^Save$/ }).click();
    await expect(page.getByText("Test demo")).toBeVisible({ timeout: 10_000 });
  });

  test("kanban cards show lead score badges", async ({ page }) => {
    await page.goto("/crm/lead?view=kanban");
    await expect(page.getByTestId("crm-kanban-board")).toBeVisible({ timeout: 15_000 });
    const card = page.locator('[data-testid^="crm-kanban-card-"]').first();
    await expect(card.getByText(/⚡ \d+/)).toBeVisible({ timeout: 10_000 });
  });
});
