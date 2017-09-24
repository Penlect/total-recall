
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

app = Flask(__name__)
# Todo: hide secrets from git
app.secret_key = 'Melodies of Life 34fj34ofi34jfl3'

localhost = bool(os.environ.get('FLASK_DEBUG'))

if not localhost:
    SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
        username="penlect",
        password="melodiesoflife",
        hostname="penlect.mysql.pythonanywhere-services.com",
        databasename="penlect$recall",
    )
else:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 280
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

import recall.views  # Has to be here
import recall.models

restart = True
if localhost and restart:
    db.metadata.drop_all(db.engine, tables=[
        #models.MemoData.__table__,
        #models.RecallData.__table__,
        #models.Correction.__table__,
        #models.User.__table__,
        #models.AlmostCorrectWord.__table__,
    ])
db.create_all()

if False:
    u1 = models.User('sm2017', 'secret', 'hej@email.se', 'Daniel Andersson', 'Sweden')
    u2 = models.User('penlect', '123abc', 'email@email.com', 'Kalle Anka', 'Sweden')
    db.session.add(u1)
    db.session.add(u2)
    db.session.commit()
