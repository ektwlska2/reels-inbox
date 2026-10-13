# Reels inbox: setup

Share a reel from Instagram, and a free GitHub job downloads it, transcribes the speech with
Whisper, grabs the caption and 10 frames (for on-screen text), and saves them in this repo.
Claude then reads `reels/INDEX.md` and the folders it links to.

Everything is free: GitHub Actions gives private repos 2,000 minutes a month, and one reel
takes about 2 to 3 minutes. Nothing runs on your own computer.

## 1. GitHub account and repo (once)

1. Sign up at https://github.com if you don't have an account.
2. Create a new **private** repository called `reels-inbox`. Leave it empty.
3. Connect GitHub to Claude at https://claude.ai/connect-github and allow the Claude app on
   `reels-inbox`. Then tell Claude in the project thread, and it pushes the code here.

## 2. Access token for the shortcut (once)

1. On GitHub: profile picture > **Settings** > **Developer settings** >
   **Personal access tokens** > **Fine-grained tokens** > **Generate new token**.
2. Name it `reels shortcut`. Set expiration to 1 year.
3. **Repository access:** Only select repositories > `reels-inbox`.
4. **Permissions:** Repository permissions > **Contents: Read and write**.
5. Generate it and copy the token (starts with `github_pat_`). Keep it private. It can only
   touch this one repo.

## 3. iPhone shortcut (once)

In the **Shortcuts** app, tap **+** and build this:

1. Tap the name at the top and call it **Send to Claude**.
2. Tap **(i)** > turn on **Show in Share Sheet**. Set it to receive **URLs** and **Text**.
3. Add **Get URLs from Input** (input: Shortcut Input).
4. Add **Get Item from List** > **First Item**.
5. Add **Get Contents of URL** and tap the arrow to expand it:
   - URL: `https://api.github.com/repos/YOUR-GITHUB-NAME/reels-inbox/dispatches`
   - Method: **POST**
   - Headers:
     - `Authorization` = `Bearer github_pat_...` (your token)
     - `Accept` = `application/vnd.github+json`
   - Request Body: **JSON**
     - `event_type` (Text) = `reel`
     - `client_payload` (Dictionary) > add `url` (Text) = the **Item from List** variable
6. Add **Show Notification** with the text `Reel sent to Claude`.

## 4. Use it

In Instagram: **Share** on a reel > **Send to Claude**. The first time, scroll the share row,
tap **More**, and pin it. A couple of minutes later the reel is in `reels/`.

To check a run: the repo's **Actions** tab shows each reel. GitHub emails you if one fails.

## 5. If Instagram blocks the download

Instagram sometimes refuses downloads from GitHub's servers. If runs fail with "login required"
or "rate limit":

1. Make a **spare** Instagram account (don't use your main one) and log in to it in Chrome or
   Firefox on a computer.
2. Install the browser extension **Get cookies.txt LOCALLY** and export cookies for
   instagram.com.
3. In the repo: **Settings** > **Secrets and variables** > **Actions** > **New repository
   secret**. Name it `IG_COOKIES` and paste the whole cookies.txt file.

## Settings you can change

In `.github/workflows/ingest.yml` you can set `WHISPER_MODEL` (`base` is faster, `medium` is
more accurate, `small` is the default) and `MAX_FRAMES`.
