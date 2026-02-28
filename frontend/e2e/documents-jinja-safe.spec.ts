import { test, expect } from "@playwright/test";

const ADMIN_EMAIL = "admin@local";
const ADMIN_PASSWORD = "admin123";

test.describe("Documents editor Jinja safety", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.request.post("/api/seed/dev").catch(() => {});
    await page.getByPlaceholder("email").fill(ADMIN_EMAIL);
    await page.getByPlaceholder("password").fill(ADMIN_PASSWORD);
    await page.getByRole("button", { name: "Login" }).click();
    await expect(page.getByText("Logged in")).toBeVisible({ timeout: 10000 });
  });

  test("save twice keeps template_html identical", async ({ page }) => {
    const template = `<div class="po-page">
  <h1>PO {{ po.po_number }}</h1>
  {% if lines and (lines|length) > 0 %}
    <ul>
      {% for line in lines %}
        <li>{{ line.description }} — {{ line.qty }}</li>
      {% endfor %}
    </ul>
  {% else %}
    <p>No lines</p>
  {% endif %}
</div>`;

    await page.goto("/admin/documents");
    await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("jinja-raw-banner")).toBeVisible();

    await page.getByPlaceholder("Template name").fill(`Jinja e2e ${Date.now()}`);
    await page.getByTestId("jinja-raw-editor").fill(template);

    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.getByTestId("template-save-btn")).toBeVisible({ timeout: 10000 });

    const saveAndCaptureTemplateHtml = async () => {
      const resPromise = page.waitForResponse((r) => {
        try {
          const path = new URL(r.url()).pathname;
          return r.request().method() === "PUT" && /\/api\/document-templates\/[^/]+$/.test(path);
        } catch {
          return false;
        }
      });
      await page.getByTestId("template-save-btn").click();
      const res = await resPromise;
      expect(res.ok()).toBeTruthy();
      const body = (await res.json()) as { template_html?: string };
      expect(typeof body.template_html).toBe("string");
      return body.template_html as string;
    };

    const firstSaveHtml = await saveAndCaptureTemplateHtml();
    const secondSaveHtml = await saveAndCaptureTemplateHtml();

    expect(secondSaveHtml).toBe(firstSaveHtml);
    expect(secondSaveHtml).toContain("{% if lines and (lines|length) > 0 %}");
    expect(secondSaveHtml).toContain("{% endif %}");
    expect(secondSaveHtml).toContain("{{ line.description }}");
    expect(secondSaveHtml).not.toContain("__JINJA_BLOCK_");
    const ifCount = (secondSaveHtml.match(/{%\s*if\b/g) || []).length;
    const endifCount = (secondSaveHtml.match(/{%\s*endif\b/g) || []).length;
    expect(ifCount).toBe(endifCount);
  });
});
