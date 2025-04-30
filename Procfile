web: gunicorn --config gunicorn.conf.py supplysite.wsgi
release: python manage.py migrate
# gettingstarted.wsgi

# Use Heroku's release phase feature
# release: ./manage.py migrate --no-input