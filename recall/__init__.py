
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

app = Flask(__name__)
app.secret_key = 'some_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

import recall.views  # Has to be here
import recall.models

db.metadata.drop_all(db.engine, tables=[
    models.MemoData.__table__,
    models.RecallData.__table__,
    models.Correction.__table__,
    models.User.__table__,
    models.XlsDoc.__table__,
    models.AlmostCorrectWord.__table__,
])
db.create_all()
u1 = models.User('sm2017', 'secret', 'hej@email.se', 'Daniel Andersson', 'Sweden')
u2 = models.User('penlect', '123abc', 'email@email.com', 'Kalle Anka', 'Sweden')
db.session.add(u1)
db.session.add(u2)
db.session.commit()
