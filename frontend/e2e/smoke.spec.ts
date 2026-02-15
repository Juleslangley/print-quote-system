import { test, expect } from "@playwright/test";

const ADMIN_EMAIL = "admin@local";
const ADMIN_PASSWORD = "admin123";

test.describe("Smoke: modal and nav after close", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.getByPlaceholder("email").fill(ADMIN_EMAIL);
    await page.getByPlaceholder("password").fill(ADMIN_PASSWORD);
    await page.getByRole("button", { name: "Login" }).click();
    await expect(page.getByText("Logged in")).toBeVisible({ timeout: 10000 });
  });

  test("materials: open modal, cancel, Admin nav works", async ({ page }) => {
    await page.goto("/materials");
    await page.getByRole("button", { name: "New Material" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("button", { name: "Cancel" }).first().click();
    await expect(page.getByRole("dialog")).not.toBeVisible();
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
    await expect(page.getByRole("heading", { name: /Purchase orders/i })).toBeVisible({ timeout: 10000 });
    await page.getByRole("button", { name: "New PO" }).click();
    const newPoDialog = page.getByRole("dialog");
    await expect(newPoDialog).toBeVisible();
    await newPoDialog.getByRole("combobox").selectOption({ index: 1 });
    await newPoDialog.getByRole("button", { name: "Save" }).click();
    await expect(page).toHaveURL(/\/admin\/purchase-orders\/[a-f0-9-]+/, { timeout: 15000 });
    await expect(page.getByRole("heading", { name: "Draft" })).toBeVisible({ timeout: 5000 });

    await page.getByRole("button", { name: "Add Line" }).click();
    const addLineDialog = page.getByRole("dialog", { name: "Add line" });
    await expect(addLineDialog).toBeVisible();
    await addLineDialog.getByLabel(/Description/i).fill("E2E test line");
    await addLineDialog.getByRole("button", { name: "Save line" }).click();
    await expect(addLineDialog).not.toBeVisible({ timeout: 5000 });
    await expect(page.getByText("E2E test line")).toBeVisible({ timeout: 5000 });

    await page.getByRole("button", { name: "Save" }).first().click();
    await expect(page.getByRole("heading", { name: /^PO\d+$/ })).toBeVisible({ timeout: 10000 });
  });
});
