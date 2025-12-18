
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth
import os
from werkzeug.utils import secure_filename
import shutil
import uuid # Importación de módulos necesarios para la aplicación Flask
from functools import wraps
from datetime import datetime
from dotenv import load_dotenv

# Creación de la instancia de la aplicación Flask
app = Flask(__name__)
# Configuración de la clave secreta para sesiones, generada aleatoriamente
app.secret_key = os.urandom(24)


# Clave secreta para acceso a finanzas (cámbiala por una segura)
FINANZAS_KEY = "root10"  # Cambia esto en producción



load_dotenv()

database_url = os.environ.get('DATABASE_URL')
if not database_url:
    raise ValueError("No se encontró la variable DATABASE_URL. Verifica las variables de entorno en Railway.")

# Railway ya te da la URL con postgresql://, pero por si acaso
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False



# === FUNCIÓN PARA CALCULAR TOTAL AGRÍCOLA ===
def calc_total_agricola(carrito_agricola):
    """Calcula el total del carrito agrícola"""
    return sum(item['subtotal'] for item in carrito_agricola)

# ==================== DECORADOR: PERMITE USUARIOS O INVITADOS ====================
def login_required_or_guest(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session or 'guest' in session:
            return f(*args, **kwargs)
        return redirect(url_for('login'))
    return decorated_function




# Configuración de la carpeta para subir imágenes
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Extensiones de archivo permitidas para las imágenes
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Creación de la carpeta de subidas si no existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Inicialización de SQLAlchemy para la gestión de la base de datos
db = SQLAlchemy(app)
# Inicialización de Flask-Migrate para manejar migraciones de la base de datos
migrate = Migrate(app, db)

# Configuración de OAuth para autenticación con Google
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id='TU_CLIENT_ID',  # ID del cliente de Google OAuth
    client_secret='TU_CLIENT_SECRET',  # Secreto del cliente de Google OAuth
    access_token_url='https://oauth2.googleapis.com/token',  # URL para obtener el token de acceso
    authorize_url='https://accounts.google.com/o/oauth2/auth',  # URL para autorización
    api_base_url='https://www.googleapis.com/oauth2/v1/',  # URL base para la API de Google
    client_kwargs={'scope': 'openid profile email'},  # Ámbitos de la autenticación
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs'  # URI para las claves públicas de Google
)

# Definición del modelo Usuario para la base de datos
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)  # ID único del usuario
    nombre = db.Column(db.String(100), nullable=False)  # Nombre del usuario
    email = db.Column(db.String(100), unique=True, nullable=False)  # Correo único del usuario
    password = db.Column(db.String(100))  # Contraseña del usuario (puede ser nula para usuarios de Google)

# Definición del modelo Restaurante para la base de datos
class Restaurante(db.Model):
    __tablename__ = 'restaurantes'
    id = db.Column(db.Integer, primary_key=True)  # ID único del restaurante
    nombre = db.Column(db.String(100), nullable=False)  # Nombre del restaurante
    descripcion = db.Column(db.Text)  # Descripción del restaurante
    categoria = db.Column(db.String(100), nullable=False)  # Categoría del restaurante
    imagen = db.Column(db.String(255), nullable=True)  # Ruta de la imagen del restaurante
    menus = db.relationship('Menu', backref='restaurante')  # Relación con los menús
    pedidos = db.relationship('Pedido', backref='restaurante')  # Relación con los pedidos

# Definición del modelo Menu para la base de datos
class Menu(db.Model):
    __tablename__ = 'menus'
    id = db.Column(db.Integer, primary_key=True)  # ID único del menú
    restaurante_id = db.Column(db.Integer, db.ForeignKey('restaurantes.id'))  # ID del restaurante asociado
    nombre = db.Column(db.String(100), nullable=False)  # Nombre del menú
    descripcion = db.Column(db.Text)  # Descripción del menú
    precio = db.Column(db.Float, nullable=False)  # Precio del menú
    categoria = db.Column(db.String(100), nullable=False)  # Categoría del menú
    imagen = db.Column(db.String(255), nullable=True)  # Ruta de la imagen del menú




class PedidoItem(db.Model):
    __tablename__ = 'pedidos_items'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    
    # Relación opcional con menú
    menu = db.relationship('Menu', backref='items_pedido')






# Definición del modelo Pedido para la base de datos
# En tu clase Pedido, agrega esta línea:
# EN models.py o en tu app.py → clase Pedido
class Pedido(db.Model):
    __tablename__ = 'pedidos'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    restaurante_id = db.Column(db.Integer, db.ForeignKey('restaurantes.id'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    metodo_pago = db.Column(db.String(50), nullable=False)
    metodo_pago_detalle = db.Column(db.String(200))
    direccion_entrega = db.Column(db.String(200))
    numero_celular = db.Column(db.String(20))
    nombre_cliente = db.Column(db.String(100))
    tipo_entrega = db.Column(db.String(20), nullable=False)
    hora_reserva = db.Column(db.Time)
    fecha_reserva = db.Column(db.Date)
    estado = db.Column(db.String(20), default='pendiente')
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    
    # NUEVA COLUMNA
    codigo_pedido = db.Column(db.String(20), unique=True, nullable=False)

    # RELACIONES
    usuario = db.relationship('Usuario', backref='pedidos')
    
    # ELIMINA ESTA LÍNEA:
    # restaurante = db.relationship('Restaurante', backref='pedidos')
    
    # MANTÉN SOLO LOS ITEMS
    items = db.relationship('PedidoItem', backref='pedido', lazy=True, cascade='all, delete-orphan')





# === MODELO PRODUCTO AGRÍCOLA ===
class ProductoAgricola(db.Model):
    __tablename__ = 'productos_agricolas'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio_compra = db.Column(db.Float, nullable=False)  # Precio al comprar
    precio_venta = db.Column(db.Float, nullable=False)   # Precio al vender
    stock = db.Column(db.Integer, default=0)
    imagen = db.Column(db.String(255))

# === MODELOS PARA PEDIDOS AGRÍCOLAS ===
class PedidoAgricola(db.Model):
    __tablename__ = 'pedidos_agricolas'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    total = db.Column(db.Float, nullable=False)
    tipo_entrega = db.Column(db.String(50), nullable=False)
    direccion = db.Column(db.Text)
    telefono = db.Column(db.String(20))
    hora_recogida = db.Column(db.String(10))
    fecha = db.Column(db.DateTime, server_default=db.func.now())
    estado = db.Column(db.String(50), default='pendiente')
    usuario = db.relationship('Usuario', backref='pedidos_agricolas')

class DetallePedidoAgricola(db.Model):
    __tablename__ = 'detalles_pedido_agricola'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos_agricolas.id'))
    producto_id = db.Column(db.Integer, db.ForeignKey('productos_agricolas.id'))
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    producto = db.relationship('ProductoAgricola', backref='detalles_pedido')






# Función para verificar si la extensión del archivo es permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Función para copiar una imagen desde una ruta local a la carpeta de subidas
def copy_image_from_path(source_path, destination_dir):
    if not os.path.exists(source_path):
        return None
    filename = secure_filename(os.path.basename(source_path))  # Obtener nombre seguro del archivo
    destination_path = os.path.join(destination_dir, filename)  # Ruta de destino
    shutil.copy2(source_path, destination_path)  # Copiar archivo
    return os.path.join('uploads', filename)  # Retornar ruta relativa



# === FUNCIÓN PARA CALCULAR TOTAL AGRÍCOLA ===
def calc_total_agricola(carrito_agricola):
    """Calcula el total del carrito agrícola"""
    return sum(item.get('subtotal', 0) for item in carrito_agricola)




# Ruta principal: redirige a restaurantes si hay sesión activa, o a login si no
@app.route('/')
def index():
    if 'user_id' in session or 'guest' in session:
        return redirect(url_for('restaurantes'))
    return redirect(url_for('login'))

# Ruta para el inicio de sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']  # Obtener correo del formulario
        password = request.form['password']  # Obtener contraseña del formulario
        is_admin = email.endswith('@admin.saboresexpress.com')  # Verificar si es administrador
        is_client = email.endswith('@gmail.com')  # Verificar si es cliente
        if not (is_admin or is_client):
            flash('Debes usar un correo @gmail.com para clientes o @admin.saboresexpress.com para administradores.')
            return redirect(url_for('login'))
        usuario = Usuario.query.filter_by(email=email, password=password).first()  # Buscar usuario
        if usuario:
            if is_admin:
                session['admin_id'] = usuario.id  # Guardar ID de administrador en la sesión
                flash('Inicio de sesión de administrador exitoso.')
                return redirect(url_for('admin'))
            else:
                session['user_id'] = usuario.id  # Guardar ID de usuario en la sesión
                session.pop('guest', None)  # Eliminar modo invitado
                flash('Inicio de sesión exitoso.')
                return redirect(url_for('restaurantes'))
        flash('Correo o contraseña incorrectos.')
    return render_template('login.html')

# Ruta para el registro de usuarios
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']  # Obtener nombre del formulario
        email = request.form['email']  # Obtener correo del formulario
        password = request.form['password']  # Obtener contraseña del formulario
        is_admin = email.endswith('@admin.saboresexpress.com')  # Verificar si es administrador
        is_client = email.endswith('@gmail.com')  # Verificar si es cliente
        if not (is_admin or is_client):
            flash('Debes usar un correo @gmail.com para clientes o @admin.saboresexpress.com para administradores.')
            return redirect(url_for('registro'))
        if Usuario.query.filter_by(email=email).first():
            flash('El correo ya está registrado.')
            return redirect(url_for('registro'))
        usuario = Usuario(nombre=nombre, email=email, password=password)  # Crear nuevo usuario
        db.session.add(usuario)
        db.session.commit()
        flash('Registro exitoso. Por favor, inicia sesión.')
        return redirect(url_for('login'))
    return render_template('registro.html')

# Ruta para iniciar sesión con Google
@app.route('/login/google')
def login_google():
    redirect_uri = url_for('authorize', _external=True)  # Obtener URI de redirección
    return google.authorize_redirect(redirect_uri)  # Redirigir a Google para autenticación

# Ruta para manejar la autorización de Google
@app.route('/authorize')
def authorize():
    try:
        token = google.authorize_access_token()  # Obtener token de acceso
        user_info = google.parse_id_token(token, nonce=None)  # Obtener información del usuario
        email = user_info['email']
        nombre = user_info['name']
        if email.endswith('@admin.saboresexpress.com'):
            flash('Los administradores deben usar la página de inicio de sesión.')
            return redirect(url_for('login'))
        if not email.endswith('@gmail.com'):
            flash('Los clientes deben usar un correo @gmail.com.')
            return redirect(url_for('login'))
        usuario = Usuario.query.filter_by(email=email).first()
        if not usuario:
            usuario = Usuario(nombre=nombre, email=email, password='')  # Crear usuario si no existe
            db.session.add(usuario)
            db.session.commit()
        session['user_id'] = usuario.id  # Guardar ID de usuario en la sesión
        session.pop('guest', None)  # Eliminar modo invitado
        flash('Inicio de sesión con Google exitoso.')
        return redirect(url_for('restaurantes'))
    except Exception as e:
        flash(f'Error al autenticar con Google: {str(e)}')
        return redirect(url_for('login'))

# Ruta para entrar como invitado
@app.route('/guest')
def guest():
    session['guest'] = True  # Establecer modo invitado
    flash('Has entrado como invitado.')
    return redirect(url_for('restaurantes'))

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Eliminar ID de usuario
    session.pop('admin_id', None)  # Eliminar ID de administrador
    session.pop('guest', None)  # Eliminar modo invitado
    session.pop('carrito', None)  # Eliminar carrito
    flash('Sesión cerrada.')
    return redirect(url_for('login'))

# Ruta para mostrar los restaurantes
@app.route('/restaurantes')
def restaurantes():
    if 'user_id' not in session and 'guest' not in session:
        return redirect(url_for('login'))

    # === BUSCAR RESTAURANTES ===
    busqueda = request.args.get('busqueda', '').strip()
    query = Restaurante.query
    if busqueda:
        query = query.filter(Restaurante.nombre.ilike(f'%{busqueda}%'))
    restaurantes = query.all()

    # === PRODUCTOS AGRÍCOLAS (solo con stock) ===
    # MOSTRAR TODOS (para probar)
    productos_agricolas = ProductoAgricola.query.all()

    # === RESTAURANTES POPULARES (basado en pedidos) ===
    restaurantes_populares = db.session.query(
        Restaurante, 
        db.func.count(Pedido.id).label('total_pedidos')
    ).join(Pedido, isouter=True)\
     .group_by(Restaurante.id)\
     .order_by(db.desc('total_pedidos'))\
     .limit(3)\
     .all()

    # Convertir a lista de tuplas: (restaurante, count)
    restaurantes_populares = [(r, count) for r, count in restaurantes_populares]

    return render_template(
        'restaurantes.html',
        restaurantes=restaurantes,
        productos_agricolas=productos_agricolas,
        restaurantes_populares=restaurantes_populares,
        busqueda=busqueda
    )

# Ruta para mostrar el menú de un restaurante
@app.route('/menu/<int:restaurante_id>')
def menu(restaurante_id):
    if 'user_id' not in session and 'guest' not in session:
        return redirect(url_for('login'))

    # Obtener restaurante
    restaurante = Restaurante.query.get_or_404(restaurante_id)

    # Búsqueda
    busqueda = request.args.get('busqueda', '')
    if busqueda:
        menus = Menu.query.filter_by(restaurante_id=restaurante_id)\
            .filter(Menu.nombre.ilike(f'%{busqueda}%'))\
            .all()
    else:
        menus = Menu.query.filter_by(restaurante_id=restaurante_id).all()

    # Menús populares (3 más pedidos)
    menus_populares = db.session.query(Menu, db.func.count(PedidoItem.id), Restaurante)\
        .join(PedidoItem, isouter=True)\
        .join(Restaurante, Menu.restaurante_id == Restaurante.id)\
        .group_by(Menu.id, Restaurante.id)\
        .order_by(db.func.count(PedidoItem.id).desc())\
        .limit(3)\
        .all()

    # === CARRITO: Asegurar formato de diccionario ===
    if 'carrito' not in session or not isinstance(session['carrito'], dict):
        session['carrito'] = {}

    restaurante_id_str = str(restaurante_id)
    carrito_items = session['carrito'].get(restaurante_id_str, [])

    # Calcular total
    total = sum(item['precio'] * item['cantidad'] for item in carrito_items)

    return render_template(
        'menu.html',
        restaurante=restaurante,
        menus=menus,
        busqueda=busqueda,
        menus_populares=menus_populares,
        carrito_items=carrito_items,
        total=total,
        current_date=datetime.now().strftime('%Y-%m-%d')  # Añadido si usas fecha mínima
    )


# Ruta para agregar ítems al carrito (botón normal)
@app.route('/agregar_carrito/<int:restaurante_id>/<int:menu_id>', methods=['POST'])
def agregar_carrito(restaurante_id, menu_id):
    if 'user_id' not in session:
        flash('Debes iniciar sesión para agregar al carrito.')
        return redirect(url_for('login'))

    cantidad = int(request.form.get('cantidad', 1))
    restaurante_id_str = str(restaurante_id)

    # Asegurar formato de diccionario
    if 'carrito' not in session or not isinstance(session['carrito'], dict):
        session['carrito'] = {}

    if restaurante_id_str not in session['carrito']:
        session['carrito'][restaurante_id_str] = []

    carrito_restaurante = session['carrito'][restaurante_id_str]

    # Buscar si ya existe
    for item in carrito_restaurante:
        if item['menu_id'] == menu_id:
            item['cantidad'] += cantidad
            session.modified = True
            return redirect(url_for('menu', restaurante_id=restaurante_id))

    # Agregar nuevo ítem
    menu = Menu.query.get(menu_id)
    if menu:
        nuevo_item = {
            'menu_id': menu_id,
            'nombre': menu.nombre,
            'precio': float(menu.precio),
            'cantidad': cantidad,
            'restaurante_id': restaurante_id
        }
        carrito_restaurante.append(nuevo_item)
        session['carrito'][restaurante_id_str] = carrito_restaurante
        session.modified = True

    return redirect(url_for('menu', restaurante_id=restaurante_id))

# Ruta para eliminar ítems del carrito
@app.route('/eliminar_carrito/<int:restaurante_id>/<int:menu_id>', methods=['POST'])
def eliminar_carrito(restaurante_id, menu_id):
    if 'user_id' not in session and 'guest' not in session:
        return redirect(url_for('login'))
    if 'guest' in session:
        flash('Los invitados no pueden modificar el carrito. Por favor, inicia sesión.')
        return redirect(url_for('menu', restaurante_id=restaurante_id))
    if 'carrito' not in session or str(restaurante_id) not in session['carrito']:
        flash('El carrito está vacío.')
        return redirect(url_for('menu', restaurante_id=restaurante_id))
    carrito = session['carrito'][str(restaurante_id)]
    session['carrito'][str(restaurante_id)] = [item for item in carrito if item['menu_id'] != menu_id]  # Eliminar ítem
    if not session['carrito'][str(restaurante_id)]:
        session['carrito'].pop(str(restaurante_id), None)  # Eliminar carrito si está vacío
    session.modified = True  # Marcar la sesión como modificada
    flash('Ítem eliminado del carrito.')
    return redirect(url_for('menu', restaurante_id=restaurante_id))





# -------------------------------------------------
#  RUTAS DE MERCADO AGRÍCOLA
# -------------------------------------------------
# Ruta del mercado agrícola
@app.route('/agricola')
@login_required_or_guest
def agricola_market():
    productos = ProductoAgricola.query.filter(ProductoAgricola.stock > 0).all()
    print(f"DEBUG: Productos encontrados: {len(productos)}")
    for p in productos:
        print(f"DEBUG: - {p.nombre} (Stock: {p.stock})")
    
    return render_template('agricola_market.html',
                           productos=productos,
                           carrito_agricola=session.get('carrito_agricola', []),
                           total_agricola=calc_total_agricola(session.get('carrito_agricola', [])))


# Añadir al carrito agrícola
@app.route('/agricola/add/<int:agricola_id>', methods=['POST'])
def agregar_carrito_agricola(agricola_id):
    prod = ProductoAgricola.query.get_or_404(agricola_id)
    cant = int(request.form['cantidad'])
    
    if cant > prod.stock:
        flash('No hay suficiente stock disponible')
        return redirect(url_for('agricola_market'))

    carrito = session.get('carrito_agricola', [])
    
    # Buscar si el producto ya está en el carrito
    item_existente = None
    for item in carrito:
        if item['id'] == prod.id:
            item_existente = item
            break
    
    if item_existente:
        # Verificar que no exceda el stock al actualizar
        if item_existente['cantidad'] + cant > prod.stock:
            flash('No hay suficiente stock disponible')
            return redirect(url_for('agricola_market'))
        item_existente['cantidad'] += cant
        item_existente['subtotal'] = item_existente['cantidad'] * prod.precio_venta
    else:
        carrito.append({
            'id': prod.id,
            'nombre': prod.nombre,
            'precio_venta': prod.precio_venta,
            'cantidad': cant,
            'subtotal': prod.precio_venta * cant
        })
    
    session['carrito_agricola'] = carrito
    flash('Producto añadido al carrito')
    return redirect(url_for('agricola_market'))

# Eliminar del carrito agrícola
@app.route('/agricola/remove/<int:agricola_id>', methods=['POST'])
def eliminar_carrito_agricola(agricola_id):
    carrito = session.get('carrito_agricola', [])
    session['carrito_agricola'] = [i for i in carrito if i['id'] != agricola_id]
    flash('Producto eliminado del carrito')
    return redirect(url_for('agricola_market'))

# Confirmar pedido agrícola
@app.route('/agricola/confirmar', methods=['POST'])
def confirmar_pedido_agricola():
    carrito = session.get('carrito_agricola', [])
    if not carrito:
        flash('Carrito vacío')
        return redirect(url_for('agricola_market'))

    # Verificar stock antes de procesar
    for item in carrito:
        producto = ProductoAgricola.query.get(item['id'])
        if producto.stock < item['cantidad']:
            flash(f'Stock insuficiente para {producto.nombre}')
            return redirect(url_for('agricola_market'))

    # Restar stock y crear pedido
    for item in carrito:
        producto = ProductoAgricola.query.get(item['id'])
        producto.stock -= item['cantidad']

    # Crear pedido agrícola
    pedido = PedidoAgricola(
        user_id=session.get('user_id'),
        total=sum(i['subtotal'] for i in carrito),
        tipo_entrega=request.form['tipo_entrega'],
        direccion=request.form.get('direccion'),
        telefono=request.form.get('telefono'),
        hora_recogida=request.form.get('hora_recogida')
    )
    
    db.session.add(pedido)
    db.session.flush()

    # Crear detalles del pedido
    for item in carrito:
        detalle = DetallePedidoAgricola(
            pedido_id=pedido.id,
            producto_id=item['id'],
            cantidad=item['cantidad'],
            precio_unitario=item['precio_venta']
        )
        db.session.add(detalle)

    db.session.commit()
    session.pop('carrito_agricola', None)
    flash('¡Pedido agrícola confirmado! Te contactaremos pronto.')
    return redirect(url_for('restaurantes'))






# Ruta para seleccionar método de pago
@app.route('/seleccionar_pago', methods=['POST'])
def seleccionar_pago():
    if 'user_id' not in session and 'guest' not in session:
        return redirect(url_for('login'))
    if 'guest' in session:
        flash('Los invitados no pueden seleccionar método de pago. Por favor, inicia sesión.')
        return redirect(url_for('restaurantes'))
    
    metodo_pago = request.form.get('metodo_pago')
    if metodo_pago not in ['tarjeta', 'banca_movil', 'transferencia']:
        flash('Método de pago inválido.')
        return redirect(url_for('restaurantes'))
    
    # === GUARDAR DETALLES ===
    if metodo_pago == 'tarjeta':
        numero_tarjeta = request.form.get('numero_tarjeta')
        fecha_vencimiento = request.form.get('fecha_vencimiento')
        cvv = request.form.get('cvv')
        if not (numero_tarjeta and fecha_vencimiento and cvv):
            flash('Por favor completa todos los datos de la tarjeta.')
            return redirect(url_for('restaurantes'))
        session['metodo_pago_detalle'] = f"Número: {numero_tarjeta[-4:]} **** **** ****"
    elif metodo_pago == 'banca_movil':
        numero_celular = request.form.get('numero_celular')
        nombre_titular = request.form.get('nombre_titular')
        if not (numero_celular and nombre_titular):
            flash('Por favor completa todos los datos de banca móvil.')
            return redirect(url_for('restaurantes'))
        session['metodo_pago_detalle'] = f"Celular: {numero_celular}"
    elif metodo_pago == 'transferencia':
        numero_cuenta = request.form.get('numero_cuenta')
        nombre_titular = request.form.get('nombre_titular')
        if not (numero_cuenta and nombre_titular):
            flash('Por favor completa todos los datos de la transferencia.')
            return redirect(url_for('restaurantes'))
        session['metodo_pago_detalle'] = f"Cuenta: {numero_cuenta[-4:]} ****"

    session['metodo_pago'] = metodo_pago
    flash(f'Método de pago seleccionado: {metodo_pago}')

    # OBTENER RESTAURANTE_ID DEL FORMULARIO
    restaurante_id = request.form.get('restaurante_id')
    if restaurante_id:
        return redirect(url_for('menu', restaurante_id=restaurante_id))
    else:
        return redirect(url_for('restaurantes'))
    


@app.route('/detalle_pago', methods=['GET', 'POST'])
@login_required_or_guest
def detalle_pago():
    """Muestra y procesa los detalles de pago"""
    if request.method == 'POST':
        # Procesar los datos del pago
        metodo_pago = request.form.get('metodo_pago')
        metodo_pago_detalle = request.form.get('metodo_pago_detalle')
        
        # Guardar en la sesión
        session['metodo_pago'] = metodo_pago
        session['metodo_pago_detalle'] = metodo_pago_detalle
        
        flash('Método de pago guardado correctamente.')
        return redirect(url_for('agricola_market'))
    
    return render_template('detalle_pago.html')



@app.route('/confirmar_pedido/<int:restaurante_id>', methods=['POST'])
def confirmar_pedido(restaurante_id):
    # === VALIDACIONES ===
    if 'user_id' not in session and 'guest' not in session:
        flash('Debes iniciar sesión.')
        return redirect(url_for('login'))
    if 'guest' in session:
        flash('Los invitados no pueden confirmar pedidos.')
        return redirect(url_for('menu', restaurante_id=restaurante_id))
    if 'carrito' not in session or str(restaurante_id) not in session['carrito']:
        flash('El carrito está vacío.')
        return redirect(url_for('menu', restaurante_id=restaurante_id))
    metodo_pago = session.get('metodo_pago')
    if not metodo_pago:
        flash('Selecciona un método de pago.')
        return redirect(url_for('menu', restaurante_id=restaurante_id))

    tipo_entrega = request.form.get('tipo_entrega')
    if tipo_entrega not in ['domicilio', 'reserva']:
        flash('Tipo de entrega inválido.')
        return redirect(url_for('menu', restaurante_id=restaurante_id))

    nombre_cliente = request.form.get('nombre_cliente')
    if not nombre_cliente:
        flash('El nombre es obligatorio.')
        return redirect(url_for('menu', restaurante_id=restaurante_id))

    # === DATOS SEGÚN TIPO ===
    if tipo_entrega == 'domicilio':
        direccion = request.form.get('direccion')
        numero_celular = request.form.get('numero_celular')
        if not direccion or not numero_celular:
            flash('Completa dirección y celular.')
            return redirect(url_for('menu', restaurante_id=restaurante_id))
        hora_reserva = fecha_reserva = None
    else:
        hora_reserva = request.form.get('hora_reserva')
        fecha_reserva = request.form.get('fecha_reserva')
        if not hora_reserva or not fecha_reserva:
            flash('Completa fecha y hora de reserva.')
            return redirect(url_for('menu', restaurante_id=restaurante_id))
        direccion = numero_celular = None

    # === CARRITO Y CÁLCULOS ===
    carrito = session['carrito'][str(restaurante_id)]
    items = []
    subtotal = 0
    for item in carrito:
        item_subtotal = item['cantidad'] * item['precio']
        items.append({
            'nombre': item['nombre'],
            'cantidad': item['cantidad'],
            'precio': item['precio'],
            'subtotal': item_subtotal
        })
        subtotal += item_subtotal

    iva = round(subtotal * 0.16, 2)
    total = subtotal + iva

    # === GENERAR CÓDIGO ÚNICO ===
    import uuid
    from datetime import datetime
    pedido_codigo = str(uuid.uuid4())[:8].upper()
    fecha_pedido = datetime.now().strftime("%d/%m/%Y %H:%M")

    # === GUARDAR PEDIDO ===
    pedido = Pedido(
        usuario_id=session['user_id'],
        restaurante_id=restaurante_id,
        total=total,
        metodo_pago=metodo_pago,
        metodo_pago_detalle=session.get('metodo_pago_detalle'),
        direccion_entrega=direccion,
        numero_celular=numero_celular,
        nombre_cliente=nombre_cliente,
        tipo_entrega=tipo_entrega,
        hora_reserva=hora_reserva,
        fecha_reserva=fecha_reserva,
        codigo_pedido=pedido_codigo  # AQUÍ SE GUARDA
    )
    db.session.add(pedido)
    db.session.flush()

    # === GUARDAR ÍTEMS ===
    for item in carrito:
        item_pedido = PedidoItem(
            pedido_id=pedido.id,
            menu_id=item['menu_id'],
            cantidad=item['cantidad'],
            precio=item['precio']
        )
        db.session.add(item_pedido)

    db.session.commit()

    # === LIMPIAR CARRITO DEL RESTAURANTE ===
    if 'carrito' in session and str(restaurante_id) in session['carrito']:
        session['carrito'].pop(str(restaurante_id), None)
        if not session['carrito']:
            session.pop('carrito', None)
    session.modified = True

    # === OBTENER RESTAURANTE ===
    restaurante = Restaurante.query.get_or_404(restaurante_id)

    # === RENDERIZAR FACTURA ===
    return render_template(
        'factura.html',
        pedido_id=pedido_codigo,
        fecha_pedido=fecha_pedido,
        numero_pedido=pedido.id,
        nombre_cliente=nombre_cliente,
        tipo_entrega=tipo_entrega,
        direccion=direccion,
        numero_celular=numero_celular,
        hora_reserva=hora_reserva,
        fecha_reserva=fecha_reserva,
        items=items,
        subtotal=subtotal,
        iva=iva,
        total=total,
        metodo_pago=metodo_pago,
        restaurante=restaurante
    )

# Ruta para el panel de administración
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        if 'restaurante' in request.form:
            nombre = request.form['nombre']
            descripcion = request.form['descripcion']
            categoria = request.form['categoria']
            imagen_file = request.files.get('imagen')
            
            imagen_path = None
            if imagen_file and allowed_file(imagen_file.filename):
                filename = secure_filename(imagen_file.filename)
                imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                imagen_file.save(imagen_path)  # Guardar imagen
                imagen_path = imagen_path.replace('static/', '')
            else:
                local_image_path = 'C:/Users/ASUS/Pictures/imagen.jpg'
                imagen_path = copy_image_from_path(local_image_path, app.config['UPLOAD_FOLDER'])
            
            restaurante = Restaurante(
                nombre=nombre,
                descripcion=descripcion,
                categoria=categoria,
                imagen=imagen_path if imagen_path else 'uploads/default.jpg'
            )  # Crear nuevo restaurante
            db.session.add(restaurante)
            db.session.commit()
            flash('Restaurante añadido.')
        elif 'menu' in request.form:
            restaurante_id = request.form['restaurante_id']
            nombre = request.form['nombre']
            descripcion = request.form['descripcion']
            precio = float(request.form['precio'])
            categoria = request.form['categoria']
            imagen_file = request.files.get('imagen')
            
            imagen_path = None
            if imagen_file and allowed_file(imagen_file.filename):
                filename = secure_filename(imagen_file.filename)
                imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                imagen_file.save(imagen_path)
                imagen_path = imagen_path.replace('static/', '')
            else:
                local_image_path = 'C:/Users/ASUS/Pictures/imagen_menu.jpg'
                imagen_path = copy_image_from_path(local_image_path, app.config['UPLOAD_FOLDER'])
            
            menu = Menu(
                restaurante_id=restaurante_id,
                nombre=nombre,
                descripcion=descripcion,
                precio=precio,
                categoria=categoria,
                imagen=imagen_path if imagen_path else 'uploads/default.jpg'
            )  # Crear nuevo menú
            db.session.add(menu)
            db.session.commit()
            flash('Menú añadido.')
    restaurantes = Restaurante.query.all()
    menus = Menu.query.all()
    return render_template('admin.html', restaurantes=restaurantes, menus=menus)


@app.route('/admin/finanzas', methods=['GET', 'POST'])
def admin_finanzas():
    # 1. Verificar que sea administrador
    if 'admin_id' not in session:
        flash('Acceso denegado. Debes ser administrador.', 'danger')
        return redirect(url_for('login'))

    # 2. Verificación de la clave secreta (doble autenticación)
    if request.method == 'POST':
        clave_ingresada = request.form.get('clave', '').strip()
        if clave_ingresada == FINANZAS_KEY:
            session['finanzas_auth'] = True
        else:
            flash('Clave incorrecta. Acceso denegado.', 'danger')
            return render_template('finanzas_login.html')

    # 3. Si no tiene autorización de finanzas, mostrar login
    if not session.get('finanzas_auth'):
        return render_template('finanzas_login.html')

    # 4. === CÁLCULO DE DATOS FINANCIEROS ===
    from datetime import datetime
    from sqlalchemy import extract

    hoy = datetime.now()
    mes_actual_num = hoy.month
    año_actual = hoy.year

    # Todos los restaurantes
    restaurantes = Restaurante.query.all()

    reporte_restaurantes = []
    total_ingresos = total_costos = total_ganancia = 0

    for rest in restaurantes:
        # Sumar ingresos del restaurante
        pedidos = Pedido.query.filter_by(restaurante_id=rest.id).all()
        ingresos = sum(p.total for p in pedidos if p.total)

        # Estimaciones realistas (puedes ajustar estos porcentajes)
        costo = ingresos * 0.60                    # 60% costo operativo
        ganancia = ingresos * 0.40                  # 40% ganancia neta

        # Balance simplificado
        activo_corriente = ingresos * 0.75
        activo_no_corriente = ingresos * 0.25
        total_activos = activo_corriente + activo_no_corriente

        pasivo_corriente = costo * 0.85
        pasivo_no_corriente = costo * 0.15
        total_pasivos = pasivo_corriente + pasivo_no_corriente

        patrimonio = total_activos - total_pasivos

        reporte_restaurantes.append({
            'restaurante': rest,
            'ingresos': round(ingresos, 2),
            'costo': round(costo, 2),
            'ganancia': round(ganancia, 2),
            'activo_corriente': round(activo_corriente, 2),
            'activo_no_corriente': round(activo_no_corriente, 2),
            'total_activos': round(total_activos, 2),
            'pasivo_corriente': round(pasivo_corriente, 2),
            'pasivo_no_corriente': round(pasivo_no_corriente, 2),
            'total_pasivos': round(total_pasivos, 2),
            'patrimonio': round(patrimonio, 2)
        })

        total_ingresos += ingresos
        total_costos += costo
        total_ganancia += ganancia

    # === RESUMEN MENSUAL Y ANUAL ===
    pedidos_mes = Pedido.query.filter(
        extract('month', Pedido.fecha) == mes_actual_num,
        extract('year', Pedido.fecha) == año_actual
    ).all()
    ingresos_mes = sum(p.total for p in pedidos_mes if p.total)
    ganancia_mes = ingresos_mes * 0.40

    pedidos_año = Pedido.query.filter(
        extract('year', Pedido.fecha) == año_actual
    ).all()
    ingresos_año = sum(p.total for p in pedidos_año if p.total)
    ganancia_año = ingresos_año * 0.40

    # === ENVÍO AL TEMPLATE (TODAS LAS VARIABLES NECESARIAS) ===
    return render_template(
        'admin_finanzas.html',
        hoy=hoy,                                      # Para la fecha bonita
        reporte_restaurantes=reporte_restaurantes,
        total_ingresos=round(total_ingresos, 2),
        total_costos=round(total_costos, 2),
        total_ganancia=round(total_ganancia, 2),
        ingresos_mes=round(ingresos_mes, 2),
        ganancia_mes=round(ganancia_mes, 2),
        ingresos_año=round(ingresos_año, 2),
        ganancia_año=round(ganancia_año, 2),
        mes_actual=hoy.strftime('%B %Y'),             # Ej: "noviembre 2025"
        año_actual=año_actual
    )



# Ruta para eliminar un restaurante
@app.route('/eliminar_restaurante/<int:restaurante_id>', methods=['POST'])
def eliminar_restaurante(restaurante_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    restaurante = Restaurante.query.get_or_404(restaurante_id)  # Obtener restaurante o devolver 404
    db.session.delete(restaurante)
    db.session.commit()
    flash('Restaurante eliminado exitosamente.')
    return redirect(url_for('admin'))

# Ruta para eliminar un menú
@app.route('/eliminar_menu/<int:menu_id>', methods=['POST'])
def eliminar_menu(menu_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    menu = Menu.query.get_or_404(menu_id)  # Obtener menú o devolver 404
    db.session.delete(menu)
    db.session.commit()
    flash('Menú eliminado exitosamente.')
    return redirect(url_for('admin'))

# Ruta para actualizar un restaurante
@app.route('/actualizar_restaurante/<int:restaurante_id>', methods=['GET', 'POST'])
def actualizar_restaurante(restaurante_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    restaurante = Restaurante.query.get_or_404(restaurante_id)  # Obtener restaurante o devolver 404
    if request.method == 'POST':
        restaurante.nombre = request.form['nombre']
        restaurante.descripcion = request.form['descripcion']
        restaurante.categoria = request.form['categoria']
        imagen_file = request.files.get('imagen')
        
        if imagen_file and allowed_file(imagen_file.filename):
            filename = secure_filename(imagen_file.filename)
            imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagen_file.save(imagen_path)
            restaurante.imagen = imagen_path.replace('static/', '')  # Actualizar imagen
        
        db.session.commit()
        flash('Restaurante actualizado exitosamente.')
        return redirect(url_for('admin'))
    
    return render_template('actualizar_restaurante.html', restaurante=restaurante)

# Ruta para actualizar un menú
@app.route('/actualizar_menu/<int:menu_id>', methods=['GET', 'POST'])
def actualizar_menu(menu_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    menu = Menu.query.get_or_404(menu_id)  # Obtener menú o devolver 404
    restaurantes = Restaurante.query.all()  # Obtener todos los restaurantes
    if request.method == 'POST':
        menu.restaurante_id = request.form['restaurante_id']
        menu.nombre = request.form['nombre']
        menu.descripcion = request.form['descripcion']
        menu.precio = float(request.form['precio'])
        menu.categoria = request.form['categoria']
        imagen_file = request.files.get('imagen')
        
        if imagen_file and allowed_file(imagen_file.filename):
            filename = secure_filename(imagen_file.filename)
            imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagen_file.save(imagen_path)
            menu.imagen = imagen_path.replace('static/', '')  # Actualizar imagen
        
        db.session.commit()
        flash('Menú actualizado exitosamente.')
        return redirect(url_for('admin'))
    
    return render_template('actualizar_menu.html', menu=menu, restaurantes=restaurantes)




# === PÁGINA GESTIÓN AGRÍCOLA ===
@app.route('/admin/agricola', methods=['GET', 'POST'])
def admin_agricola():
    if 'admin_id' not in session:
        return redirect(url_for('login'))

    productos = ProductoAgricola.query.all()

    if request.method == 'POST':
        if 'agricola' in request.form:
            nombre = request.form['nombre']
            descripcion = request.form['descripcion']
            precio_compra = float(request.form['precio_compra'])
            precio_venta = float(request.form['precio_venta'])
            stock = int(request.form['stock'])

            imagen_path = 'uploads/agricola_default.jpg'
            if 'imagen' in request.files:
                file = request.files['imagen']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(path)
                    imagen_path = f'uploads/{filename}'

            nuevo = ProductoAgricola(
                nombre=nombre,
                descripcion=descripcion,
                precio_compra=precio_compra,
                precio_venta=precio_venta,
                stock=stock,
                imagen=imagen_path
            )
            db.session.add(nuevo)
            db.session.commit()
            flash(f'Producto agrícola "{nombre}" añadido.')

    return render_template('admin_agricola.html', productos=productos)

# === ELIMINAR PRODUCTO AGRÍCOLA ===
@app.route('/admin/agricola/eliminar/<int:id>', methods=['POST'])
def eliminar_agricola(id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    producto = ProductoAgricola.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    flash(f'Producto agrícola eliminado.')
    return redirect(url_for('admin_agricola'))







# Nuevas rutas API para el chatbot (JSON)
@app.route('/api/restaurantes', methods=['GET'])
def api_restaurantes():
    restaurantes = Restaurante.query.all()
    return jsonify([{
        'id': r.id,
        'nombre': r.nombre,
        'descripcion': r.descripcion,
        'categoria': r.categoria
    } for r in restaurantes])

@app.route('/api/menus/<int:restaurante_id>', methods=['GET'])
def api_menus(restaurante_id):
    menus = Menu.query.filter_by(restaurante_id=restaurante_id).all()
    return jsonify([{
        'id': m.id,
        'nombre': m.nombre,
        'descripcion': m.descripcion,
        'precio': m.precio,
        'categoria': m.categoria
    } for m in menus])

@app.route('/api/agregar_carrito', methods=['POST'])
def api_agregar_carrito():
    if 'user_id' not in session:
        return jsonify({'error': 'Debes iniciar sesión para agregar al carrito'}), 403

    data = request.json
    restaurante_id = str(data.get('restaurante_id'))
    menu_id = data.get('menu_id')
    cantidad = data.get('cantidad', 1)

    # Inicializar carrito como diccionario si no existe
    if 'carrito' not in session or not isinstance(session['carrito'], dict):
        session['carrito'] = {}

    # Asegurar que el restaurante tenga una lista
    if restaurante_id not in session['carrito']:
        session['carrito'][restaurante_id] = []

    carrito_restaurante = session['carrito'][restaurante_id]

    # Buscar si el ítem ya existe
    for item in carrito_restaurante:
        if item['menu_id'] == menu_id:
            item['cantidad'] += cantidad
            session.modified = True
            return jsonify({'success': True, 'message': f'{cantidad} ítem(s) agregado(s)'})

    # Si no existe, obtener datos del menú
    menu = Menu.query.get(menu_id)
    if not menu:
        return jsonify({'error': 'Menú no encontrado'}), 404

    # Agregar nuevo ítem
    nuevo_item = {
        'menu_id': menu_id,
        'nombre': menu.nombre,
        'precio': float(menu.precio),
        'cantidad': cantidad,
        'restaurante_id': int(restaurante_id)
    }
    carrito_restaurante.append(nuevo_item)
    session['carrito'][restaurante_id] = carrito_restaurante
    session.modified = True

    return jsonify({'success': True, 'message': 'Ítem agregado al carrito'})
    

@app.route('/api/carrito_resumen')
def api_carrito_resumen():
    if 'carrito' not in session or not isinstance(session['carrito'], dict):
        return jsonify({'restaurantes': []})
    
    resumen = []
    for rest_id, items in session['carrito'].items():
        if items:
            resumen.append({
                'restaurante_id': int(rest_id),
                'total_items': sum(i['cantidad'] for i in items)
            })
    return jsonify({'restaurantes': resumen})





@app.route('/editar_carrito/<int:restaurante_id>/<int:menu_id>', methods=['POST'])
def editar_carrito(restaurante_id, menu_id):
    if 'user_id' not in session:
        flash('Debes iniciar sesión.')
        return redirect(url_for('login'))

    nueva_cantidad = int(request.form.get('cantidad', 1))
    restaurante_id_str = str(restaurante_id)

    if 'carrito' not in session or not isinstance(session['carrito'], dict):
        session['carrito'] = {}

    if restaurante_id_str not in session['carrito']:
        return redirect(url_for('menu', restaurante_id=restaurante_id))

    # Buscar y actualizar
    for item in session['carrito'][restaurante_id_str]:
        if item['menu_id'] == menu_id:
            if nueva_cantidad <= 0:
                session['carrito'][restaurante_id_str].remove(item)
                flash('Ítem eliminado.')
            else:
                item['cantidad'] = nueva_cantidad
                flash(f'Cantidad actualizada a {nueva_cantidad}.')
            session.modified = True
            break

    return redirect(url_for('menu', restaurante_id=restaurante_id))











# Contexto de la aplicación para inicializar la base de datos y poblar datos iniciales
with app.app_context():
   # db.create_all()  # Crear todas las tablas definidas


    # === DATOS INICIALES PARA PRODUCTOS AGRÍCOLAS ===
    if not ProductoAgricola.query.first():
        productos_agricolas = [
            ProductoAgricola(
                nombre='Papas Criollas',
                descripcion='Papas criollas frescas, ideales para sancochos y guisos. Sabor auténtico y textura cremosa.',
                precio_compra=2.50,
                precio_venta=4.00,
                stock=120,
                imagen='uploads/papas.jfif'
            ),
            ProductoAgricola(
                nombre='Tomates Maduros',
                descripcion='Tomates rojos maduros, jugosos y dulces. Perfectos para salsas, ensaladas y guisos.',
                precio_compra=3.20,
                precio_venta=5.50,
                stock=80,
                imagen='uploads/tomates.jfif'
            ),
            ProductoAgricola(
                nombre='Cebolla Cabezona',
                descripcion='Cebolla cabezona blanca, esencial para sofritos, sopas y todo tipo de preparaciones.',
                precio_compra=2.80,
                precio_venta=4.20,
                stock=95,
                imagen='uploads/cebollas.jfif'
            ),
            ProductoAgricola(
                nombre='Arveja Fresca',
                descripcion='Arveja fresca y dulce, ideal para guisos, sopas y ensaladas. Alto valor nutricional.',
                precio_compra=4.50,
                precio_venta=6.80,
                stock=60,
                imagen='uploads/arvejas.jfif'
            ),
            ProductoAgricola(
                nombre='Zanahoria Orgánica',
                descripcion='Zanahorias orgánicas crujientes y dulces. Perfectas para jugos, ensaladas y guarniciones.',
                precio_compra=2.20,
                precio_venta=3.80,
                stock=110,
                imagen='uploads/zanahorias.jfif'
            ),
            ProductoAgricola(
                nombre='Cilantro Fresco',
                descripcion='Cilantro fresco recién cosechado. Aroma intenso para sopas, guisos y salsas.',
                precio_compra=1.80,
                precio_venta=3.00,
                stock=75,
                imagen='uploads/cilantro.jfif'
            ),
            ProductoAgricola(
                nombre='Ajo Nacional',
                descripcion='Ajo fresco nacional, esencial para dar sabor a todo tipo de preparaciones culinarias.',
                precio_compra=3.50,
                precio_venta=5.20,
                stock=50,
                imagen='uploads/ajos.jfif'
            )
        ]
        
        db.session.bulk_save_objects(productos_agricolas)
        db.session.commit()
        print("✅ Productos agrícolas básicos creados: Papas, Tomates, Cebollas, Arveja, Zanahoria")





    if not Restaurante.query.first():  # Verificar si no hay restaurantes
        restaurante_image_path = 'C:/Users/ASUS/Pictures/restaurante.jpg'  # Ruta de imagen predeterminada para restaurantes
        menu_image_path = 'C:/Users/ASUS/Pictures/menu.jpg'  # Ruta de imagen predeterminada para menús
        
        # Lista de restaurantes iniciales
        restaurantes = [
            Restaurante(
                nombre='Wabi Sabi Sushi Bar',
                descripcion='Restaurante especializado en sushi y cocina japonesa auténtica',
                categoria='Sushi',
                imagen='uploads/wabisabisushibar.jpg'
            ),
            Restaurante(
                nombre='PamDay',
                descripcion='Sushi fresco y auténtico con un toque moderno',
                categoria='Sushi',
                imagen=copy_image_from_path(restaurante_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/pamday.jpg'
            )
        ]
        
        # Agregar más restaurantes
        restaurantes.extend([
            Restaurante(
                nombre='Pollo Broaster La Brasil',
                descripcion='Especialistas en pollo broaster crujiente',
                categoria='Pollo',
                imagen=copy_image_from_path(restaurante_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/pollobrosterlabrasil.jpg'
            ),
            Restaurante(
                nombre='Kroky',
                descripcion='Pollo broaster con un toque único',
                categoria='Pollo',
                imagen=copy_image_from_path(restaurante_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/kroky.jpg'
            )
        ])
        
        restaurantes.extend([
            Restaurante(
                nombre="Q'Riko!",
                descripcion='Sabores auténticos de la cocina china',
                categoria='Casa China',
                imagen=copy_image_from_path(restaurante_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/qriko.jpg'
            ),
            Restaurante(
                nombre="FORTUNA'Z",
                descripcion='Tradición china en cada plato',
                categoria='Casa China',
                imagen=copy_image_from_path(restaurante_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/fortunaz.jpg'
            ),
            Restaurante(
                nombre='Casa China Restaurante',
                descripcion='Un clásico de la comida china',
                categoria='Casa China',
                imagen=copy_image_from_path(restaurante_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/casachinarestaurante.jpg'
            )
        ])
        
        restaurantes.extend([
            Restaurante(
                nombre='Alitas y algo más',
                descripcion='Alitas y opciones rápidas para todos los gustos',
                categoria='Comidas Rápidas',
                imagen=copy_image_from_path(restaurante_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/alitasyalgomas.jpg'
            ),
            Restaurante(
                nombre='Chervo Pizza',
                descripcion='Pizzas rápidas y deliciosas',
                categoria='Comidas Rápidas',
                imagen=copy_image_from_path(restaurante_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/chervopizza.jpg'
            ),
            Restaurante(
                nombre='Pizzeria LUWAK',
                descripcion='Pizzas artesanales para llevar',
                categoria='Comidas Rápidas',
                imagen=copy_image_from_path(restaurante_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/pizerialuwak.jpg'
            ),
            Restaurante(
                nombre='Pizza Express',
                descripcion='Entrega rápida de pizzas frescas',
                categoria='Comidas Rápidas',
                imagen=copy_image_from_path(restaurante_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/pizzaexpress.jpg'
            )
        ])
        
        db.session.bulk_save_objects(restaurantes)  # Guardar restaurantes en la base de datos
        db.session.commit()

        # Menús para Wabi Sabi Sushi Bar
        menus_wabi = [
            Menu(
                restaurante_id=1,
                nombre='Edamame',
                descripcion='Vainas de soja al vapor',
                precio=4.50,
                categoria='Entradas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Edamame.jpeg'
            ),
            Menu(
                restaurante_id=1,
                nombre='Vegetales Tempura',
                descripcion='Mix de vegetales de tempura, rebosados en tempura, acompañados de salsa ponzu',
                precio=5.00,
                categoria='Entradas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/VegetalesTempura.jpeg'
            ),
            Menu(
                restaurante_id=1,
                nombre='Guozas de Cerdo',
                descripcion='Tradicionales empanadillas japonesas rellenas de cerdo, cebolla, jengibre y col',
                precio=5.00,
                categoria='Entradas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/GuozasdeCerdo.jpeg'
            ),
            Menu(
                restaurante_id=1,
                nombre='Okonomiyaki de Cerdo',
                descripcion='Tradicional tortilla japonesa cocida a la plancha rellena de cerdo y vegetales con una cobertura de salsa TonKatsu, mayonesa y katsuobushi',
                precio=7.50,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/OkonomiyakideCerdo.jpeg'
            ),
            Menu(
                restaurante_id=1,
                nombre='Karaage',
                descripcion='Pollo frito estilo japonés, guarnición de arroz furikake',
                precio=9.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Karaage.jpeg'
            ),
            Menu(
                restaurante_id=1,
                nombre='Ramen Vegetariano',
                descripcion='Sopa a base de fondo de vegetales y hongos shitake. Ajitama, huevo cocido marinado, maíz dulce, tofu al banco y vegetales de temporada',
                precio=9.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/RamenVegetariano.jpeg'
            )
        ]
        db.session.bulk_save_objects(menus_wabi)
        db.session.commit()

        # Menús para PamDay
        menus_pamday = [
            Menu(
                restaurante_id=2,
                nombre='Tokio Sushi',
                descripcion='12 bocados de sushi, 1 tipo de rollito a elección acompañados con vegetales y s17.50',
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Kappuru.jpeg'
            ),
            Menu(
                restaurante_id=2,
                nombre='Kita Midori',
                descripcion='Camarón furai, queso crema, vegetales tempura, cubierto de aguacate caramelizado',
                precio=8.00,
                categoria='Rollitos',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/KitaMidori.jpeg'
            ),
            Menu(
                restaurante_id=2,
                nombre='Ramen',
                descripcion='Una perfecta combinación de sabores, viene acompañado por panceta, naruto (cangrejo), cebollín, champiñones, zanahoria y huevo cocido marinado en una salsa especial',
                precio=5.50,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Ramen.jpeg'
            ),
            Menu(
                restaurante_id=2,
                nombre='Sushi Dog',
                descripcion='Un rollo crocante, frito totalmente cubierto de panko y relleno de pollo especial bbq, lechuga y aguacate cubierto con una mayonesa especial y queso cheddar semipicante',
                precio=6.75,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/SushiDog.jpeg'
            ),
            Menu(
                restaurante_id=2,
                nombre='Infusión Maracuyá',
                descripcion='Bebida refrescante a base de maracuyá',
                precio=1.50,
                categoria='Bebidas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/InfusiónMaracuyá.jpeg'
            )
        ]
        db.session.bulk_save_objects(menus_pamday)
        db.session.commit()

        # Menús para Pollo Broaster La Brasil
        menus_pollobrasil = [
            Menu(
                restaurante_id=3,
                nombre='Papas fritas + Presa de pollo',
                descripcion='Porción de papas fritas acompañada de una presa de pollo',
                precio=1.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/papas + presa.png'
            ),
            Menu(
                restaurante_id=3,
                nombre='Arroz + Papas fritas + Presa de pollo',
                descripcion='Combinación de arroz, papas fritas y una presa de pollo',
                precio=1.30,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/arroz + papas +presa.jpeg'
            ),
            Menu(
                restaurante_id=3,
                nombre='Arroz + Papas fritas + Pechuga',
                descripcion='Combinación de arroz, papas fritas y una pechuga de pollo',
                precio=1.50,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/arroz + papas + pechuga.jpeg'
            ),
            Menu(
                restaurante_id=3,
                nombre='Papas fritas + 2 Presas de pollo',
                descripcion='Porción de papas fritas con dos presas de pollo',
                precio=2.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/papas + 2 presas.jpeg'
            ),
            Menu(
                restaurante_id=3,
                nombre='Choripapa',
                descripcion='Papas fritas con chorizo',
                precio=1.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/choripapa.jpeg'
            ),
            Menu(
                restaurante_id=3,
                nombre='Salchipapa',
                descripcion='Papas fritas con salchicha',
                precio=0.70,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/salchipapa.jpeg'
            )
        ]
        db.session.bulk_save_objects(menus_pollobrasil)
        db.session.commit()

        # Menús para Kroky
        menus_kroky = [
            Menu(
                restaurante_id=4,
                nombre='1/2 Porción: 1 Presa + Papas',
                descripcion='Media porción con una presa de pollo y papas fritas',
                precio=2.35,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/1-2Porción1Presa+Papas.jpeg'
            ),
            Menu(
                restaurante_id=4,
                nombre='1 Porción: 2 Presas + Papas',
                descripcion='Porción completa con dos presas de pollo y papas fritas',
                precio=3.90,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/1Porción2 Presas+Papas.jpeg'
            ),
            Menu(
                restaurante_id=4,
                nombre='1/2 Pollo: 4 Presas + Papas',
                descripcion='Media pollo con cuatro presas y papas fritas',
                precio=8.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/1-2Pollo4Presas+Papas.jpeg'
            ),
            Menu(
                restaurante_id=4,
                nombre='1 Pollo: 8 Presas + Papas',
                descripcion='Pollo entero con ocho presas y papas fritas',
                precio=15.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/1Pollo8Presas+Papas.jpeg'
            ),
            Menu(
                restaurante_id=4,
                nombre='Hamburguesa',
                descripcion='Hamburguesa clásica',
                precio=2.50,
                categoria='Comidas Rápidas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Hamburguesa.jpeg'
            ),
            Menu(
                restaurante_id=4,
                nombre='Salchipapa',
                descripcion='Papas fritas con salchicha',
                precio=2.00,
                categoria='Comidas Rápidas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Salchipapa.jpeg'
            )
        ]
        db.session.bulk_save_objects(menus_kroky)
        db.session.commit()

        # Menús para Q'Riko!
        menus_qriko = [
            Menu(
                restaurante_id=5,
                nombre='Chaufa de Pollo',
                descripcion='Arroz frito con pollo, verduras y salsa de soja',
                precio=2.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/chaufa pollo.jpeg'
            ),
            Menu(
                restaurante_id=5,
                nombre='Chaufa de Carne',
                descripcion='Arroz frito con carne, verduras y salsa de soja',
                precio=2.20,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/chaulafan de carne.jpeg'
            ),
            Menu(
                restaurante_id=5,
                nombre='Chaufa Mixto',
                descripcion='Arroz frito con pollo, carne, verduras y salsa de soja',
                precio=2.50,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/chaulafan de mixto.jpeg'
            ),
            Menu(
                restaurante_id=5,
                nombre='Pollo Chi jau kai',
                descripcion='Pollo apanado con salsa agridulce y verduras',
                precio=2.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/pollo chi.jpeg'
            ),
            Menu(
                restaurante_id=5,
                nombre='Tallarín Saltado de Pollo',
                descripcion='Tallarines salteados con pollo y verduras',
                precio=2.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/tallarin salteado de pollo.jpeg'
            ),
            Menu(
                restaurante_id=5,
                nombre='Tallarín Saltado Mixto',
                descripcion='Tallarines salteados con pollo, carne y verduras',
                precio=2.50,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/tallarin salteado mixto.jpeg'
            )
        ]
        db.session.bulk_save_objects(menus_qriko)
        db.session.commit()

        # Menús para FORTUNA'Z
        menus_fortunaz = [
            Menu(
                restaurante_id=6,
                nombre='Chaufa de Pollo',
                descripcion='Arroz frito con pollo, verduras y salsa de soja',
                precio=2.50,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/chaufa pollo 2.jpeg'
            ),
            Menu(
                restaurante_id=6,
                nombre='Taypa Especial',
                descripcion='Combinación de carnes y verduras salteadas en salsa especial',
                precio=8.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/taypa.jpeg'
            ),
            Menu(
                restaurante_id=6,
                nombre='Pollo Tipakay',
                descripcion='Pollo apanado con salsa agridulce y acompañamiento',
                precio=2.50,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/tipakay.jpeg'
            ),
            Menu(
                restaurante_id=6,
                nombre='Aeropuerto Especial',
                descripcion='Arroz chaufa con tallarines, pollo, carne y verduras',
                precio=4.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/aeropuerto especial.jpeg'
            )
        ]
        db.session.bulk_save_objects(menus_fortunaz)
        db.session.commit()

        # Menús para Casa China Restaurante
        menus_casachina = [
            Menu(
                restaurante_id=7,
                nombre='Chaufa de Pollo',
                descripcion='Arroz frito con pollo, verduras y salsa de soja',
                precio=2.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/chaulafan de pollo.jpeg'
            ),
            Menu(
                restaurante_id=7,
                nombre='Pollo Chi Jau Kai',
                descripcion='Pollo apanado con salsa agridulce y verduras',
                precio=2.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/pollo chi2.jpeg'
            ),
            Menu(
                restaurante_id=7,
                nombre='Chaufa de Pollo',
                descripcion='Arroz frito con pollo, verduras y salsa de soja',
                precio=2.50,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/chaufa pollo.jpeg'
            ),
            Menu(
                restaurante_id=7,
                nombre='Taypa Especial',
                descripcion='Combinación de carnes y verduras salteadas en salsa especial',
                precio=8.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/taypa.jpeg'
            ),
            Menu(
                restaurante_id=7,
                nombre='Pollo Tipakay',
                descripcion='Pollo apanado con salsa agridulce y acompañamiento',
                precio=2.50,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/tipakay.jpeg'
            ),
            Menu(
                restaurante_id=7,
                nombre='Aeropuerto Especial',
                descripcion='Arroz chaufa con tallarines, pollo, carne y verduras',
                precio=4.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/aeropuerto especial.jpeg'
            )
        ]
        db.session.bulk_save_objects(menus_casachina)
        db.session.commit()

        # Menús para Alitas y algo más
        menus_alitas = [
            Menu(
                restaurante_id=8,
                nombre='Alitas BBQ (6 unidades)',
                descripcion='Alitas de pollo con salsa BBQ, acompañadas de papas fritas',
                precio=4.50,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Alitas BBQ (6 unidades).jpeg'
            ),
            Menu(
                restaurante_id=8,
                nombre='Alitas Picantes (6 unidades)',
                descripcion='Alitas de pollo con salsa picante, acompañadas de papas fritas',
                precio=4.50,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Alitas Picantes (6 unidades).jpeg'
            ),
            Menu(
                restaurante_id=8,
                nombre='Hamburguesa Clásica',
                descripcion='Hamburguesa con carne, lechuga, tomate y salsa especial',
                precio=3.00,
                categoria='Comidas Rápidas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Hamburguesa Clásica.jpeg'
            ),
            Menu(
                restaurante_id=8,
                nombre='Salchipapa Grande',
                descripcion='Papas fritas con salchicha y salsas',
                precio=2.50,
                categoria='Comidas Rápidas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Salchipapa Grande.jpeg'
            ),
            Menu(
                restaurante_id=8,
                nombre='Combo Familiar (12 alitas)',
                descripcion='12 alitas (mezcla de BBQ y picantes) con papas fritas grandes',
                precio=8.00,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Combo Familiar (12 alitas).jpeg'
            ),
            Menu(
                restaurante_id=8,
                nombre='Nuggets de Pollo (8 unidades)',
                descripcion='Nuggets de pollo crujientes con salsa a elección',
                precio=3.50,
                categoria='Platos Fuertes',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Nuggets de Pollo (8 unidades).jpeg'
            )
        ]
        db.session.bulk_save_objects(menus_alitas)
        db.session.commit()

        # Menús para Chervo Pizza
        menus_chervo = [
            Menu(
                restaurante_id=9,
                nombre='Pizza Hawaiana (Mediana)',
                descripcion='Pizza con jamón, piña, queso mozzarella y salsa de tomate',
                precio=6.00,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Pizza Hawaiana (Mediana).jpeg'
            ),
            Menu(
                restaurante_id=9,
                nombre='Pizza Pepperoni (Mediana)',
                descripcion='Pizza con pepperoni, queso mozzarella y salsa de tomate',
                precio=6.50,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/pizza peperoni.jpeg'
            ),
            Menu(
                restaurante_id=9,
                nombre='Pizza Vegetariana (Mediana)',
                descripcion='Pizza con vegetales frescos, queso mozzarella y salsa de tomate',
                precio=5.50,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/pizza vegetariana.jpeg'
            ),
            Menu(
                restaurante_id=9,
                nombre='Pizza Suprema (Grande)',
                descripcion='Pizza con pepperoni, jamón, champiñones, pimientos y queso',
                precio=9.00,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Pizza Suprema (Grande).jpeg'
            ),
            Menu(
                restaurante_id=9,
                nombre='Pizza Cuatro Quesos (Mediana)',
                descripcion='Pizza con mozzarella, cheddar, parmesano y gorgonzola',
                precio=7.00,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Pizza Cuatro Quesos (Mediana).jpeg'
            ),
            Menu(
                restaurante_id=9,
                nombre='Pizza Margarita (Pequeña)',
                descripcion='Pizza clásica con tomate, mozzarella y albahaca',
                precio=4.00,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Pizza Margarita (Pequeña).jpeg'
            )
        ]
        db.session.bulk_save_objects(menus_chervo)
        db.session.commit()

        # Menús para Pizzeria LUWAK
        menus_luwak = [
            Menu(
                restaurante_id=10,
                nombre='Pizza Clásica de Jamón (Mediana)',
                descripcion='Pizza con jamón, queso mozzarella y salsa de tomate',
                precio=5.50,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/pizza jamon.jpeg'
            ),
            Menu(
                restaurante_id=10,
                nombre='Pizza de Pepperoni (Mediana)',
                descripcion='Pizza con pepperoni, queso mozzarella y salsa de tomate',
                precio=6.00,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/pizza peperoni.jpeg'
            ),
            Menu(
                restaurante_id=10,
                nombre='Pizza Vegetariana (Grande)',
                descripcion='Pizza con vegetales frescos, queso y salsa de tomate',
                precio=8.00,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/pizza vegetariana.jpeg'
            ),
            Menu(
                restaurante_id=10,
                nombre='Pizza de Pollo BBQ (Mediana)',
                descripcion='Pizza con pollo, salsa BBQ, queso y cebolla',
                precio=6.50,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/pizza bbq.jpeg'
            ),
            Menu(
                restaurante_id=10,
                nombre='Pizza de Champiñones (Pequeña)',
                descripcion='Pizza con champiñones, queso mozzarella y salsa de tomate',
                precio=4.50,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/pizza champiñones.jpeg'
            ),
            Menu(
                restaurante_id=10,
                nombre='Pizza Mixta (Grande)',
                descripcion='Pizza con jamón, pepperoni, vegetales y queso',
                precio=9.50,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/pizza mixta.jpeg'
            )
        ]
        db.session.bulk_save_objects(menus_luwak)
        db.session.commit()

        # Menús para Pizza Express
        menus_pizzaexpress = [
            Menu(
                restaurante_id=11,
                nombre='Pizza de Jamón y Queso (Mediana)',
                descripcion='Pizza con jamón, queso mozzarella y salsa de tomate',
                precio=5.00,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/pizza jamon.jpeg'
            ),
            Menu(
                restaurante_id=11,
                nombre='Pizza de Pepperoni (Grande)',
                descripcion='Pizza con pepperoni, queso mozzarella y salsa de tomate',
                precio=8.50,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/pizza peperoni.jpeg'
            ),
            Menu(
                restaurante_id=11,
                nombre='Pizza Hawaiana (Pequeña)',
                descripcion='Pizza con jamón, piña, queso y salsa de tomate',
                precio=4.00,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Pizza Hawaiana (Pequeña).jpeg'
            ),
            Menu(
                restaurante_id=11,
                nombre='Pizza de Pollo y Champiñones (Mediana)',
                descripcion='Pizza con pollo, champiñones, queso y salsa de tomate',
                precio=6.50,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Pizza de Pollo y Champiñones (Mediana).jpeg'
            ),
            Menu(
                restaurante_id=11,
                nombre='Pizza Cuatro Estaciones (Grande)',
                descripcion='Pizza con jamón, champiñones, alcachofas y aceitunas',
                precio=9.00,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Pizza Cuatro Estaciones (Grande).jpeg'
            ),
            Menu( 
                restaurante_id=11,
                nombre='Pizza Margarita (Mediana)',
                descripcion='Pizza clásica con tomate, mozzarella y albahaca',
                precio=5.00,
                categoria='Pizzas',
                imagen=copy_image_from_path(menu_image_path, app.config['UPLOAD_FOLDER']) or 'uploads/Pizza Margarita (Mediana).jpeg'
            )
        ]
        db.session.bulk_save_objects(menus_pizzaexpress)
        db.session.commit()

    # Crear usuario administrador por defecto si no existe
    if not Usuario.query.filter_by(email='admin@admin.saboresexpress.com').first():
        admin = Usuario(nombre='Administrador', email='admin@admin.saboresexpress.com', password='admin123')
        db.session.add(admin)
        db.session.commit()




with app.app_context():
    db.create_all()




# Iniciar la aplicación en modo debug
if __name__ == '__main__':
    app.run(debug=True)