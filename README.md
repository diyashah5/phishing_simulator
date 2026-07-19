# Phishing Simulator

A Flask-based phishing awareness simulator for admin-driven training campaigns.

## Features

- Admin login and dashboard
- Create phishing campaigns with target email lists
- Generate campaign-specific phishing URLs
- Track opens, clicks, and submitted credentials
- Export campaign results to CSV
- Manage user groups and email templates
- Display an awareness page after credential submission

## Repository Structure

- `app.py` - Main Flask application and route handlers
- `templates/` - HTML templates for admin and phishing pages
- `static/` - CSS and static assets
- `phishing.db` - SQLite database created automatically
- `captured_credentials.txt` - Log of submitted credentials and timestamps

## Requirements

- Python 3.8 or newer
- Flask
- Pillow

## Setup

1. Create and activate a Python virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install flask pillow
```

3. Run the application:

```powershell
python app.py
```

4. Open the admin page in your browser:

```text
http://127.0.0.1:10000/admin/login
```

## Default Admin Credentials

- Username: `admin`
- Password: `admin123`

## Usage

1. Log in as the admin user.
2. Create a campaign and add target email addresses.
3. Copy the generated phishing links for each target.
4. Review campaign results and export data as needed.

## Deployment

This project supports environment-based deployment using configurable `BASE_URL` and SMTP credentials:

- **Local**: `BASE_URL=http://127.0.0.1:10000` (defined in `.env`)
- **Production**: Set `BASE_URL=https://your-app.onrender.com` on Render
- **Email**: Configure `MAILTRAP_*` environment variables for automated email delivery

This design ensures seamless operation across development and production environments without code changes.

## Notes

- `phishing.db` is generated automatically on first run.
- Submitted credentials are appended to `captured_credentials.txt`.
- This project is intended for security awareness training only.

## Security Warning

Use this project responsibly. Do not use it for unauthorized phishing or malicious activity.
