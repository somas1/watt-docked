DEBUG = True

SERVER_NAME = '10.0.1.33:8989'
# SERVER_NAME = 'mini.local:8000'
SECRET_KEY = 'insecurekeyfordev'

# SQLAlchemy.
db_uri = 'sqlite:///' + '../watt_app/database/watts.sqlite'
SQLALCHEMY_DATABASE_URI = db_uri
SQLALCHEMY_TRACK_MODIFICATIONS = False
