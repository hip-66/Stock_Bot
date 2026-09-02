@echo off
cd /d "C:\Users\Uriya.DESKTOP-AEQOV71\Desktop\Projects\Stock Bot"

:loop
echo Starting the Financial Telegram Bot...
"C:\Users\Uriya.DESKTOP-AEQOV71\AppData\Local\Python\bin\python.exe" bot.py
echo Bot crashed or stopped. Restarting in 5 seconds...
timeout /t 5
goto loop