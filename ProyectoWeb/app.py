from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from sqlalchemy.exc import IntegrityError
import os

# Para crear el archivo donde se está guardando toda la información en general
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///asesorias.db'
app.config['SECRET_KEY'] = 'tu_clave_secreta'
db = SQLAlchemy(app)
migrate = Migrate(app, db)  # Añadir esta línea
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Modelos
asesoria_alumno = db.Table('asesoria_alumno',
    db.Column('asesoria_id', db.Integer, db.ForeignKey('asesoria.id'), primary_key=True),
    db.Column('alumno_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(10), nullable=False)
    especializacion = db.Column(db.String(200), nullable=True)  # Nueva columna
    foto = db.Column(db.String(200), nullable=True)  # Nueva columna
    edad = db.Column(db.Integer, nullable=True)  # Nueva columna
    nivel = db.Column(db.String(50), nullable=True)  # Nueva columna
    asesorias = db.relationship('Asesoria', secondary=asesoria_alumno, back_populates='alumnos')

class Asesoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(200), nullable=False)
    costo = db.Column(db.Float, nullable=False)
    max_alumnos = db.Column(db.Integer, nullable=False)
    temas = db.Column(db.String(200), nullable=False)
    maestro_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    alumnos = db.relationship('User', secondary=asesoria_alumno, back_populates='asesorias')
    total_pagado = db.Column(db.Float, default=0.0)
    meet_link = db.Column(db.String(200), nullable=True)

class RegistroAsesoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asesoria_id = db.Column(db.Integer, db.ForeignKey('asesoria.id'), nullable=False)
    alumno_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pagado = db.Column(db.Boolean, default=False)

    asesoria = db.relationship('Asesoria', backref=db.backref('registros', lazy=True))
    alumno = db.relationship('User', backref=db.backref('registro_asesorias', lazy=True))

# Rutas
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user is None or user.password != password:
            flash('Credenciales incorrectas.', 'danger')
            return redirect(url_for('login'))
        
        login_user(user)
        if user.rol == 'alumno':
            return redirect(url_for('dashboard_alumno'))
        elif user.rol == 'maestro':
            return redirect(url_for('dashboard_maestro'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/crear_usuario', methods=['GET', 'POST'])
def crear_usuario():
    if request.method == 'POST':
        rol = request.form['rol']
        if rol == 'maestro':
            return redirect(url_for('registro_maestro'))
        else:
            return redirect(url_for('registro_alumno'))
    return render_template('crear_usuario.html')

@app.route('/registro_maestro', methods=['GET', 'POST'])
def registro_maestro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        especializacion = request.form['especializacion']
        foto = request.files['foto']
        edad = request.form['edad']
        nivel = request.form['nivel']
        if password != confirm_password:
            flash('Las contraseñas no coinciden.')
            return redirect(url_for('registro_maestro'))
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('El correo ya está registrado. Usa uno diferente.')
            return redirect(url_for('registro_maestro'))
        
        if foto:
            foto_filename = foto.filename
            foto_path = os.path.join(app.root_path, 'static/profile_pics', foto_filename)
            foto.save(foto_path)
        else:
            foto_filename = None
        
        nuevo_maestro = User(
            nombre=nombre, email=email, password=password, rol='maestro',
            especializacion=especializacion, foto=foto_filename, edad=edad, nivel=nivel
        )
        db.session.add(nuevo_maestro)
        db.session.commit()
        flash('Maestro registrado con éxito.')
        return redirect(url_for('login'))
    return render_template('registro_maestro.html')

@app.route('/registro_alumno', methods=['GET', 'POST'])
def registro_alumno():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Las contraseñas no coinciden.')
            return redirect(url_for('registro_alumno'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('El correo ya está registrado. Usa uno diferente.')
            return redirect(url_for('registro_alumno'))

        nuevo_alumno = User(nombre=nombre, email=email, password=password, rol='alumno')
        db.session.add(nuevo_alumno)
        db.session.commit()
        flash('Alumno registrado con éxito.')
        return redirect(url_for('login'))
    return render_template('registro_alumno.html')

# Ruta para el dashboard del maestro
@app.route('/dashboard_maestro')
@login_required
def dashboard_maestro():
    asesorias = db.session.query(Asesoria).filter_by(maestro_id=current_user.id).all()
    return render_template('dashboard_maestro.html', asesorias=asesorias)

# Ruta para el dashboard del alumno
@app.route('/dashboard_alumno')
@login_required
def dashboard_alumno():
    asesorias = db.session.query(Asesoria, User).join(User, Asesoria.maestro_id == User.id).all()
    return render_template('dashboard_alumno.html', asesorias=asesorias)

# Ruta para ver asesorías totales
@app.route('/ver_asesoria/<int:id>')
@login_required
def ver_asesoria(id):
    asesoria = Asesoria.query.get_or_404(id)
    maestro = User.query.get(asesoria.maestro_id)
    alumnos = asesoria.alumnos
    registrado = request.args.get('registrado', default=False, type=bool)
    return render_template('ver_asesoria.html', asesoria=asesoria, maestro=maestro, alumnos=alumnos, registrado=registrado)


#Ruta para pago de asesoría
@app.route('/validar_registro/<int:id>', methods=['POST'])
@login_required
def validar_registro(id):
    asesoria = Asesoria.query.get_or_404(id)
    if current_user in asesoria.alumnos:
        flash('Ya estás registrado en esta asesoría.', 'danger')
        return redirect(url_for('ver_asesoria', id=asesoria.id, registrado=True))
    
    # Agregar al alumno y actualizar el total pagado
    asesoria.alumnos.append(current_user)
    asesoria.total_pagado += asesoria.costo
    db.session.commit()
    flash('Te has registrado en la asesoría con éxito.', 'success')
    return redirect(url_for('ver_asesoria', id=asesoria.id, pagado=True))

@app.route('/pago_asesoria/<int:id>', methods=['GET', 'POST'])
@login_required
def pago_asesoria(id):
    asesoria = Asesoria.query.get_or_404(id)
    if request.method == 'POST':
        nombre = request.form['nombre']
        tarjeta = request.form['tarjeta']
        vencimiento = request.form['vencimiento']
        cvv = request.form['cvv']
        celular = request.form['celular']

        if not all([nombre, tarjeta, vencimiento, cvv, celular]):
            flash('Todos los campos son obligatorios.', 'danger')
            return redirect(url_for('pago_asesoria', id=asesoria.id))

        # Registrar el pago
        registro = RegistroAsesoria.query.filter_by(asesoria_id=asesoria.id, alumno_id=current_user.id).first()
        if not registro:
            registro = RegistroAsesoria(asesoria_id=asesoria.id, alumno_id=current_user.id, pagado=False)
            db.session.add(registro)

        registro.pagado = True
        asesoria.total_pagado += asesoria.costo

        db.session.commit()
        flash('Pago realizado y te has registrado en la asesoría con éxito.', 'success')

        # Enviar mensaje de WhatsApp
        mensaje = f'Pago realizado en GAD de {asesoria.costo} y los últimos cuatro dígitos de la tarjeta son {tarjeta[-4:]}'
        client.messages.create(
            body=mensaje,
            from_=f'whatsapp:{TWILIO_WHATSAPP_NUMBER}',
            to=f'whatsapp:{celular}'
        )

        return redirect(url_for('ver_asesoria', id=asesoria.id))

    return render_template('pago_asesoria.html', asesoria=asesoria)

@app.route('/procesar_pago/<int:id>', methods=['POST'])
@login_required
def procesar_pago(id):
    asesoria = Asesoria.query.get_or_404(id)
    
    # Registrar todos los datos recibidos en el formulario
    print("Datos recibidos en request.form:")
    for key, value in request.form.items():
        print(f"{key}: {value}")

    nombre = request.form.get('nombre')
    tarjeta = request.form.get('tarjeta')
    vencimiento = request.form.get('vencimiento')
    cvv = request.form.get('cvv')
    celular = request.form.get('celular')

    # Verificar si todos los campos se recibieron
    print(f"Nombre: {nombre}, Tarjeta: {tarjeta}, Vencimiento: {vencimiento}, CVV: {cvv}, Celular: {celular}")

    if not all([nombre, tarjeta, vencimiento, cvv, celular]):
        return redirect(url_for('pago_asesoria', id=asesoria.id))

    # Buscar el registro de la asesoría para este alumno
    registro = RegistroAsesoria.query.filter_by(asesoria_id=asesoria.id, alumno_id=current_user.id).first()
    if not registro:
        registro = RegistroAsesoria(asesoria_id=asesoria.id, alumno_id=current_user.id, pagado=False)
        db.session.add(registro)

    # Lógica del pago (simulada)
    registro.pagado = True

    db.session.commit()
    flash('Pago realizado y te has registrado en la asesoría con éxito.', 'success')
    return redirect(url_for('ver_asesoria', id=asesoria.id))

# Ruta para crear una nueva asesoría
@app.route('/nueva_asesoria', methods=['GET', 'POST'])
@login_required
def nueva_asesoria():
    if request.method == 'POST':
        descripcion = request.form['descripcion']
        costo = request.form['costo']
        max_alumnos = request.form['max_alumnos']
        temas = request.form['temas']
        meet_link = request.form['meet_link']
        nueva_asesoria = Asesoria(
            descripcion=descripcion, costo=costo, max_alumnos=max_alumnos,
            temas=temas, maestro_id=current_user.id, meet_link=meet_link
        )
        db.session.add(nueva_asesoria)
        db.session.commit()
        flash('Asesoría creada con éxito.')
        return redirect(url_for('dashboard_maestro'))
    return render_template('nueva_asesoria.html')


@app.route('/registrar_asesoria/<int:id>', methods=['POST'])
@login_required
def registrar_asesoria(id):
    asesoria = Asesoria.query.get_or_404(id)
    if current_user not in asesoria.alumnos:
        asesoria.alumnos.append(current_user)
        db.session.commit()
        flash('Te has registrado en la asesoría con éxito.')
    else:
        flash('Ya estás registrado en esta asesoría.')
    return redirect(url_for('ver_asesoria', id=asesoria.id))

@app.route('/ver_detalle_asesoria_maestro/<int:id>')
@login_required
def ver_detalle_asesoria_maestro(id):
    asesoria = Asesoria.query.get_or_404(id)
    maestro = User.query.get(asesoria.maestro_id)
    alumnos = asesoria.alumnos
    total_pagado = asesoria.total_pagado
    return render_template('ver_detalle_asesoria_maestro.html', asesoria=asesoria, maestro=maestro, alumnos=alumnos, total_pagado=total_pagado)

# Ruta para ver los detalles de una asesoría
@app.route('/ver_detalle_asesoria/<int:id>')
@login_required
def ver_detalle_asesoria(id):
    asesoria = Asesoria.query.get_or_404(id)
    maestro = User.query.get(asesoria.maestro_id)
    alumnos = asesoria.alumnos
    return render_template('ver_asesoria.html', asesoria=asesoria, maestro=maestro, alumnos=alumnos)

@app.route('/ver_asesorias_totales')
@login_required
def ver_asesorias_totales():
    asesorias = db.session.query(Asesoria, User).join(User, Asesoria.maestro_id == User.id).all()
    return render_template('ver_asesorias_totales.html', asesorias=asesorias)

# Ruta para borrar una asesoría
@app.route('/borrar_asesoria/<int:id>', methods=['POST'])
@login_required
def borrar_asesoria(id):
    asesoria = Asesoria.query.get_or_404(id)
    try:
        # Eliminar registros relacionados de RegistroAsesoria
        RegistroAsesoria.query.filter_by(asesoria_id=asesoria.id).delete()
        # Eliminar la asesoría
        db.session.delete(asesoria)
        db.session.commit()
        flash('Asesoría eliminada con éxito', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Error al eliminar la asesoría. Intenta de nuevo.', 'danger')
    return redirect(url_for('dashboard_maestro'))

# Ruta para editar una asesoría
@app.route('/editar_asesoria/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_asesoria(id):
    asesoria = Asesoria.query.get_or_404(id)
    if asesoria.maestro_id != current_user.id:
        flash('No tienes permiso para editar esta asesoría.')
        return redirect(url_for('ver_asesorias_totales'))

    if request.method == 'POST':
        asesoria.descripcion = request.form['descripcion']
        asesoria.costo = request.form['costo']
        asesoria.max_alumnos = request.form['max_alumnos']
        asesoria.temas = request.form['temas']
        asesoria.meet_link = request.form['meet_link']
        db.session.commit()
        flash('Asesoría actualizada con éxito.')
        return redirect(url_for('ver_detalle_asesoria_maestro', id=asesoria.id))
    return render_template('editar_asesoria.html', asesoria=asesoria)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)

    