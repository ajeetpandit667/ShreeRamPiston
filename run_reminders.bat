@echo off
cd %~dp0
python manage.py shell -c "from repairs.cron import send_reminders; send_reminders()"