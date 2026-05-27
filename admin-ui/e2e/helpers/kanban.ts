import type { Locator, Page } from "@playwright/test";

/** dnd-kit needs pointer movement past activation distance (6px) before drop. */
export async function dragKanbanCard(page: Page, card: Locator, dropZone: Locator) {
  const cardBox = await card.boundingBox();
  const dropBox = await dropZone.boundingBox();
  if (!cardBox || !dropBox) {
    throw new Error("Kanban drag: card or drop zone not visible");
  }

  const startX = cardBox.x + cardBox.width / 2;
  const startY = cardBox.y + cardBox.height / 2;
  const endX = dropBox.x + dropBox.width / 2;
  const endY = dropBox.y + dropBox.height / 2;

  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(startX + 10, startY, { steps: 4 });
  await page.mouse.move(endX, endY, { steps: 30 });
  await page.mouse.up();
}
