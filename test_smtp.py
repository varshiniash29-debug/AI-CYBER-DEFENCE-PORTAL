import smtplib
import sys
try:
    server = smtplib.SMTP('smtp.gmail.com', 587, timeout=15)
    server.starttls()
    server.login('varshiniash29@gmail.com', 'tndjqpuljpnfnqiv')
    print('LOGIN_OK')
    server.quit()
except Exception as e:
    print('LOGIN_ERROR', repr(e))
    sys.exit(1)
