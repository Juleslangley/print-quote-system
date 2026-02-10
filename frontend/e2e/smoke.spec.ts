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
    await page.goto("/admin/materials");
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
    await page.goto("/admin/customers");
    await page.getByRole("button", { name: "New Customer" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("button", { name: "Cancel" }).first().click();
    await expect(page.getByRole("dialog")).not.toBeVisible();
    await page.getByRole("link", { name: "Admin" }).click();
    await expect(page).toHaveURL(/\/admin$/);
  });
});
