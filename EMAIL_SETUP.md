# Password Reset Email Setup Guide

## Current Setup (Development)
By default, password reset emails print to the console. When users click "Forgot Password?" and submit their email, they'll see a confirmation page, and the reset email will appear in your terminal running `manage.py runserver`.

## Production Email Setup (Gmail Example)

To enable real email delivery using Gmail's SMTP:

1. **Enable Gmail App Password** (if using Gmail):
   - Go to your Google Account: https://myaccount.google.com/
   - Navigate to Security > App passwords
   - Generate an app password for Django
   - Copy the 16-character password

2. **Set Environment Variables** (before running Django):

   **Windows (Command Prompt):**
   ```batch
   set SMTP_HOST=smtp.gmail.com
   set SMTP_PORT=587
   set SMTP_USER=your_email@gmail.com
   set SMTP_PASS=your_16_char_app_password
   set SMTP_TLS=True
   set DEFAULT_FROM_EMAIL=your_email@gmail.com
   
   python manage.py runserver
   ```

   **Windows (PowerShell):**
   ```powershell
   $env:SMTP_HOST="smtp.gmail.com"
   $env:SMTP_PORT="587"
   $env:SMTP_USER="your_email@gmail.com"
   $env:SMTP_PASS="your_16_char_app_password"
   $env:SMTP_TLS="True"
   $env:DEFAULT_FROM_EMAIL="your_email@gmail.com"
   
   python manage.py runserver
   ```

   **Linux/Mac (.bash_profile or .env file):**
   ```bash
   export SMTP_HOST=smtp.gmail.com
   export SMTP_PORT=587
   export SMTP_USER=your_email@gmail.com
   export SMTP_PASS=your_16_char_app_password
   export SMTP_TLS=True
   export DEFAULT_FROM_EMAIL=your_email@gmail.com
   
   python manage.py runserver
   ```

3. **Test the Setup**:
   - Click "Forgot Password?" on the login page
   - Enter a registered user's email
   - Check the user's inbox for a password reset email

## Other Email Providers

### Gmail (without app password)
- SMTP_HOST: smtp.gmail.com
- SMTP_PORT: 587
- SMTP_TLS: True

### Outlook/Hotmail
- SMTP_HOST: smtp.office365.com
- SMTP_PORT: 587
- SMTP_TLS: True

### Mailtrap (for testing)
- SMTP_HOST: live.smtp.mailtrap.io
- SMTP_PORT: 587
- SMTP_TLS: True
- SMTP_USER: Your Mailtrap username
- SMTP_PASS: Your Mailtrap password

### SendGrid
- SMTP_HOST: smtp.sendgrid.net
- SMTP_PORT: 587
- SMTP_TLS: True
- SMTP_USER: apikey
- SMTP_PASS: Your SendGrid API key

## Testing Without SMTP
If you don't want to configure SMTP yet, password reset emails will print to your terminal console when running `manage.py runserver`. This is perfect for development and testing.
