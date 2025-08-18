from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, logout_user, login_required, current_user, LoginManager
from flask_cors import CORS

application = Flask(__name__)
application.config['SECRET_KEY'] = 'minha_chave_1234'  # Chave secreta para sessões
application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'

loginmanager = LoginManager()
db = SQLAlchemy(application)
loginmanager.init_app(application)
loginmanager.login_view = 'login'  # Redireciona para a rota de login
CORS(application)  # Permite requisições de outros domínios
# Modelagem dos dados
#User (id, username, password)
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    cart = db.relationship('CartItem', backref='user', lazy=True)  # Relacionamento com o carrinho de compras

# Produto (id, name, price, description)
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True) #primary_key=True significa que é a chave primária, ou seja, um identificador único para cada produto
    name = db.Column(db.String(120), nullable=False) #nullable=False significa que o campo é obrigatório
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True) #nullable=True significa que o campo é opcional

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)

# === Autenticação do usuário ===
@loginmanager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ======== Routes ========
# == LOGIN e LOGOUT ==
@application.route('/login', methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    user = User.query.filter_by(username=username).first()
    if user and data.get("password") == user.password:
        login_user(user)
        return jsonify({"message": "Login bem-sucedido!"}), 201

    return jsonify({"message": "Credenciais inválidas"}), 401

@application.route('/logout', methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout bem-sucedido!"}), 201

# == Rotas de Produtos ==
@application.route('/api/products/add', methods=["POST"])
@login_required  # Protege a rota para que apenas usuários autenticados possam acessar
def add_product():
    data = request.json
    if 'name' in data and 'price' in data:
        product = Product(
            name=data.get("name"),
            price=data.get("price"),
            description=data.get("description", "")
        )
        db.session.add(product)
        db.session.commit()
        return {"message": "Produto adicionado com sucesso!"}, 201
    else:
        return jsonify({"message": "Dados inválidos do produto"}), 400
    
@application.route('/api/products/delete/<int:product_id>', methods=["DELETE"])
@login_required 
def delete_product(product_id):
    product = Product.query.get(product_id)
    if product:
        db.session.delete(product)
        db.session.commit()
        return {"message": "Produto deletado com sucesso!"}, 201
    else:
        return jsonify({"message": "Produto não encontrado"}), 404

@application.route('/api/products/<int:product_id>', methods=["GET"])
def get_product_details(product_id):
    product = Product.query.get(product_id)
    if product:
        return jsonify({
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "description": product.description
        }), 201
    else:
        return jsonify({"message": "Produto não encontrado"}), 404

@application.route('/api/products/update/<int:product_id>', methods=["PUT"])
@login_required 
def update_product(product_id):
    data = request.json
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"message": "Produto não encontrado"}), 404
    if 'name' in data:
        product.name = data['name']
    if 'price' in data:
        product.price = data['price']
    if 'description' in data:
        product.description = data['description']
    db.session.commit()
    
    return jsonify({"message": "Produto atualizado com sucesso!"}), 201

@application.route('/api/products', methods=["GET"])
def get_products():
    products = Product.query.all()
    product_list = []
    for product in products:
        product_data = ({
            "id": product.id,
            "name": product.name,
            "price": product.price,
        })
        product_list.append(product_data)

    return jsonify(product_list), 201

# == Rotas do Checkout ==
@application.route('/api/cart/add/<int:product_id>', methods=["POST"])
@login_required
def add_to_cart(product_id):
    user = User.query.get(int(current_user.id))
    product = Product.query.get(product_id)

    if user and product:
        cart_item = CartItem(user_id=user.id, product_id=product.id)
        db.session.add(cart_item)
        db.session.commit()
        return jsonify({"message": f"Produto {product.name} adicionado ao carrinho"}), 201
    #     return jsonify({"message": f"Produto {product.name} adicionado ao carrinho do usuário {user.username}"}), 201
    return jsonify({"message": "Falha ao adicionar o item no carrinho"}), 400

@application.route('/api/cart/remove/<int:product_id>', methods=["DELETE"])
@login_required
def remove_from_cart(product_id):
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({"message": "Item removido do carrinho"}), 201
    else:
        return jsonify({"message": "Falha ao remover o item no carrinho"}), 404

@application.route('/api/cart', methods=["GET"])
@login_required
def view_cart():
    user = User.query.get(int(current_user.id))
    cart_items = user.cart
    cart_content = []
    for item in cart_items:
        product = Product.query.get(item.product_id)
        cart_content.append({
            "id": item.id,
            "user_id": item.user_id,
            "product_id": item.product_id,
            "product_name": product.name,
            "product_price": product.price
        })
    return jsonify(cart_content), 201

@application.route('/api/cart/checkout', methods=["POST"])
@login_required
def checkout():
    user = User.query.get(int(current_user.id))
    cart_items = user.cart
    if not cart_items:
        return jsonify({"message": "Seu carrinho está vazio"}), 400

    # Aqui você pode implementar a lógica de checkout, como processar o pagamento
    # Por enquanto, vamos apenas limpar o carrinho
    for item in cart_items:
        db.session.delete(item)
    db.session.commit()
    
    return jsonify({"message": "Checkout realizado com sucesso!"}), 201

# === Home Route ===
@application.route('/')
def home():
    return "Minha primeira aplicação Flask!"

# === Configuração do para o Flask-Shell-Context ===
# Isso permite que você acesse o banco de dados e modelos diretamente no shell do Flask
@application.shell_context_processor
def make_shell_context():
    return {'db': db, 'Product': Product}

# === Executando a aplicação ===
if __name__ == "__main__":
    # db.create_all()  # Cria as tabelas no banco de dados
    application.run(debug=True)
    # print(db.engine.table_names())  # Verifica as tabelas criadas no banco de dados