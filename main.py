from flask import Flask, redirect, render_template, request, session, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta
from dotenv import load_dotenv
import os
from datetime import datetime, timezone

from bot import notifier
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.permanent_session_lifetime = timedelta(hours=1)
app.secret_key = os.getenv('SECRET_KEY')

# --- ПІДКЛЮЧЕННЯ ДО SQLITE ЗБЕРЕЖЕНО ---
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
    category = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(30), nullable=False)

    # ВИПРАВЛЕНО: Додано cascade для коректного видалення продуктів.
    order_items = db.relationship('Order_item', backref='product', lazy='dynamic',
                                  cascade="all, delete-orphan")

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


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    contact_way = db.Column(db.String(30), nullable=False)
    date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    status = db.Column(db.String(30), default='New')
    items = db.relationship('Order_item', backref='order', lazy='dynamic', cascade="all, delete-orphan")
    total_price = db.Column(db.Float, nullable=False, default=0.0)
    source = db.Column(db.String(50), default='Not given')

class Order_item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=True)  # Текст оголошення
    is_active = db.Column(db.Boolean, default=False)  # Прапорець: показувати чи ні
    color = db.Column(db.String(30), default='danger')  # <-- ДОДАНО: Колір плашки (danger, success, info, warning)

    def __repr__(self):
        return f'<Announcement {self.id}>'

    # Зв'язок 'product' видалено, оскільки він визначений у класі Product з backref='product'.

# -------------------------DB MODELS logic ended--------------------------------#


def IsAdmin(username, password):
    if username == os.getenv('ADMIN') and password == os.getenv('PASSWORD'):
        return True
    return False


# -------------------------Default routes logic started--------------------------------#
@app.route('/')
def index():

    announcement = Announcement.query.first()

    # ------------------ DEBUG ------------------
    if announcement:
        print(f"Announcement found! Active: {announcement.is_active}, Text: {announcement.text[:10]}...")
    else:
        print("Announcement NOT found in DB.")
    # -------------------------------------------
    return render_template('index.html')

@app.route('/api/get-announcement', methods=['GET'])
def api_get_announcement():
    try:
        announcement = Announcement.query.first()
        if announcement.is_active:
            data = {
                "text": announcement.text,
                "color": announcement.color
            }
            return jsonify(data)
        else:
            return jsonify({})

    except Exception as e:
        print(e)
        return {}



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


@app.route('/api/product/<int:product_id>', methods=['GET'])
def get_product_details(product_id):
    """
    Повертає повні деталі продукту для відображення у модальному вікні.
    """
    # 1. Знаходимо продукт, або повертаємо 404
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    # 2. Формуємо JSON-відповідь
    # ВАЖЛИВО: Використовуємо .text як повний опис, оскільки у моделі немає full_text
    # Ціна повинна бути перетворена на str для безпечної передачі
    try:
        price_str = f"{product.price:.2f}"
    except:
        price_str = str(product.price)  # Запасний варіант, якщо price не float/int

    return jsonify({
        'id': product.id,
        'title': product.title,
        'category': product.category,
        'price': price_str,
        'full_text': product.text,  # Використовуємо поле 'text' як повний опис
        'status': product.status,
        # Повертаємо відносні шляхи до фото
        'photo1': product.photo1,
        'photo2': product.photo2,
        'photo3': product.photo3
    })


@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/posts')
def posts():
    all_posts = Post.query.order_by(Post.date.desc()).all()
    return render_template('posts.html', posts=all_posts)


@app.route('/api/post/<int:post_id>', methods=['GET'])
def get_post_details(post_id):
    post = Post.query.get(post_id)

    if post is None:
        return jsonify({'error': 'Post not found'}), 404

    return jsonify({
        'id': post.id,
        'title': post.title,
        'date': post.date.strftime('%Y-%m-%d'),  # Форматируем дату для JS
        'photo': post.photo,  # Основное фото (для карусели)
        # Предполагаем, что полное содержание находится в поле 'full_text' или 'text'
        'full_text': post.full_text if hasattr(post, 'full_text') else post.text,
        # Если есть дополнительные фото (опционально)
        'photo2': post.photo2 if hasattr(post, 'photo2') else None,
        'photo3': post.photo3 if hasattr(post, 'photo3') else None,
    }), 200


@app.route('/checkout')
def checkout():
    return render_template("checkout.html")


@app.route('/submit_order', methods=['POST'])
def submit_order():
    # 1. Отримання даних JSON з фронтенду
    try:
        data = request.get_json()
    except:
        return jsonify({'error': 'Invalid JSON format'}), 400

    # Оновлено: 'source' не є обов'язковим, тому перевіряємо лише ключові поля
    if not all(k in data for k in ['full_name', 'phone', 'email', 'contact_way', 'cart_items']):
        return jsonify({'error': 'Missing required fields (Name, Phone, Email, Contact Way or Cart Items)'}), 400

    # Дані клієнта
    full_name = data['full_name']
    phone = data['phone']
    email = data['email']
    contact_way = data['contact_way']
    cart_items = data['cart_items']

    # НОВЕ ПОЛЕ: Отримуємо джерело. Якщо не надано, використовуємо значення за замовчуванням 'Not given'.
    source = data.get('source', 'Not given')

    if not cart_items:
        return jsonify({'error': 'Cart is empty.'}), 400

    product_ids = [int(id) for id in cart_items.keys()]

    # ПРИПУЩЕННЯ: Product.query коректно визначено
    products_map = {p.id: p for p in Product.query.filter(Product.id.in_(product_ids)).all()}

    order_item_list = []
    total_price = 0.0

    for product_id_str, item_data in cart_items.items():
        product_id = int(product_id_str)
        amount = item_data.get('qty', 0)

        if product_id not in products_map or amount <= 0:
            continue

        product = products_map[product_id]

        item_subtotal = product.price * amount
        total_price += item_subtotal

        # ПРИПУЩЕННЯ: Order_item коректно визначено
        order_item = Order_item(
            item_id=product.id,
            amount=amount,
        )
        order_item_list.append(order_item)

    if total_price == 0.0:
        return jsonify({'error': 'Failed to calculate total price or cart contains invalid items.'}), 400

    # Створення об'єкта замовлення, включаючи нове поле 'source'
    new_order = Order(
        full_name=full_name,
        email=email,
        phone=phone,
        contact_way=contact_way,
        source=source,  # <--- ЗБЕРІГАЄМО НОВЕ ПОЛЕ
        total_price=total_price,
    )

    try:
        # ПРИПУЩЕННЯ: db.session коректно визначено
        db.session.add(new_order)
        db.session.flush()

        for item in order_item_list:
            item.order_id = new_order.id

        db.session.add_all(order_item_list)

        db.session.commit()

        try:
            # ПРИПУЩЕННЯ: notifier коректно визначено
            notifier(new_order)
        except Exception as telegram_error:

            print(f"ATTENTION: Failed to send Telegram notification! Error: {telegram_error}")

        return jsonify({
            'success': True,
            'message': 'Order successfully placed.',
            'order_id': new_order.id
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error placing order: {e}")
        return jsonify({'error': 'Server error: Failed to save the order to the database.'}), 500

@app.route('/thank_you')
def thank_you():
    order_id = request.args.get('order_id', 'N/A')
    return render_template('thankyou.html', order_id=order_id)
# -------------------------Default routes logic ended--------------------------------#


@app.route('/admin/orders')
def admin_orders():
    if not session.get("logged_in"):
        flash('You need to be logged in to access the admin panel.', 'warning')
        return redirect(url_for('login'))

    orders = Order.query.order_by(Order.date.desc()).all()

    return render_template('admin_orders.html', orders=orders)



@app.route('/admin/update_status', methods=['POST'])
def admin_update_status():
    if not session.get("logged_in"):
        flash('You need to be logged in to access the admin panel.', 'warning')
        return redirect(url_for('login'))

    data = request.get_json()
    order_id = data.get('order_id')
    new_status = data.get('status')

    order = Order.query.get(order_id)

    if not order:
        return jsonify({'error': f'Заказ с ID {order_id} не найден'}), 404

    valid_statuses = ['New', 'Contacted', 'Completed', 'Cancelled']
    if new_status not in valid_statuses:
        return jsonify({'error': 'Недопустимое значение статуса.'}), 400

    old_status = order.status

    try:

        order.status = new_status
        db.session.commit()


        return jsonify({'success': True, 'status': new_status}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error updating order status: {e}")
        return jsonify({'error': 'Ошибка сервера при обновлении статуса.'}), 500


@app.route('/admin/delete_order/<int:order_id>', methods=['POST'])

def admin_delete_order(order_id):
    if not session.get("logged_in"):
        flash('You need to be logged in to access the admin panel.', 'warning')
        return redirect(url_for('login'))

    order_to_delete = Order.query.get(order_id)

    if not order_to_delete:
        return jsonify({'error': f'Замовлення з ID {order_id} не знайдено'}), 404

    try:
        db.session.delete(order_to_delete)
        db.session.commit()

        return jsonify({'success': True, 'message': f'Замовлення #{order_id} успішно видалено.'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Помилка видалення замовлення: {e}")
        return jsonify({'error': f'Помилка сервера при видаленні замовлення: {e}'}), 500



@app.route('/admin/announcement', methods=['GET', 'POST'])
def admin_announcement():
    if not session.get("logged_in"):
        flash('You need to be logged in to access the admin panel.', 'warning')
        return redirect(url_for('login'))

    announcement = Announcement.query.first()
    if not announcement:
        # Встановлюємо default 'danger' при першому створенні
        announcement = Announcement(text='', is_active=False, color='danger')
        db.session.add(announcement)
        db.session.commit()

    if request.method == 'POST':
        announcement.text = request.form.get('text', '').strip()
        announcement.color = request.form.get('color', 'danger')  # <-- ЗМІНА ТУТ: Отримуємо колір

        if not announcement.text:
            announcement.is_active = False
        else:
            is_active_str = request.form.get('is_active')
            announcement.is_active = (is_active_str == 'on')

        try:
            db.session.commit()
            flash('Announcement settings updated successfully!', 'success')
            return redirect(url_for('admin_announcement'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating announcement: {e}', 'error')

    return render_template('announce_admin.html', announcement=announcement)
# -------------------------Сart routes logic Started--------------------------------#

@app.route('/cart')
def Cart():
    return render_template('cart.html')


@app.route('/api/get-cart-details', methods=['POST'])
def get_cart_details():

    try:

        data = request.get_json()

        product_ids = data.get('product_ids', [])

        if not product_ids:
            return jsonify({'products': []}), 200

        products_from_db = Product.query.filter(Product.id.in_(product_ids)).all()

        serialized_products = []
        for product in products_from_db:
            serialized_products.append({
                'id': product.id,
                'title': product.title,
                'price': product.price,  # Актуальна ціна!
                'category': product.category,
                'status' : product.status,
                'photo_url': product.photo1  # Назву файлу для подальшого використання у JS
            })

        return jsonify({'products': serialized_products}), 200

    except Exception as e:
        print(f"Помилка API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# -------------------------Cart routes logic ended--------------------------------#



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
            status = request.form.get('status')

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
                category=category,
                status=status
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

@app.route('/change_status/<int:product_id>', methods=['POST'])
def change_status(product_id):
    new_status = request.form.get('status')
    product = Product.query.get_or_404(product_id)
    product.status = new_status
    db.session.commit()
    return redirect(url_for('delete_product_page'))


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
        # Сначала удаляем из БД (CASCADE позаботится о Order_item)
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


@app.route('/admin/edit-product-details-<int:product_id>', methods=['POST', 'GET'])
def editProductDetails(product_id):
    if not session.get("logged_in"):
        flash('You need to be logged in to access the admin panel.', 'warning')
        return redirect(url_for('login'))

    product = Product.query.get_or_404(product_id)

    if request.method == 'GET':
        return render_template('update_product.html', product=product)

    try:
        product.title = request.form.get('title')
        product.text = request.form.get('text')
        product.price = request.form.get('price')
        product.category = request.form.get('category')
        db.session.commit()

        flash("Product updated successfully!", 'success')

        return redirect(url_for('delete_product_page'))
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred {e}")
        print(e)
        return render_template('update_product.html', product=product)


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


@app.route('/admin/edit-post-details-<int:post_id>', methods=['POST', 'GET'])
def editPostDetails(post_id):
    if not session.get("logged_in"):
        flash('You need to be logged in to access the admin panel.', 'warning')
        return redirect(url_for('login'))

    post = Post.query.get_or_404(post_id)

    if request.method == 'GET':
        return render_template('update_post.html', post=post)

    try:
        post.title = request.form.get('title')
        post.text = request.form.get('text')

        db.session.commit()

        flash("Post updated successfully!", 'success')

        return redirect(url_for('delete_post_page'))
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred {e}")
        return render_template('update_post.html', post=post)


@app.route('/follow-us')
def follow_us():
    return render_template('follow_us.html')

# -------------------------ADMIN logic ended--------------------------------#
# Убедись, что твоя база данных создается при запуске приложения
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)