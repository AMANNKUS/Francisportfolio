# Publish this portfolio with GitHub Pages

The website is complete and uses relative links, so it works as either a user site or a project site. No build tool or paid service is required.

1. Sign in to your GitHub account. Use the exact username shown on your profile.
2. Create a **public** repository named `YOUR_GITHUB_USERNAME.github.io` for a user site. If that repository already contains a website you want to keep, create a separate repository named `data-analytics-portfolio` instead.
3. Upload the **contents** of this folder into the repository root. `index.html` must be at the top level, alongside `styles.css`, `script.js`, `assets/` and `projects/`. Do not upload the ZIP itself or place everything inside another folder.
4. Commit the files to the `main` branch.
5. Open **Settings → Pages**. Under **Build and deployment**, choose **Deploy from a branch**, then **main** and **/ (root)**. Save.
6. Wait for the Pages deployment to succeed. Open the website link displayed by GitHub in **Settings → Pages** and check the home page, case-study page and downloads.

For a user site, the address will be `https://YOUR_GITHUB_USERNAME.github.io/`. For a project site, it will be `https://YOUR_GITHUB_USERNAME.github.io/data-analytics-portfolio/`.

The `.nojekyll` file is included to serve these static files without Jekyll processing. Keep the folder structure unchanged. GitHub Pages does not require the `.openai` preview configuration or a `dist` folder; neither is included in the upload package.

## Optional: show GitHub profile and repository links

After the repository name is confirmed, change the opening `<html lang="en">` tag in **both** `index.html` and `projects/bellabeat/index.html` to:

```html
<html lang="en" data-github-username="YOUR_GITHUB_USERNAME" data-github-repository="YOUR_REPOSITORY_NAME">
```

Replace the two values with the actual username and repository name. The shared script then shows working profile and repository links. Those links stay hidden until configured.

## Official guidance

- [GitHub Pages quickstart](https://docs.github.com/en/pages/quickstart)
- [Configure a publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

Do not commit passwords, tokens or private data. The included files contain no login credentials.
