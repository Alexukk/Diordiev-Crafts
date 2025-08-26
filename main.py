from flask import Flask, redirect, render_template, request
import telebot
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///DiordievCrafts.db'
db = SQLAlchemy(app)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def aboutUs():
    return render_template('about.html')




if __name__ == '__main__':
    app.run(debug=True)