
const { test, expect } = require('@playwright/test');

// Environnement E2E isolé
const TEST_UI = 'http://127.0.0.1:13000';
const TEST_API = 'http://127.0.0.1:18082';

async function login(page, email, password = 'Demo12345!') {
  await page.goto(TEST_UI);

  await page.getByLabel('Adresse e-mail').fill(email);
  await page.getByLabel('Mot de passe').fill(password);
  await page.getByRole('button', { name: /Se connecter/i }).click();

  await expect(page.locator('.user-menu')).toBeVisible();
}

async function gotoSection(page, label) {
  await page
    .locator('aside.sidebar nav')
    .getByRole('button', { name: label, exact: true })
    .click();

  // Le libellé du menu peut différer du titre de la page.
  const expectedTitles = {
    'Pièces & stock': 'Pièces détachées'
  };

  await expect(page.locator('.page-heading h1'))
    .toHaveText(expectedTitles[label] || label);
}

// Vérifier que les tests utilisent bien l'API E2E.
test.beforeAll(async ({ request }) => {
  const response = await request.get(
    `${TEST_API}/api/health`,
    { timeout: 10000 }
  );

  expect(
    response.status(),
    'Le serveur E2E sur le port 18082 doit être démarré'
  ).toBe(200);

  expect((await response.json()).service).toBe('garagepro');
});

// E2E-01 : Formulaire de connexion
test('E2E-01 - Formulaire de connexion visible', async ({ page }) => {
  await page.goto(TEST_UI);

  await expect(
    page.getByRole('heading', { name: 'Connexion' })
  ).toBeVisible();

  await expect(page.getByLabel('Adresse e-mail')).toBeVisible();
  await expect(page.getByLabel('Mot de passe')).toBeVisible();
});

// E2E-02 : Mot de passe incorrect
test('E2E-02 - Refus d’un mauvais mot de passe', async ({ page }) => {
  await page.goto(TEST_UI);

  await page.getByLabel('Adresse e-mail').fill('admin@gmail.com');
  await page.getByLabel('Mot de passe').fill('MauvaisMotDePasse123!');

  await page
    .getByRole('button', { name: /Se connecter/i })
    .click();

  await expect(
    page.locator('.login-card .error')
  ).toContainText('Identifiants invalides');

  await expect(page.locator('.user-menu')).toHaveCount(0);
});

// E2E-03 : ADMIN
test('E2E-03 - Connexion ADMIN et accès aux pages administrateur', async ({ page }) => {
  await login(page, 'admin@gmail.com');

  await gotoSection(page, 'Utilisateurs');

  await expect(
    page.locator('.toolbar button.primary', { hasText: 'Ajouter' })
  ).toBeVisible();

  await gotoSection(page, 'Pièces & stock');

  await expect(
    page.locator('.table-card')
  ).toBeVisible();
});

// E2E-04 : Contrôle des permissions CLIENT
test('E2E-04 - Le CLIENT ne voit pas la création d’intervention', async ({ page }) => {
  await login(page, 'client@gmail.com');

  await gotoSection(page, 'Interventions');

  await expect(
    page.locator('.toolbar button.primary', { hasText: 'Ajouter' })
  ).toHaveCount(0);

  await expect(page.locator('.table-card')).toBeVisible();
});

// E2E-05 : Formulaire véhicule CLIENT
test('E2E-05 - Le CLIENT peut ouvrir le formulaire véhicule', async ({ page }) => {
  await login(page, 'client@gmail.com');

  await gotoSection(page, 'Véhicules');

  await page
    .locator('.toolbar button.primary', { hasText: 'Ajouter' })
    .click();

  const modal = page.locator('.modal');

  await expect(modal).toBeVisible();

  await expect(
    page.getByRole('heading', { name: 'Nouvel enregistrement' })
  ).toBeVisible();

  await expect(modal.getByText('Immatriculation')).toBeVisible();
  await expect(modal.getByText('Modèle')).toBeVisible();

  await page.getByRole('button', { name: 'Annuler' }).click();

  await expect(modal).toHaveCount(0);
});

// E2E-06 : Formulaire de rendez-vous CLIENT
test('E2E-06 - Le CLIENT peut ouvrir un rendez-vous', async ({ page }) => {
  await login(page, 'client@gmail.com');

  await gotoSection(page, 'Rendez-vous');

  await page
    .locator('.toolbar button.primary', { hasText: 'Ajouter' })
    .click();

  const modal = page.locator('.modal');

  await expect(modal).toBeVisible();

  await expect(
    modal.getByRole('heading', { name: 'Nouvel enregistrement' })
  ).toBeVisible();

  // Vérifier qu'il s'agit d'un formulaire interactif.
  const fields = modal.locator('input, select, textarea');

  await expect(fields.first()).toBeVisible();

  // Vérifier l'annulation du formulaire.
  await page.getByRole('button', { name: 'Annuler' }).click();

  await expect(modal).toHaveCount(0);
});

// E2E-07 : Permissions MÉCANICIEN
test('E2E-07 - Le MÉCANICIEN voit ses menus sans création intervention', async ({ page }) => {
  await login(page, 'mecanicien@gmail.com');

  await gotoSection(page, 'Rendez-vous');

  await expect(
    page.locator('.table-card')
  ).toBeVisible();

  await gotoSection(page, 'Interventions');

  await expect(
    page.locator('.toolbar button.primary', { hasText: 'Ajouter' })
  ).toHaveCount(0);
});

// E2E-08 : Déconnexion
test('E2E-08 - Déconnexion depuis le compte ADMIN', async ({ page }) => {
  await login(page, 'admin@gmail.com');

  await page
    .getByRole('button', { name: 'Déconnexion' })
    .click();

  await expect(
    page.getByRole('heading', { name: 'Connexion' })
  ).toBeVisible();

  await expect(page.locator('.user-menu')).toHaveCount(0);
});
