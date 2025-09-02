
from main import db
from datetime import datetime, timezone

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    photo1 = db.Column(db.String, nullable=False)
    photo2 = db.Column(db.String, nullable=False)
    photo3 = db.Column(db.String, nullable=False)


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