from flask import Flask, redirect, render_template, request, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.permanent_session_lifetime = timedelta(days=2)
app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///DiordievCrafts.db'
db = SQLAlchemy(app)


def IsAdmin(username, password):
    if username == os.getenv('ADMIN') and password == os.getenv('PASSWORD'):
        return True
    else:
        return False


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def aboutUs():
    return render_template('about.html')


@app.route('/shop', methods=['GET'])
def shop():
    # request to db
    return render_template('shop.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # 1. Проверяем логин и пароль до сохранения в сессию
        if IsAdmin(username, password):
            session['logged_in'] = True
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('admin_panel'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/admin-panel')
def admin_panel():
    if "logged_in" not in session or not session["logged_in"]:
        flash('You need to be logged in to create a post.', 'warning')
        return redirect(url_for('login'))
    return render_template('panel.html')


@app.route('/create-post', methods=['GET', 'POST'])
def create_post():

    if "logged_in" not in session or not session["logged_in"]:
        flash('You need to be logged in to create a post.', 'warning')
        return redirect(url_for('login'))

    # Теперь ты можешь быть уверен, что сюда попадет только админ
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        text = request.form.get('text')
        photo1 = request.form.get('photo1')
        photo2 = request.form.get('photo2')
        photo3 = request.form.get('photo3')

        # writing to db
        flash('Post created successfully!', 'success')
        return redirect(url_for('create_post'))

    return render_template('create_post.html')


if __name__ == '__main__':
    app.run(debug=True)