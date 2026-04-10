from flask import Flask, jsonify, request

from flask_sqlalchemy import SQLAlchemy

from flask_marshmallow import Marshmallow
from marshmallow import fields, validate, ValidationError

from datetime import datetime

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lib.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db = SQLAlchemy(app) # database connection
seriliazer = Marshmallow(app)

########################################################################
# MODELS

class Author(db.Model):
    __tablename__ = "authors"
    
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100), nullable=False)
    nationality  = db.Column(db.String(80))
    bio          = db.Column(db.Text)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    books = db.relationship("Book", 
                            back_populates="author",
                            cascade="all, delete-orphan")


class Book(db.Model):
    __tablename__ = "books"
    
    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(100), nullable=False)
    year_pub      = db.Column(db.String(80))
    genre         = db.Column(db.Text)
    price         = db.Column(db.Float, nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    #a book belongs to an author"
    author_id = db.Column(db.Integer, db.ForeignKey("authors.id"), nullable=False)
    author    = db.relationship("Author", back_populates="books")


########################################################################
# SCHEMA

class AuthorSchema(seriliazer.SQLAlchemyAutoSchema):
    class Meta:
        model = Author
        load_instance = True
        include_fk = True

    name = fields.Str(
        required = True,
        validate=validate.Length(min=1, max=100)
    )

    bio = fields.Str(
        required = True,
        validate=validate.Length(min=1, max=100)
    )

    books = fields.List(
        fields.Nested(lambda: BookSchema(exclude=("author",))),
        dump_only = True # read_only(you cannot set the books)
    )


class BookSchema(seriliazer.SQLAlchemyAutoSchema):
    class Meta:
        model = Book
        load_instance = True
        include_fk = True

    title = fields.Str(
        required=True, 
        validate=validate.Length(min=1, max=200)
    )
    price = fields.Float(
        required=True, 
        validate=validate.Range(min=0.0)
    )
    genre = fields.Str(
        validate=validate.OneOf([
        "Literary Fiction", "Science Fiction",
        "Mystery", "Non-fiction", "Poetry"
        ])
    )
    id        = fields.Int(dump_only=True)     # client cannot set their own id
    author    = fields.Nested(
        AuthorSchema(only=("id","name", "nationality")), 
        dump_only=True
    )

# intatnsiate the schemas
author_schema = AuthorSchema()
list_of_authors = AuthorSchema(many=True)

########################################################################
# Endpoints

@app.route("/api/authors", methods=["GET"])
def get_all_authors():
    return jsonify(list_of_authors.dump(Author.query.all())), 200


@app.route("/api/authors/<int:author_id>", methods=["GET"])
def get_one_author(author_id):
    return jsonify(author_schema.dump(db.get_or_404(Author, author_id))), 200

@app.route("/api/authors", methods=["POST"])
def create_an_author():
    try:
        new_data = author_schema.load(
            request.json
        )
    except ValidationError as err:
        return jsonify({
            "error": err.messages
        }), 422
    
    db.session.add(new_data)
    db.session.commit()

    return jsonify(author_schema.dump(new_data)), 201

@app.route("/api/authors/<int:author_id>", methods=["PATCH"])
def update_author(author_id):
    author = db.get_or_404(author_id)
    try:
        update_record = author_schema.load(
        request.json,
        instance=author,
        partial=True
    )
    except ValidationError as err:
        return jsonify({
            "error": err
        }), 422
    
    db.session.commit()

    return jsonify(author_schema.dump(update_author)), 200

@app.route("/api/authors/<int:author_id>", methods=["DELETE"])
def delete_author(author_id):
    author = db.get_or_404(Author, author_id)
    db.session.delete(author)
    db.session.commit()
    return "", 204

# RUN

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run()
