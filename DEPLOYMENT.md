# RentWise Production Deployment Guide

This build is prepared for a fast real-world MVP launch using:

- Django 5.2 LTS
- PostgreSQL through `DATABASE_URL`
- Gunicorn
- WhiteNoise for static files
- Persistent uploaded-media storage through `MEDIA_ROOT`
- OpenStreetMap/Leaflet for map display
- Gemini API for optional free-tier AI assistant
- Local database fallback if Gemini is unavailable

## Recommended first host

Use Render or Railway for the first launch. Both can connect to GitHub, provide PostgreSQL, expose environment variables, and give you a public HTTPS URL.

For the fastest path, use Render because it has a straightforward Django + PostgreSQL flow and supports persistent disks for uploaded images.

## Before deploying

Do not upload this directly as a ZIP to the server. Put the folder in a GitHub repository first.

From your local project folder:

```powershell
git init
git add .
git commit -m "Prepare RentWise production MVP"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

## Production environment variables

Set these in the hosting provider dashboard, not inside GitHub.

```env
SECRET_KEY=generate-a-long-random-secret-key
DEBUG=False
ALLOWED_HOSTS=your-app.onrender.com,yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://your-app.onrender.com,https://yourdomain.com,https://www.yourdomain.com
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME
DB_SSL_REQUIRE=True
DB_CONN_MAX_AGE=600
MAP_PROVIDER=osm
GEOCODER_PROVIDER=nominatim
AI_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-1.5-flash
MEDIA_ROOT=/var/data/rentwise_media
MEDIA_URL=/media/
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=0
```

Keep `SECURE_HSTS_SECONDS=0` at the beginning. After your custom domain and HTTPS are stable, you can increase it gradually.

## Render setup

1. Create a Render account.
2. Push this project to GitHub.
3. In Render, create a PostgreSQL database.
4. Copy the database `DATABASE_URL`.
5. Create a Web Service from your GitHub repo.
6. Set the build command:

```bash
./build.sh
```

7. Set the start command:

```bash
python manage.py migrate && gunicorn rentwise.wsgi:application --log-file -
```

8. Add the environment variables listed above.
9. Add a persistent disk for uploaded images:

```text
Mount path: /var/data
MEDIA_ROOT: /var/data/rentwise_media
```

10. Deploy.
11. Open the Render Shell and create the first real admin:

```bash
python manage.py createsuperuser
```

Or use the environment-variable command:

```bash
ADMIN_USERNAME=youradmin ADMIN_EMAIL=you@example.com ADMIN_PASSWORD='strong-password-here' python manage.py create_platform_admin
```

12. Open:

```text
https://your-app.onrender.com/admin/
```

## Railway setup

1. Create a Railway account.
2. Push this project to GitHub.
3. Create a new Railway project from your GitHub repo.
4. Add a PostgreSQL service.
5. Copy the PostgreSQL `DATABASE_URL` into the web service environment variables.
6. Add all environment variables listed above.
7. Set the start command:

```bash
python manage.py migrate && python manage.py collectstatic --no-input && gunicorn rentwise.wsgi:application --log-file -
```

8. Generate a public domain in Railway Networking.
9. Update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` with that domain.
10. Create your production admin from the Railway shell.

## Media/image uploads

Uploaded building and unit images need persistent storage.

For the first launch, a host persistent disk/volume is acceptable. Later, migrate media to object storage such as S3-compatible storage, Cloudinary, or another image CDN.

If you deploy without persistent media storage, uploaded images may disappear after a redeploy or container restart.

## What not to do in production

Do not run production with:

```env
DEBUG=True
```

Do not use sample passwords for real admin accounts.

Do not run `load_sample_data` on the live database unless you intentionally want demo listings visible.

Do not commit `.env` to GitHub.

## First launch checklist

- Production PostgreSQL connected
- `DEBUG=False`
- Strong `SECRET_KEY`
- Correct `ALLOWED_HOSTS`
- Correct `CSRF_TRUSTED_ORIGINS`
- HTTPS working
- Admin account created
- Test caretaker signup
- Test building image upload
- Test unit image upload
- Test public search
- Test assistant with Gemini key
- Test fallback assistant by temporarily removing Gemini key
- Test on phone screen size
- Confirm contact/call buttons work
- Confirm fake/demo data is removed if not wanted

## Suggested MVP operating rules

- Only approved caretakers should be allowed to publish real listings.
- Start with a small pilot area, for example Roysambu, Kasarani, Kahawa, and Ruiru.
- Manually verify caretaker phone numbers before approving many listings.
- Back up PostgreSQL regularly.
- Watch API usage and server logs daily during launch.

## After the first live test: safety and operations added in this build

This version adds the next MVP safeguards before wider public use:

- Caretaker approval before public publishing
- Admin phone verification flag before listings show publicly
- Suspended caretakers have their buildings hidden automatically
- Public search, public building pages, and assistant recommendations only use approved + phone-verified caretaker listings
- Lightweight admin analytics at `/admin/analytics/`
- Terms, privacy, and contact pages
- Optional Sentry error monitoring through `SENTRY_DSN`
- Timestamped database backup command

### Caretaker approval workflow

1. A caretaker signs up from the public create-account button.
2. They can log in and add buildings/units as drafts.
3. Their listings stay hidden until admin approves them and marks the phone verified.
4. Admin opens `/admin/`, selects the caretaker, then uses:
   - Approve Caretaker
   - Mark Phone Verified
5. After both are done, the caretaker can publish visible listings.

### Admin analytics

Open:

```text
https://your-domain.com/admin/analytics/
```

This shows early launch searches, viewing requests, and assistant usage. It is intentionally simple and database-backed so the MVP does not depend on Google Analytics or another tracker.

### Backups

Run this from the hosting shell when needed:

```bash
python manage.py backup_data
```

For Render with persistent disk, set:

```env
BACKUP_DIR=/var/data/rentwise_backups
```

This does not replace provider-level PostgreSQL backups, but it gives you a quick JSON export for MVP operations.

### Error monitoring

Optional but recommended after launch:

1. Create a free Sentry project for Django.
2. Copy the DSN.
3. Add it to your host environment variables:

```env
SENTRY_DSN=your-sentry-dsn-here
SENTRY_TRACES_SAMPLE_RATE=0.05
```

If `SENTRY_DSN` is empty, the app runs normally with console logging only.

## House seeker accounts

The production build supports optional house seeker accounts for saved homes. Do not force account creation for browsing; use accounts only for bookmarking, shortlist management, and future alerts.

Useful URLs:

```text
/seeker-signup/  - house seeker account creation
/account/        - saved homes dashboard
/signup/         - caretaker profile/listing creation
```

For production launch, keep guest browsing open and promote account creation only when the user clicks save/bookmark.

## Render Python / psycopg guardrail

This project includes both `.python-version` and `runtime.txt` so Render does not fall back to its newest default Python runtime. Render's current default for new services can be Python 3.14.3, which may be ahead of some binary wheels. Keep `.python-version` in the repository root.

The PostgreSQL driver is pinned as `psycopg[binary]>=3.2.10,<4.0` instead of one exact old patch version. This avoids deploy failures when Render uses a newer Python patch level and a specific older `psycopg-binary` wheel is not published for that runtime.

If Render still starts with Python 3.14, set this environment variable manually in the Render dashboard:

```text
PYTHON_VERSION=3.13.5
```

Then redeploy manually.

## Automatic image compression

Caretakers can upload normal phone photos. RentWise now compresses building and unit photos before saving them:

- maximum accepted upload: `RENTWISE_MAX_IMAGE_UPLOAD_MB` (default `8` MB)
- saved image max width: `RENTWISE_IMAGE_MAX_WIDTH` (default `1600` px)
- saved image max height: `RENTWISE_IMAGE_MAX_HEIGHT` (default `1200` px)
- JPEG quality: `RENTWISE_IMAGE_JPEG_QUALITY` (default `80`)

The saved files are JPEGs. In normal rental photos this should keep most images roughly in the 200 KB to 900 KB range, depending on detail and lighting.

## Cloudflare R2 media storage

Local development still uses normal Django media storage. For production image storage on Cloudflare R2, add these environment variables in Render after your bucket and public/custom domain are ready:

```env
USE_S3_MEDIA=True
CLOUDFLARE_R2_ACCESS_KEY_ID=your-r2-access-key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your-r2-secret-key
CLOUDFLARE_R2_BUCKET_NAME=your-bucket-name
CLOUDFLARE_R2_ENDPOINT_URL=https://ACCOUNT_ID.r2.cloudflarestorage.com
CLOUDFLARE_R2_REGION=auto
CLOUDFLARE_R2_MEDIA_PREFIX=media
CLOUDFLARE_R2_PUBLIC_BASE_URL=https://your-public-r2-domain
```

Keep R2 keys in Render environment variables only. Do not commit them to GitHub.

## Assistant without full page reload

The assistant page now submits messages with JavaScript and receives a JSON reply. If JavaScript fails, the normal Django POST still works as a fallback.
