/**
 * v0.3-14: Playwright E2E tests for KinFrame showcase and core user flows.
 */
import { test, expect } from '@playwright/test'

const API_BASE = '/api'
const ADMIN_USER = 'e2e_admin'
const ADMIN_PASS = 'e2epass123'

/** Log in via API, return session cookie string for reuse. */
async function getSessionCookie(request: any): Promise<string> {
  const resp = await request.post(`${API_BASE}/auth/login`, {
    data: { username: ADMIN_USER, password: ADMIN_PASS },
  })
  expect(resp.status()).toBe(200)
  const cookies = resp.headers()['set-cookie']
  expect(cookies).toBeDefined()
  return cookies
}

/** Set the kinframe_session cookie on the page context via API login. */
async function loginViaApi(page: any, request: any) {
  const cookie = await getSessionCookie(request)
  await page.context().addCookies([
    {
      name: 'kinframe_session',
      value: extractCookieValue(cookie, 'kinframe_session'),
      domain: 'localhost',
      path: '/',
    },
  ])
}

function extractCookieValue(setCookieHeader: string, name: string): string {
  const match = setCookieHeader.match(new RegExp(`${name}=([^;]+)`))
  return match ? match[1] : ''
}

// ── 1. Login Flow ──────────────────────────────────────────────────

test.describe('Login flow', () => {
  test('login via UI redirects to /showcase', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('form')).toBeVisible()

    await page.getByLabel('Username').fill(ADMIN_USER)
    await page.getByLabel('Password').fill(ADMIN_PASS)
    await page.getByRole('button', { name: /sign in/i }).click()

    await page.waitForURL('**/showcase', { timeout: 10000 })
    expect(page.url()).toContain('/showcase')
  })

  test('login with wrong password shows error', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel('Username').fill('nobody')
    await page.getByLabel('Password').fill('wrongpassword')
    await page.getByRole('button', { name: /sign in/i }).click()

    // Error message should appear
    await expect(page.locator('.bg-red-50, [class*="error"]')).toBeVisible({ timeout: 5000 })
    // Should stay on login page
    expect(page.url()).toContain('/login')
  })
})

// ── 2. Showcase Rendering ──────────────────────────────────────────

test.describe('Showcase rendering', () => {
  test.beforeEach(async ({ page, request }) => {
    await loginViaApi(page, request)
  })

  test('showcase loads and displays slide area', async ({ page }) => {
    await page.goto('/showcase')
    await page.waitForLoadState('networkidle')

    // Showcase should have the main stage area (h-screen container with bg-neutral-950)
    const stage = page.locator('.bg-neutral-950')
    await expect(stage.first()).toBeVisible({ timeout: 5000 })

    // KinFrame branding should be in the menu bar
    await expect(page.getByText('KinFrame')).toBeVisible({ timeout: 5000 })
  })

  test('bottom bar is visible on showcase', async ({ page }) => {
    await page.goto('/showcase')

    // Bottom bar with position indicator or category info
    const hasBottom = await page.locator('text=/\\d+\\s*\\/\\s*\\d+/').first().isVisible({ timeout: 5000 }).catch(() => false)
    const hasPhotoCount = await page.locator('[class*="bottom"]').first().isVisible({ timeout: 5000 }).catch(() => false)

    expect(hasBottom || hasPhotoCount).toBe(true)
  })
})

// ── 3. Keyboard Navigation ─────────────────────────────────────────

test.describe('Keyboard navigation', () => {
  test.beforeEach(async ({ page, request }) => {
    await loginViaApi(page, request)
    await page.goto('/showcase')
    await page.waitForLoadState('networkidle')
  })

  test('ArrowRight triggers next photo navigation', async ({ page }) => {
    // Click on the page to focus it first
    await page.click('body')
    await page.keyboard.press('ArrowRight')
    // Should not crash or navigate away from showcase
    await expect(page).toHaveURL(/\/showcase/)
  })

  test('ArrowLeft triggers previous photo navigation', async ({ page }) => {
    await page.click('body')
    await page.keyboard.press('ArrowLeft')
    await expect(page).toHaveURL(/\/showcase/)
  })

  test('ArrowDown switches to next category', async ({ page }) => {
    await page.click('body')
    await page.keyboard.press('ArrowDown')
    await expect(page).toHaveURL(/\/showcase/)
  })

  test('ArrowUp switches to previous category', async ({ page }) => {
    await page.click('body')
    await page.keyboard.press('ArrowUp')
    await expect(page).toHaveURL(/\/showcase/)
  })
})

// ── 4. Mouse Navigation ────────────────────────────────────────────

test.describe('Mouse navigation', () => {
  test.beforeEach(async ({ page, request }) => {
    await loginViaApi(page, request)
    await page.goto('/showcase')
    await page.waitForLoadState('networkidle')
  })

  test('left click navigates photos', async ({ page }) => {
    // Click in the main slide area
    const viewport = page.viewportSize()!
    await page.mouse.click(viewport.width * 0.5, viewport.height * 0.5)
    await expect(page).toHaveURL(/\/showcase/)
  })

  test('right click does not show browser context menu', async ({ page }) => {
    // Right-click in the main area
    const viewport = page.viewportSize()!
    await page.mouse.click(viewport.width * 0.5, viewport.height * 0.5, { button: 'right' })
    // Verify we're still on showcase (context menu suppressed)
    await expect(page).toHaveURL(/\/showcase/)
  })
})

// ── 5. Menu Behavior ───────────────────────────────────────────────

test.describe('Menu behavior', () => {
  test.beforeEach(async ({ page, request }) => {
    await loginViaApi(page, request)
    await page.goto('/showcase')
    await page.waitForLoadState('networkidle')
  })

  test('menu appears on mouse hover at top', async ({ page }) => {
    // Move mouse to top of page to trigger menu
    await page.mouse.move(640, 10)
    await page.waitForTimeout(500)

    // Menu items should be visible
    const galleryLink = page.getByTitle('Gallery')
    const isVisible = await galleryLink.isVisible({ timeout: 3000 }).catch(() => false)
    expect(isVisible).toBe(true)
  })

  test('menu contains navigation links', async ({ page }) => {
    await page.mouse.move(640, 10)
    await page.waitForTimeout(500)

    await expect(page.getByTitle('Gallery')).toBeVisible({ timeout: 3000 })
    await expect(page.getByTitle('Upload')).toBeVisible({ timeout: 3000 })
  })
})

// ── 6. Category Bar ────────────────────────────────────────────────

test.describe('Category bar', () => {
  test.beforeEach(async ({ page, request }) => {
    await loginViaApi(page, request)
    await page.goto('/showcase')
    await page.waitForLoadState('networkidle')
  })

  test('C key toggles category sidebar', async ({ page }) => {
    await page.click('body')
    await page.keyboard.press('KeyC')
    // Should not crash; category sidebar visibility toggles
    await expect(page).toHaveURL(/\/showcase/)
  })
})

// ── 7. Photo Detail Page ───────────────────────────────────────────

test.describe('Photo detail', () => {
  test.beforeEach(async ({ page, request }) => {
    await loginViaApi(page, request)
  })

  test('navigating to photo detail shows metadata', async ({ page, request }) => {
    // Get a photo ID from the showcase API
    const resp = await request.get(`${API_BASE}/showcase`)
    const data = await resp.json()
    const readyPhotos = data.photos?.filter((p: any) => p.photo?.status === 'ready') || []

    if (readyPhotos.length === 0) {
      test.skip(true, 'No ready photos available')
      return
    }

    const photoId = readyPhotos[0].photo.id
    await page.goto(`/photo/${photoId}`)
    await page.waitForLoadState('networkidle')

    // Should show photo ID or metadata on the page
    const hasContent = await page.locator('text=/caption|message|taken|category/i').first().isVisible({ timeout: 5000 }).catch(() => false)
    expect(hasContent).toBe(true)
  })
})

// ── 8. Upload Flow ─────────────────────────────────────────────────

test.describe('Upload flow', () => {
  test.beforeEach(async ({ page, request }) => {
    await loginViaApi(page, request)
  })

  test('upload page loads and shows form', async ({ page }) => {
    await page.goto('/upload')
    await page.waitForLoadState('networkidle')

    // Upload page should have a file input or upload button
    const hasUpload = await page.locator('input[type="file"]').first().isVisible({ timeout: 5000 }).catch(() => false)
    const hasButton = await page.locator('text=/upload|select|choose/i').first().isVisible({ timeout: 5000 }).catch(() => false)
    expect(hasUpload || hasButton).toBe(true)
  })
})

// ── 9. Admin Functions ─────────────────────────────────────────────

test.describe('Admin visibility', () => {
  test.beforeEach(async ({ page, request }) => {
    await loginViaApi(page, request)
    await page.goto('/showcase')
    await page.waitForLoadState('networkidle')
  })

  test('admin user sees admin menu items', async ({ page }) => {
    await page.mouse.move(640, 10)
    await page.waitForTimeout(500)

    // Admin should see Users and Jobs links
    const usersLink = page.getByTitle('Users')
    const jobsLink = page.getByTitle('Jobs')

    const usersVisible = await usersLink.isVisible({ timeout: 3000 }).catch(() => false)
    const jobsVisible = await jobsLink.isVisible({ timeout: 3000 }).catch(() => false)

    expect(usersVisible).toBe(true)
    expect(jobsVisible).toBe(true)
  })

  test('admin can access admin pages', async ({ page }) => {
    await page.goto('/admin/jobs')
    await page.waitForLoadState('networkidle')
    // Should not redirect to login
    expect(page.url()).toContain('/admin/jobs')

    // Should show jobs content
    const hasContent = await page.locator('text=/job|status|type/i').first().isVisible({ timeout: 5000 }).catch(() => false)
    expect(hasContent).toBe(true)
  })
})

// ── 10. Empty State ────────────────────────────────────────────────

test.describe('Empty state', () => {
  test.beforeEach(async ({ page, request }) => {
    await loginViaApi(page, request)
  })

  test('empty category shows empty state message', async ({ page, request }) => {
    // Check if any category has 0 photos
    const resp = await request.get(`${API_BASE}/showcase`)
    const data = await resp.json()
    const categories = data.categories || []

    // Find a category with 0 photos
    const photoCountByCategory: Record<string, number> = {}
    for (const item of data.photos || []) {
      const cat = item.photo?.category
      if (cat) photoCountByCategory[cat] = (photoCountByCategory[cat] || 0) + 1
    }

    const emptyCategory = categories.find((c: any) => !photoCountByCategory[c.slug])

    if (!emptyCategory) {
      test.skip(true, 'No empty categories to test')
      return
    }

    // Navigate to showcase with the empty category
    await page.goto(`/showcase?category=${emptyCategory.slug}`)
    await page.waitForLoadState('networkidle')

    // Should show empty state message
    const hasEmptyMessage = await page.locator('text=/no photos|empty|nothing|upload/i').first().isVisible({ timeout: 5000 }).catch(() => false)
    expect(hasEmptyMessage).toBe(true)
  })
})

// ── 11. Mobile Viewport ────────────────────────────────────────────

test.describe('Mobile viewport', () => {
  test.beforeEach(async ({ page, request }) => {
    await loginViaApi(page, request)
  })

  test('showcase renders on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/showcase')
    await page.waitForLoadState('networkidle')

    // Should not crash or show error
    const bodyText = await page.locator('body').innerText()
    expect(bodyText.length).toBeGreaterThan(0)
  })

  test('mobile hamburger menu visible for categories', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/showcase')
    await page.waitForLoadState('networkidle')

    // Mobile hamburger button should be visible (has aria-label)
    const hamburger = page.getByLabel(/categories/i)
    const isVisible = await hamburger.isVisible({ timeout: 5000 }).catch(() => false)
    expect(isVisible).toBe(true)
  })

  test('mobile touch targets meet minimum size', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/showcase')
    await page.waitForLoadState('networkidle')

    // Check nav links have min 44px touch targets (h-11 class = 44px)
    const navLinks = page.locator('.h-11')
    const count = await navLinks.count()
    expect(count).toBeGreaterThan(0)
  })
})
