
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/numbers')
def numbers():
    return render_template('numbers.html')