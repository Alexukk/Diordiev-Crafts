from flask import Flask, redirect, render_template, request, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta
from dotenv import load_dotenv
import os
from datetime import datetime, timezone

from unicodedata import category
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.permanent_session_lifetime = timedelta(hours=1)
app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///DiordievCrafts.db'
db = SQLAlchemy(app)

UPLOAD_FOLDER = 'static/uploads/posts'
PRODUCTS_FOLDER = 'static/uploads/products'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PRODUCTS_FILES'] = PRODUCTS_FOLDER

# Проверяем, существует ли папка, и создаем ее, если нет
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# -------------------------DB MODELS logic started--------------------------------#

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    photo1 = db.Column(db.String, nullable=False)
    photo2 = db.Column(db.String, nullable=False)
    photo3 = db.Column(db.String, nullable=False)
    category = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<Product {self.id}>'


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)
    photo = db.Column(db.String)
    date = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Post {self.id}>'


# -------------------------DB MODELS logic ended--------------------------------#


def IsAdmin(username, password):
    if username == os.getenv('ADMIN') and password == os.getenv('PASSWORD'):
        return True
    return False


# -------------------------Default routes logic started--------------------------------#
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def aboutUs():
    return render_template('about.html')


@app.route('/shop', methods=['GET'])
def shop():
    sort_by = request.args.get('sort_by')
    category = request.args.get('type')

    query = Product.query

    if category:
        print(f"Filtering by category: {category}")  # Use f-string for better debugging
        query = query.filter_by(category=category.capitalize())
    else:
        print("No category filter applied.")

    if sort_by == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.price.desc())


    products = query.all()

    return render_template('shop.html', products=products)


@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/posts')
def posts():
    all_posts = Post.query.order_by(Post.date.desc()).all()
    return render_template('posts.html', posts=all_posts)

# -------------------------Default routes logic ended--------------------------------#

# -------------------------ADMIN logic started--------------------------------#

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

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
    if not session.get("logged_in"):
        flash('You need to be logged in to access the admin panel.', 'warning')
        return redirect(url_for('login'))
    return render_template('panel.html')

# -------------------------Adding product logic --------------------------------------#

@app.route('/create-product', methods=['GET', 'POST'])
def create_product():
    if not session.get("logged_in"):
        flash('You need to be logged in to create a product.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            title = request.form.get('title')
            price = request.form.get('price')
            text = request.form.get('text')
            category = request.form.get('category')

            # Вспомогательная функция для сохранения файла
            def save_and_get_path(file):
                if file and file.filename:
                    # Создаём уникальное имя файла
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                    filename_with_ts = f"{timestamp}_{filename}"

                    # Сохраняем файл в правильную папку
                    file.save(os.path.join(app.config['PRODUCTS_FILES'], filename_with_ts))

                    # Возвращаем относительный путь для БД
                    return os.path.join('uploads', 'products', filename_with_ts)
                return None

            photo_path1 = save_and_get_path(request.files.get('photo1'))
            photo_path2 = save_and_get_path(request.files.get('photo2'))
            photo_path3 = save_and_get_path(request.files.get('photo3'))

            new_product = Product(
                title=title,
                price=price,
                text=text,
                photo1=photo_path1,
                photo2=photo_path2,
                photo3=photo_path3,
                category=category
            )
            db.session.add(new_product)
            db.session.commit()

            flash('Product created successfully!', 'success')
            return redirect(url_for('shop'))
        except Exception as e:
            db.session.rollback()
            print(e)
            flash(f'Error occurred while creating the product: {e}', 'error')
            return redirect(url_for('create_product'))

    return render_template('create_product.html')


@app.route('/delete-product', methods=['GET'])
def delete_product_page():
    if not session.get("logged_in"):
        flash('You need to be logged in to delete a product.', 'warning')
        return redirect(url_for('login'))

    all_products = Product.query.all()
    return render_template('delete_product.html', products=all_products)


@app.route('/delete-product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if not session.get("logged_in"):
        flash('You need to be logged in to delete a product.', 'warning')
        return redirect(url_for('login'))

    product_to_delete = Product.query.get_or_404(product_id)

    photo_filenames = [
        product_to_delete.photo1,
        product_to_delete.photo2,
        product_to_delete.photo3
    ]

    try:
        # Сначала удаляем из БД
        db.session.delete(product_to_delete)
        db.session.commit()

        # Затем удаляем файлы
        for filename in photo_filenames:
            if filename:
                # Используем правильную переменную для пути к папке продуктов
                file_path = os.path.join('./static/', filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                else:
                    print(f"File not found: {file_path}")

        flash('Product deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error during post or file deletion: {e}")
        flash(f'Error occurred while deleting the product: {e}', 'error')

    return redirect(url_for('delete_product_page'))


# -------------------------Create post logic --------------------------------------#
@app.route('/create-post', methods=['GET', 'POST'])
def create_post():
    if not session.get("logged_in"):
        flash('You need to be logged in to create a post.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            title = request.form.get('title')
            text = request.form.get('text')


            uploaded_file = request.files.get('photo')
            photo_path = None
            if uploaded_file and uploaded_file.filename:
                # Делаем имя файла безопасным
                filename = secure_filename(uploaded_file.filename)
                # Сохраняем файл в папку загрузок
                uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

                photo_path = filename

            new_post = Post(title=title, photo=photo_path, text=text)
            db.session.add(new_post)
            db.session.commit()

            flash('Post created successfully!', 'success')
            return redirect(url_for('posts'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error occurred while creating the post: {e}', 'error')
            return redirect(url_for('create_post'))
    else:
        return render_template('create_post.html')

# -------------------------Delete post logic --------------------------------------#

@app.route('/delete-post', methods=['GET'])
def delete_post_page():
    if not session.get("logged_in"):
        flash('You need to be logged in to delete a post.', 'warning')
        return redirect(url_for('login'))
    all_posts = Post.query.order_by(Post.date.desc()).all()
    return render_template('delete_post.html', posts=all_posts)



@app.route('/delete-post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    if not session.get("logged_in"):
        flash('You need to be logged in to delete a post.', 'warning')
        return redirect(url_for('login'))

    post_to_delete = Post.query.get_or_404(post_id)


    photo_filename = post_to_delete.photo

    try:
        db.session.delete(post_to_delete)
        db.session.commit()
        if photo_filename:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            else:
                print(f"File not found: {file_path}")

        flash('Post deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error during post or file deletion: {e}")
        flash(f'Error occurred while deleting the post: {e}', 'error')

    return redirect(url_for('posts'))


# -------------------------ADMIN logic ended--------------------------------#
# Убедись, что твоя база данных создается при запуске приложения
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)