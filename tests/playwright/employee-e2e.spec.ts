import { test, expect } from '@playwright/test';
import { execSync } from 'node:child_process';

const employeeEmail = process.env.EMPLOYEE_EMAIL;
const employeePassword = process.env.EMPLOYEE_PASSWORD;
const previewUrl = process.env.PREVIEW_URL;

const requireEnv = () => {
  if (!employeeEmail || !employeePassword || !previewUrl) {
    test.skip(true, 'PREVIEW_URL, EMPLOYEE_EMAIL, and EMPLOYEE_PASSWORD must be set');
  }
};

test('employee can invite client and deliver model link end-to-end', async ({ page, context }) => {
  requireEnv();

  const uniqueStamp = Date.now();
  const clientEmail = `modelclient+${uniqueStamp}@spcprt.dev`;
  const clientPassword = `Client${uniqueStamp.toString().slice(-4)}Aa!`;
  const projectId = `automation-project-${uniqueStamp}`;
  const epoch = Math.floor(Date.now() / 1000).toString();
  const deliveryLink = `https://viewer.spaceport.ai/demo-${uniqueStamp}`;

  // Employee login
  await page.goto('/create');
  await page.getByRole('button', { name: 'Login' }).click();
  await page.getByPlaceholder(/email/i).fill(employeeEmail!);
  await page.getByPlaceholder(/password/i).fill(employeePassword!);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByText('New Project')).toBeVisible({ timeout: 20_000 });

  // Beta access invite
  await expect(page.getByText('Beta Access Management')).toBeVisible({ timeout: 20_000 });
  await page.getByPlaceholder('Enter email address').fill(clientEmail);
  await page.getByRole('button', { name: 'Grant Access' }).click();
  await expect(page.getByText(/Invitation sent successfully/i)).toBeVisible({ timeout: 15_000 });

  // Provision client credentials & project using AWS CLI
  execSync(
    `aws cognito-idp admin-set-user-password --profile spaceport-dev --user-pool-id us-west-2_a2jf3ldGV --username ${clientEmail} --password '${clientPassword}' --permanent`,
    { stdio: 'inherit' }
  );
  const userSub = execSync(
    `aws cognito-idp admin-get-user --profile spaceport-dev --user-pool-id us-west-2_a2jf3ldGV --username ${clientEmail} --query "UserAttributes[?Name=='sub'].Value" --output text`,
    { encoding: 'utf-8' }
  ).trim();
  const putItemCommand = `aws dynamodb put-item --profile spaceport-dev --table-name Spaceport-Projects-staging --item '{"userSub":{"S":"${userSub}"},"projectId":{"S":"${projectId}"},"title":{"S":"Automation Test Project"},"status":{"S":"draft"},"progress":{"N":"5"},"createdAt":{"N":"${epoch}"},"updatedAt":{"N":"${epoch}"},"email":{"S":"${clientEmail}"},"params":{"M":{}}}'`;
  execSync(putItemCommand, { stdio: 'inherit' });

  // Send model link from employee account
  await page.getByRole('button', { name: 'Send Model Link' }).click();
  const modalOverlay = page.locator('.model-delivery-modal-overlay');
  await expect(modalOverlay).toBeVisible();
  await page.locator('#client-email').fill(clientEmail);
  await page.getByRole('button', { name: 'Lookup' }).click();
  await page.waitForTimeout(2000);
  await page.locator('#project-select').selectOption(projectId);
  await page.locator('#model-link-input').fill(deliveryLink);
  await page.getByRole('button', { name: 'Send to client' }).click();
  await expect(page.getByText(/Model link sent successfully/i)).toBeVisible({ timeout: 15_000 });
  await page.getByRole('button', { name: 'Cancel' }).click();
  await expect(modalOverlay).not.toBeVisible();

  // Sign out employee
  await page.getByRole('button', { name: 'Sign Out' }).click();
  await expect(page.getByRole('button', { name: 'Login' })).toBeVisible();

  // Client login to confirm link
  const clientPage = await context.newPage();
  await clientPage.goto('/create');
  await clientPage.getByRole('button', { name: 'Login' }).click();
  await clientPage.getByPlaceholder(/email/i).fill(clientEmail);
  await clientPage.getByPlaceholder(/password/i).fill(clientPassword);
  await clientPage.getByRole('button', { name: 'Sign in' }).click();
  await expect(clientPage.getByText('Automation Test Project')).toBeVisible({ timeout: 20_000 });
  await expect(clientPage.locator('.model-link-pill')).toBeVisible();
  await expect(clientPage.getByText(`viewer.spaceport.ai/demo-${uniqueStamp}`)).toBeVisible();
});
