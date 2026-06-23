# RentWise Nairobi

RentWise is a caretaker-first rental discovery MVP for Nairobi. It supports public rental browsing, map-based search, caretaker listing management, building/unit image uploads, a product-style admin portal, and a Gemini/local-fallback assistant.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py load_sample_data
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

Admin portal:

```text
http://127.0.0.1:8000/admin/
```

Raw Django admin:

```text
http://127.0.0.1:8000/django-admin/
```

Sample logins after `load_sample_data`:

```text
Platform admin: platformadmin / admin12345
Caretaker: caretaker / caretaker12345
Caretaker 2: caretaker2 / caretaker12345
Caretaker 3: caretaker3 / caretaker12345
House seeker: demo / demo12345
```

## Production deployment

Use `DEPLOYMENT.md` for the real online setup. This build includes production-ready settings for PostgreSQL, Gunicorn, WhiteNoise, HTTPS security toggles, and persistent media configuration.

Do not commit real `.env` secrets to GitHub.

## Wider MVP Launch Features

This build includes the post-live-test safeguards:

- Caretaker approval before listings are public.
- Admin phone verification before listings are public.
- Caretakers can still prepare draft buildings and units while waiting for approval.
- Public search and assistant only show approved, phone-verified caretaker listings.
- Admin analytics page: `/admin/analytics/`.
- Terms, privacy, and contact pages.
- Optional Sentry error monitoring through `SENTRY_DSN`.
- Backup command: `python manage.py backup_data`.

Admin workflow: log in at `/admin/`, open a caretaker profile, then use **Approve Caretaker** and **Mark Phone Verified** before their listings go public.

## House seeker accounts and saved homes

Browsing remains open to guests. House seekers only need an account when they want to save homes and return to them later.

- House seeker signup: `/seeker-signup/`
- House seeker dashboard: `/account/`
- Public building pages include a **Save This Home** action for signed-in house seekers.
- Saved homes now bookmark specific units and show the unit type, rent, move-in cost, building name, area, landmark, view link, call caretaker link, and remove action.
- Caretaker signup remains separate at `/signup/` with the wording: **Caretaker? Create Your Profile And Listings**.

Sample data includes the demo house seeker account:

```text
demo / demo12345
```

After running `python manage.py load_sample_data`, the demo account has a small saved-home shortlist for local testing.

## Latest UI Update

This package includes the improved Zillow-inspired presentation layer:

- A photo-style illustrated hero background showing Nairobi apartment life.
- Smoother Cormorant Garamond + Manrope type scale and weights.
- Cleaner, flatter buttons that stay inside their containers.
- Unit-level bookmark controls with an apartment bookmark icon.
- Logged-out visitors see a sign-in prompt in the bookmark position instead of being allowed to save.
- Saved homes show a Remove Bookmark control with the same icon system.

Run the app as usual, then load sample data to test the complete flow.
