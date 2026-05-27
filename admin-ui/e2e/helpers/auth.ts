import type { Page } from "@playwright/test";

export const E2E_EMAIL = process.env.E2E_LOGIN_EMAIL ?? "admin@example.com";
export const E2E_PASSWORD = process.env.E2E_LOGIN_PASSWORD ?? "admin1234";

/** Authenticate via API (stable, fast) then land on dashboard. */
export async function signIn(page: Page, redirect = "/") {
  await page.goto("/login");
  const ok = await page.evaluate(
    async ({ email, password }) => {
      const r = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });
      return r.ok;
    },
    { email: E2E_EMAIL, password: E2E_PASSWORD },
  );
  if (!ok) {
    const apiLogin = await page.request.post("/api/auth/login", {
      data: { email: E2E_EMAIL, password: E2E_PASSWORD },
    });
    if (!apiLogin.ok()) {
      throw new Error("E2E login API failed — is the stack up with seed data?");
    }
  }
  await page.goto(redirect);
  await page.waitForLoadState("domcontentloaded");
}

/** Pause for demo recordings (respects E2E_DEMO_PAUSE_MS). */
export async function demoPause(page: Page, ms?: number) {
  const delay = ms ?? Number(process.env.E2E_DEMO_PAUSE_MS ?? 800);
  if (delay > 0) await page.waitForTimeout(delay);
}
