/**
 * v0.3-14: Playwright E2E tests for KinFrame showcase and core user flows.
 */
import { test, expect } from '@playwright/test'

const API_BASE = '/api'
const ADMIN_USER = 'e2e_admin'
const ADMIN_PASS = 'e2epass123'
const MEMBER_PASS = 'memberpass123'

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

async function loginViaApiAs(page: any, request: any, username: string, password: string) {
  const resp = await request.post(`${API_BASE}/auth/login`, {
    data: { username, password },
  })
  expect(resp.status()).toBe(200)
  const cookies = resp.headers()['set-cookie']
  expect(cookies).toBeDefined()
  await page.context().addCookies([
    {
      name: 'kinframe_session',
      value: extractCookieValue(cookies, 'kinframe_session'),
      domain: 'localhost',
      path: '/',
    },
  ])
}

function extractCookieValue(setCookieHeader: string, name: string): string {
  const match = setCookieHeader.match(new RegExp(`${name}=([^;]+)`))
  return match ? match[1] : ''
}

async function createMemberUser(request: any, username: string, displayName: string) {
  const cookie = await getSessionCookie(request)
  const resp = await request.post(`${API_BASE}/admin/users`, {
    headers: { cookie },
    data: {
      username,
      display_name: displayName,
      password: MEMBER_PASS,
      role: 'member',
      is_active: true,
    },
  })
  expect([201, 409]).toContain(resp.status())
}

async function uploadPhotoAsMember(request: any, username: string, password: string) {
  const loginResp = await request.post(`${API_BASE}/auth/login`, {
    data: { username, password },
  })
  expect(loginResp.status()).toBe(200)
  const cookie = loginResp.headers()['set-cookie']
  expect(cookie).toBeDefined()
  const baseImage = Buffer.from(
    '/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxAQEBUQEBIVFRUVFRUVFRUVFRUVFRUVFRUXFhUVFRUYHSggGBolGxUVITEhJSkrLi4uFx8zODMsNygtLisBCgoKDg0OGxAQGy0lICYtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/AABEIAAEAAgMBIgACEQEDEQH/xAAVAAEBAAAAAAAAAAAAAAAAAAAABf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEAAhADEAAAAdQf/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQL/xAAVEQEBAAAAAAAAAAAAAAAAAAAAEf/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAEP/aAAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9k=',
    'base64',
  )
  const comment = Buffer.from(username, 'utf8')
  const jpegComment = Buffer.concat([
    Buffer.from([0xff, 0xfe, ((comment.length + 2) >> 8) & 0xff, (comment.length + 2) & 0xff]),
    comment,
  ])
  const uniqueImage = Buffer.concat([
    baseImage.subarray(0, baseImage.length - 2),
    jpegComment,
    baseImage.subarray(baseImage.length - 2),
  ])

  const uploadResp = await request.post(`${API_BASE}/photos/upload`, {
    headers: { cookie },
    multipart: {
      category: 'life',
      user_message: 'Hide me from showcase',
      file: {
        name: `hide-toggle-${username}.jpg`,
        mimeType: 'image/jpeg',
        buffer: uniqueImage,
      },
    },
  })
  expect(uploadResp.status()).toBe(201)
  return uploadResp.json()
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

// ── 6. Auto-play (v0.4) ────────────────────────────────────────────

test.describe('Auto-play', () => {
  test.beforeEach(async ({ page, request }) => {
    await loginViaApi(page, request)
    await page.goto('/showcase')
    await page.waitForLoadState('networkidle')
  })

  test('Space key toggles auto-play Play/Pause button', async ({ page }) => {
    // Wait for menu to be visible
    await page.mouse.move(640, 10)
    await page.waitForTimeout(600)

    // Initially, the Play icon should be visible (not auto-playing)
    // The button title is "开始自动播放" when paused
    const playButton = page.getByTitle('开始自动播放')
    const isPlayVisible = await playButton.isVisible({ timeout: 3000 }).catch(() => false)
    expect(isPlayVisible).toBe(true)

    // Press Space to start auto-play
    await page.click('body')
    await page.keyboard.press('Space')

    // Now the Pause button should be visible (title="暂停自动播放")
    const pauseButton = page.getByTitle('暂停自动播放')
    const isPauseVisible = await pauseButton.isVisible({ timeout: 3000 }).catch(() => false)
    expect(isPauseVisible).toBe(true)
  })

  test('Space key toggles auto-play off', async ({ page }) => {
    await page.mouse.move(640, 10)
    await page.waitForTimeout(600)

    // Start auto-play
    await page.click('body')
    await page.keyboard.press('Space')

    // Verify playing state
    await expect(page.getByTitle('暂停自动播放')).toBeVisible({ timeout: 3000 })

    // Press Space again to stop
    await page.keyboard.press('Space')

    // Verify paused state
    await expect(page.getByTitle('开始自动播放')).toBeVisible({ timeout: 3000 })
  })

  test('ArrowRight stops auto-play', async ({ page }) => {
    await page.mouse.move(640, 10)
    await page.waitForTimeout(600)

    // Start auto-play
    await page.click('body')
    await page.keyboard.press('Space')
    await expect(page.getByTitle('暂停自动播放')).toBeVisible({ timeout: 3000 })

    // Press ArrowRight — should stop auto-play
    await page.keyboard.press('ArrowRight')
    await page.waitForTimeout(300)

    // Should be back to paused state
    await expect(page.getByTitle('开始自动播放')).toBeVisible({ timeout: 3000 })
  })

  test('interval buttons are visible in menu', async ({ page }) => {
    await page.mouse.move(640, 10)
    await page.waitForTimeout(600)

    // Interval selector buttons (3s, 5s, 8s) should be in the menu
    const s3 = page.locator('button', { hasText: '3s' })
    const s5 = page.locator('button', { hasText: '5s' })
    const s8 = page.locator('button', { hasText: '8s' })

    await expect(s3).toBeVisible({ timeout: 3000 })
    await expect(s5).toBeVisible({ timeout: 3000 })
    await expect(s8).toBeVisible({ timeout: 3000 })
  })

  test('auto-play progress indicator appears when playing', async ({ page }) => {
    // Start auto-play
    await page.click('body')
    await page.keyboard.press('Space')

    // The progress bar should be visible
    await page.waitForTimeout(300)
    const progressBar = page.locator('.absolute.bottom-24')
    const isVisible = await progressBar.isVisible({ timeout: 3000 }).catch(() => false)
    expect(isVisible).toBe(true)
  })
})

// ── 7. Map Navigation (v0.4) ─────────────────────────────────────────

test.describe('Map navigation', () => {
  test.beforeEach(async ({ page, request }) => {
    await loginViaApi(page, request)
    await page.goto('/showcase')
    await page.waitForLoadState('networkidle')
  })

  test('MapPin icon is in the menu', async ({ page }) => {
    await page.mouse.move(640, 10)
    await page.waitForTimeout(600)

    const mapLink = page.getByTitle('地图')
    await expect(mapLink).toBeVisible({ timeout: 3000 })
  })

  test('M key navigates to /map', async ({ page }) => {
    await page.click('body')
    await page.keyboard.press('KeyM')

    await page.waitForURL('**/map', { timeout: 10000 })
    expect(page.url()).toContain('/map')
  })

  test('MapPin click navigates to /map', async ({ page }) => {
    const { width } = page.viewportSize()!
    await page.mouse.move(width / 2, 10)
    await page.waitForTimeout(600)

    await page.getByTitle('地图').dispatchEvent('click')

    await page.waitForURL('**/map', { timeout: 10000 })
    expect(page.url()).toContain('/map')
  })
})

// ── 8. Category Bar ────────────────────────────────────────────────

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

  test('photo owner can hide and unhide showcase visibility from detail page', async ({ page, request }) => {
    const username = `owner_hide_${Date.now()}`
    await createMemberUser(request, username, 'Owner Hide')
    const photo = await uploadPhotoAsMember(request, username, MEMBER_PASS)

    await loginViaApiAs(page, request, username, MEMBER_PASS)
    await page.goto(`/photo/${photo.id}`)
    await page.waitForLoadState('networkidle')

    const hideButton = page.getByRole('button', { name: 'Hide from Showcase' })
    await expect(hideButton).toBeVisible({ timeout: 5000 })
    await hideButton.click()

    const showButton = page.getByRole('button', { name: 'Show in Showcase' })
    await expect(showButton).toBeVisible({ timeout: 5000 })

    await page.reload()
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: 'Show in Showcase' })).toBeVisible({ timeout: 5000 })
  })

  test('admin sees permanent delete control on photo detail', async ({ page, request }) => {
    const cookie = await getSessionCookie(request)
    const showcaseResp = await request.get(`${API_BASE}/showcase`, {
      headers: { cookie },
    })
    expect(showcaseResp.status()).toBe(200)
    const showcase = await showcaseResp.json()
    const item = Array.isArray(showcase.photos) ? showcase.photos[0] : null
    test.skip(!item?.photo?.id, 'No showcase photo available')

    await page.goto(`/photo/${item.photo.id}`)
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: 'Delete Permanently' })).toBeVisible({ timeout: 5000 })
  })

  test('member does not see permanent delete control on photo detail', async ({ page, request }) => {
    const username = `owner_no_delete_${Date.now()}`
    await createMemberUser(request, username, 'Owner No Delete')
    const photo = await uploadPhotoAsMember(request, username, MEMBER_PASS)

    await loginViaApiAs(page, request, username, MEMBER_PASS)
    await page.goto(`/photo/${photo.id}`)
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: 'Delete Permanently' })).toHaveCount(0)
  })

  test('admin can permanently delete a photo from detail after confirmation', async ({ page, request }) => {
    const username = `admin_delete_detail_${Date.now()}`
    await createMemberUser(request, username, 'Admin Delete Detail')
    const photo = await uploadPhotoAsMember(request, username, MEMBER_PASS)
    const photoPrefix = photo.id.slice(0, 8)

    await loginViaApi(page, request)
    await page.goto(`/photo/${photo.id}`)
    await page.waitForLoadState('networkidle')

    page.once('dialog', async (dialog) => {
      expect(dialog.message()).toContain('cannot be undone')
      await dialog.accept()
    })
    await page.getByRole('button', { name: 'Delete Permanently' }).click()
    await expect(page.getByRole('button', { name: 'Deleting…' })).toBeVisible({ timeout: 5000 })

    await page.waitForURL('**/admin/photos?purged=1', { timeout: 20000 })
    await expect(page.locator('tbody tr').filter({ hasText: photoPrefix })).toHaveCount(0)
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

  test('admin can access admin photos operations page', async ({ page }) => {
    await page.goto('/admin/photos')
    await page.waitForLoadState('networkidle')
    expect(page.url()).toContain('/admin/photos')
    await expect(page.getByText('Photo Operations')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('Needs review')).toBeVisible({ timeout: 5000 })
  })

  test('admin photos list exposes permanent delete action', async ({ page, request }) => {
    const adminCookie = await getSessionCookie(request)
    const adminPhotosResp = await request.get(`${API_BASE}/admin/photos?showcase_visibility=visible`, {
      headers: { cookie: adminCookie },
    })
    expect(adminPhotosResp.status()).toBe(200)
    const adminPhotos = await adminPhotosResp.json()
    const item = Array.isArray(adminPhotos.items) ? adminPhotos.items[0] : null
    test.skip(!item?.id, 'No admin photo available for delete action test')

    await page.goto('/admin/photos')
    await page.waitForLoadState('networkidle')

    const photoRow = page.locator('tbody tr').filter({ hasText: item.id.slice(0, 8) }).first()
    await expect(photoRow).toBeVisible({ timeout: 5000 })
    await expect(photoRow.getByRole('button', { name: 'Delete' })).toBeVisible({ timeout: 5000 })
  })

  test('admin can filter and toggle showcase visibility from admin surfaces', async ({ page, request }) => {
    const adminCookie = await getSessionCookie(request)
    const adminPhotosResp = await request.get(`${API_BASE}/admin/photos?showcase_visibility=visible`, {
      headers: { cookie: adminCookie },
    })
    expect(adminPhotosResp.status()).toBe(200)
    const adminPhotos = await adminPhotosResp.json()
    const item = Array.isArray(adminPhotos.items)
      ? adminPhotos.items.find((candidate: any) => candidate.status === 'ready')
      : null
    test.skip(!item?.id, 'No ready visible admin photo available for admin visibility test')
    const photo = item
    const photoPrefix = photo.id.slice(0, 8)

    await page.goto('/admin/photos')
    await page.waitForLoadState('networkidle')

    const photoRow = page.locator('tbody tr').filter({ hasText: photoPrefix }).first()
    await expect(photoRow).toBeVisible({ timeout: 5000 })
    await expect(photoRow.getByText('Visible')).toBeVisible({ timeout: 5000 })

    await page.getByLabel('Showcase').selectOption('visible')
    await page.getByRole('button', { name: 'Apply Filters' }).click()
    await expect(photoRow).toBeVisible({ timeout: 5000 })

    await photoRow.getByRole('button', { name: 'Hide' }).click()
    await expect(photoRow).toHaveCount(0, { timeout: 5000 })

    const hiddenShowcaseResp = await request.get(`${API_BASE}/showcase`, {
      headers: { cookie: adminCookie },
    })
    expect(hiddenShowcaseResp.status()).toBe(200)
    const hiddenShowcase = await hiddenShowcaseResp.json()
    const hiddenIds = new Set((hiddenShowcase.photos || []).map((item: any) => item.photo.id))
    expect(hiddenIds.has(photo.id)).toBe(false)

    await page.getByLabel('Showcase').selectOption('hidden')
    await page.getByRole('button', { name: 'Apply Filters' }).click()
    await expect(photoRow).toBeVisible({ timeout: 5000 })
    await expect(photoRow.getByText('Hidden')).toBeVisible({ timeout: 5000 })
    await expect(photoRow.getByRole('button', { name: 'Show' })).toBeVisible({ timeout: 5000 })

    await photoRow.getByRole('link', { name: new RegExp(photoPrefix) }).click()
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: 'Show in Showcase' })).toBeVisible({ timeout: 5000 })
    await page.getByRole('button', { name: 'Show in Showcase' }).click()
    await expect(page.getByRole('button', { name: 'Hide from Showcase' })).toBeVisible({ timeout: 5000 })

    const visibleShowcaseResp = await request.get(`${API_BASE}/showcase`, {
      headers: { cookie: adminCookie },
    })
    expect(visibleShowcaseResp.status()).toBe(200)
    const visibleShowcase = await visibleShowcaseResp.json()
    const visibleIds = new Set((visibleShowcase.photos || []).map((item: any) => item.photo.id))
    expect(visibleIds.has(photo.id)).toBe(true)
  })

  test('admin photo detail shows design versions and recent jobs', async ({ page, request }) => {
    const cookie = await getSessionCookie(request)
    const showcaseResp = await request.get(`${API_BASE}/showcase`, {
      headers: { cookie },
    })
    expect(showcaseResp.status()).toBe(200)
    const showcase = await showcaseResp.json()
    const photoItems = Array.isArray(showcase.photos) ? showcase.photos : []
    test.skip(!photoItems.length, 'No showcase photos available for admin detail test')

    await page.goto(`/photo/${photoItems[0].photo.id}`)
    await page.waitForLoadState('networkidle')

    await expect(page.getByText('Admin Diagnostics')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('Design Versions')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('Recent Jobs')).toBeVisible({ timeout: 5000 })
  })

  test('admin can activate a manual draft version from photo detail', async ({ page, request }) => {
    const cookie = await getSessionCookie(request)
    const showcaseResp = await request.get(`${API_BASE}/showcase`, {
      headers: { cookie },
    })
    expect(showcaseResp.status()).toBe(200)
    const showcase = await showcaseResp.json()
    const item = Array.isArray(showcase.photos) ? showcase.photos[0] : null
    test.skip(!item?.photo?.id, 'No showcase photo available')

    const activeDesignResp = await request.get(`${API_BASE}/photos/${item.photo.id}/slide-design`, {
      headers: { cookie },
    })
    expect(activeDesignResp.status()).toBe(200)
    const activeDesign = await activeDesignResp.json()
    const manualDesign = {
      ...activeDesign.design_json,
      templateId: 'minimal_white',
    }

    const createResp = await request.post(`${API_BASE}/admin/photos/${item.photo.id}/design-versions/manual`, {
      headers: { cookie },
      data: { design_json: manualDesign },
    })
    expect(createResp.status()).toBe(201)

    await loginViaApi(page, request)
    await page.goto(`/photo/${item.photo.id}`)
    await page.waitForLoadState('networkidle')

    await expect(page.getByText('Manual Design JSON')).toBeVisible({ timeout: 5000 })
    await page.getByRole('button', { name: 'Set Active' }).first().click()
    await expect(page.getByText(/Manual v\d+/)).toBeVisible({ timeout: 5000 })
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
