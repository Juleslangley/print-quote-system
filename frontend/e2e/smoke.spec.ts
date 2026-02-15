import { test, expect } from "@playwright/test";

const ADMIN_EMAIL = "admin@local";
const ADMIN_PASSWORD = "admin123";

test.describe("Smoke: modal and nav after close", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.request.post("/api/seed/dev").catch(() => {});
    await page.getByPlaceholder("email").fill(ADMIN_EMAIL);
    await page.getByPlaceholder("password").fill(ADMIN_PASSWORD);
    await page.getByRole("button", { name: "Login" }).click();
    await expect(page.getByText("Logged in")).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(500);
  });

  test("materials: open modal, cancel, Admin nav works", async ({ page }) => {
    await page.goto("/materials");
    await expect(page.getByRole("heading", { name: /Materials/i })).toBeVisible({ timeout: 15000 });
    await page.getByRole("button", { name: "New Material" }).click();
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 5000 });
    await page.getByRole("button", { name: "Cancel" }).first().click();
    await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 5000 });
    await page.getByRole("link", { name: "Admin" }).click();
    await expect(page).toHaveURL(/\/admin$/);
  });

  test("suppliers: open modal, cancel, Admin nav works", async ({ page }) => {
    await page.goto("/admin/suppliers");
    await page.getByRole("button", { name: "New Supplier" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByRole("dialog")).not.toBeVisible();
    await page.getByRole("link", { name: "Admin" }).click();
    await expect(page).toHaveURL(/\/admin$/);
  });

  test("customers: open modal, cancel, Admin nav works", async ({ page }) => {
    await page.goto("/customers");
    await page.getByRole("button", { name: "New Customer" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("button", { name: "Cancel" }).first().click();
    await expect(page.getByRole("dialog")).not.toBeVisible();
    await page.getByRole("link", { name: "Admin" }).click();
    await expect(page).toHaveURL(/\/admin$/);
  });

  test("purchase order: create draft, add line, Save assigns PO number", async ({ page }) => {
    await page.goto("/purchase-orders");
    await expect(page.getByRole("heading", { name: /Purchase orders/i })).toBeVisible({ timeout: 15000 });
    await page.getByRole("button", { name: "New PO" }).click();
    const newPoDialog = page.getByRole("dialog", { name: "New purchase order" });
    await expect(newPoDialog).toBeVisible({ timeout: 5000 });
    await newPoDialog.getByRole("combobox").selectOption({ index: 1 });
    await newPoDialog.getByRole("button", { name: "Create" }).click();
    await expect(page).toHaveURL(/\/admin\/purchase-orders\/[a-f0-9-]+/, { timeout: 15000 });
    await expect(page.getByRole("heading", { name: "Draft" })).toBeVisible({ timeout: 5000 });

    await page.getByRole("button", { name: "Add Line" }).click();
    const addLineDialog = page.getByRole("dialog", { name: "Add line" });
    await expect(addLineDialog).toBeVisible({ timeout: 5000 });
    await addLineDialog.getByLabel(/Description/i).fill("E2E test line");
    await addLineDialog.getByRole("button", { name: "Save line" }).click();
    await expect(addLineDialog).not.toBeVisible({ timeout: 5000 });
    await expect(page.getByText("E2E test line")).toBeVisible({ timeout: 5000 });

    await page.getByRole("button", { name: "Process order" }).click();
    await expect(page.getByText(/PO\d+/).first()).toBeVisible({ timeout: 10000 });
  });

  test("materials: Order button creates PO and opens Add line modal with material", async ({ page }) => {
    await page.goto("/materials");
    await expect(page.getByRole("heading", { name: /Materials/i })).toBeVisible({ timeout: 15000 });
    await page.waitForLoadState("networkidle");
    const orderBtn = page.getByRole("button", { name: "Order" }).first();
    await expect(orderBtn).toBeVisible({ timeout: 10000 });
    if (await orderBtn.isDisabled()) {
      test.skip(true, "No material with supplier; add a supplier to a material to test Order");
    }
    await orderBtn.click();
    await expect(page).toHaveURL(/\/admin\/purchase-orders\/[a-f0-9-]+/, { timeout: 15000 });
    await expect(page).toHaveURL(/materialId=/, { timeout: 5000 });
    await expect(page.getByRole("heading", { name: /Draft|PO\d+/ })).toBeVisible({ timeout: 5000 });
    const addLineDialog = page.getByRole("dialog", { name: "Add line" });
    await expect(addLineDialog).toBeVisible({ timeout: 5000 });
    await expect(addLineDialog.getByText(/Material \(from materials\)|Description/i).first()).toBeVisible({ timeout: 5000 });
  });
});
