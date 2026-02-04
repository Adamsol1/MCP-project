import { test, expect } from '@playwright/test';

//Test to check if file upload component is visible
test('file upload component is visible', async ({ page }) => {
  //Update this url to where the upload will be
  await page.goto('/');


  //Check that file upload functionality is displayed
  await expect(page.getByText('Drag & drop files here')).toBeVisible();
  await expect(page.getByText('or click to browse')).toBeVisible();
  await expect(page.getByText('Supported: .json, .csv, .pdf, .txt')).toBeVisible();



});

//Test for uploading a file. Uses a test file. Will fail if test file is deleted
test('uploaded file is shown', async ({ page })=> {
  //Important, we have to update this url for when we find were it will be placed
  await page.goto('/')

  //Find file input element
  const fileInput = page.locator('input[type="file"]');
  //Upload file
  await fileInput.setInputFiles('./tests/testFileUsedForTesting.txt')
  //Check if the uploaded file is there
  await expect(page.getByText('testFileUsedForTesting.txt')).toBeVisible();
})

//Test for removing files when pressing cancel
test('Cancel button removing selected files', async ({ page }) => {
  //Important, we have to update this url for when we find were it will be placed
  await page.goto('/')

  //Select files and upload
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles('./tests/testFileUsedForTesting.txt')

  //Find element
  const testFile = page.getByText('testFileUsedForTesting.txt')

  //Check that it is visible
  await expect(testFile).toBeVisible();



  //Press cancel
  await page.getByRole('button', {name: 'Cancel'}).click();

  //Expect nothing visible and files are gone
  await expect(testFile).not.toBeVisible();


})

test('submit button is disabled before fileupload', async ({ page }) => {
    //Important, we have to update this url for when we find were it will be placed
    await page.goto('/')

    //Get button element
    const submitButton = await page.getByRole('button', {name: 'Submit'})

    //Check if button is disabled
    await expect(submitButton).toBeDisabled();


})


test('submit button is enabled after fileupload', async ({ page }) => {
    //Important, we have to update this url for when we find were it will be placed
    await page.goto('/')

    //Get button element
    const submitButton = await page.getByRole('button', {name: 'Submit'})

    //Select files and upload
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('./tests/testFileUsedForTesting.txt')

    //Check if button is enabled
    await expect(submitButton).toBeEnabled();


})

test('remove button removes given file', async ({ page }) => {
    //Important, we have to update this url for when we find were it will be placed
    await page.goto('/')

    //Select files and upload
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('./tests/testFileUsedForTesting.txt')

    //Finds the connected remove button for uploaded file
    await page
      .locator('div', {hasText: 'testFileUsedForTesting.txt'})
      .getByRole('button', {name: "Remove"})
      .click()

    //Check the count of the file to determin if it has beebn removed
    await expect(page.locator('div', { hasText: 'testFileUsedForTesting.txt' })).toHaveCount(0);
})


test('multiple files can be uploaded', async ({ page }) => {
  //Important, we have to update this url for when we find were it will be placed
  await page.goto('/');

  //Find file input element
  const fileInput = page.locator('input[type="file"]');

  // Upload two files
  await fileInput.setInputFiles(['./tests/testFileUsedForTesting.txt', './tests/testFileUsedForTesting2.txt']);

  // Check that both files are visible
  await expect(page.getByText('testFileUsedForTesting.txt')).toBeVisible();
  await expect(page.getByText('testFileUsedForTesting2.txt')).toBeVisible();
});

test('file size is displayed', async ({ page }) => {
  await page.goto('/');


  //Upload file
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles('./tests/testFileUsedForTesting.txt');

  //Check if file size is visible
  await expect(page.getByText(/bytes|KB/)).toBeVisible();
});
