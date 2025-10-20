from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "clave_secreta_para_sesiones"


# --- Conexión a base de datos ---
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


# --- Crear tablas si no existen ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            correo TEXT UNIQUE NOT NULL,
            tipo TEXT CHECK(tipo IN ('usuario', 'admin')) NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS reclamos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_usuario INTEGER NOT NULL,
            asunto TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            fecha TEXT NOT NULL,
            estado TEXT CHECK(estado IN ('pendiente', 'resuelto')) DEFAULT 'pendiente',
            FOREIGN KEY(id_usuario) REFERENCES usuarios(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS respuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_reclamo INTEGER NOT NULL,
            contenido TEXT NOT NULL,
            fecha_respuesta TEXT NOT NULL,
            FOREIGN KEY(id_reclamo) REFERENCES reclamos(id)
        )
    ''')
    conn.commit()
    conn.close()


# --- Página de inicio ---
@app.route('/')
def index():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    usuario = session['usuario_id']
    tipo = session['tipo']

    if tipo == 'admin':
        reclamos = conn.execute('SELECT * FROM reclamos').fetchall()
    else:
        reclamos = conn.execute('SELECT * FROM reclamos WHERE id_usuario = ?', (usuario,)).fetchall()
    conn.close()
    return render_template('index.html', reclamos=reclamos, tipo=tipo)


# --- Registro ---
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        tipo = request.form['tipo']

        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO usuarios (nombre, correo, tipo) VALUES (?, ?, ?)", (nombre, correo, tipo))
            conn.commit()
            flash('Usuario registrado correctamente', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('El correo ya está registrado', 'danger')
        finally:
            conn.close()
    return render_template('registro.html')


# --- Login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM usuarios WHERE correo = ?', (correo,)).fetchone()
        conn.close()
        if user:
            session['usuario_id'] = user['id']
            session['tipo'] = user['tipo']
            session['nombre'] = user['nombre']
            return redirect(url_for('index'))
        else:
            flash('Usuario no encontrado', 'danger')
    return render_template('login.html')


# --- Cerrar sesión ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# --- Nuevo reclamo ---
@app.route('/nuevo_reclamo', methods=['GET', 'POST'])
def nuevo_reclamo():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        asunto = request.form['asunto']
        descripcion = request.form['descripcion']
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        id_usuario = session['usuario_id']

        conn = get_db_connection()
        conn.execute('INSERT INTO reclamos (id_usuario, asunto, descripcion, fecha) VALUES (?, ?, ?, ?)',
                     (id_usuario, asunto, descripcion, fecha))
        conn.commit()
        conn.close()
        flash('Reclamo registrado correctamente', 'success')
        return redirect(url_for('index'))

    return render_template('nuevo_reclamo.html')


# --- Ver detalle de reclamo ---
@app.route('/reclamo/<int:id>')
def reclamo_detalle(id):
    conn = get_db_connection()
    reclamo = conn.execute('SELECT * FROM reclamos WHERE id = ?', (id,)).fetchone()
    respuestas = conn.execute('SELECT * FROM respuestas WHERE id_reclamo = ?', (id,)).fetchall()
    conn.close()
    return render_template('detalle_reclamo.html', reclamo=reclamo, respuestas=respuestas)


# --- Agregar respuesta (solo admin) ---
@app.route('/responder/<int:id>', methods=['POST'])
def responder(id):
    if session['tipo'] != 'admin':
        flash('No tienes permiso para responder', 'danger')
        return redirect(url_for('index'))

    contenido = request.form['contenido']
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    conn.execute('INSERT INTO respuestas (id_reclamo, contenido, fecha_respuesta) VALUES (?, ?, ?)',
                 (id, contenido, fecha))
    conn.execute('UPDATE reclamos SET estado = "resuelto" WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Respuesta agregada y reclamo marcado como resuelto', 'success')
    return redirect(url_for('index'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
