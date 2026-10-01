import os
import json
from flask import Flask, render_template, request, jsonify, Response, stream_with_context, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from groq import Groq
import PyPDF2
import docx

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave_secreta_oralis_2026')

# --- AQUÍ VA EL CÓDIGO DE POSTGRESQL ---
db_url = os.environ.get('DATABASE_URL', 'sqlite:///oralis.db')

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+psycopg2://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- INICIALIZACIÓN DE LA BASE DE DATOS Y EXTENSIONES ---
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS DE BASE DE DATOS ---

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    idioma = db.Column(db.String(10), default='en')
    nivel = db.Column(db.String(10), default='B1')
    comentarios = db.relationship('Comentario', backref='usuario', lazy=True)

class Comentario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    puntuacion = db.Column(db.Integer, nullable=False)
    texto = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, server_default=db.func.now())

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Configuración del cliente oficial de Groq
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODELO_GROQ = "qwen-2.5-32b"

EXAMENES_OFICIALES = {
    "en": ["Cambridge (PET, FCE, CAE)", "IELTS", "TOEFL", "TOEIC"],
    "fr": ["DELF / DALF", "TCF", "TEF"],
    "de": ["Goethe-Zertifikat", "TestDaF", "DSH"],
    "ro": ["RLA - Romanian Language Assessment"],
    "it": ["CELI", "CILS", "PLIDA"],
    "pt": ["CAPLE", "CELPE-Bras"],
    "nl": ["CNaVT", "Inburgeringsexamen"],
    "zh": ["HSK (Hanyu Shuiping Kaoshi)"],
    "ja": ["JLPT (N5 - N1)"],
    "ru": ["TORFL / TRKI"],
    "es": ["DELE", "SIELE"],
    "ar": ["ALPT"]
}

def extraer_texto_archivo(file):
    filename = file.filename.lower()
    texto = ""
    try:
        if filename.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    texto += t + "\n"
        elif filename.endswith('.docx'):
            doc = docx.Document(file)
            for p in doc.paragraphs:
                if p.text:
                    texto += p.text + "\n"
        elif filename.endswith('.txt'):
            texto = file.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error procesando archivo: {e}")
    return texto.strip()

def construir_prompt_sistema(idioma, nivel, modo, profesion, profesion_custom, tipo_examen, tema, metodo_writing):
    prof_final = profesion_custom if profesion == "Otro" else profesion

    prompt_base = f"""Eres Oralis, una plataforma de inteligencia artificial especializada en la enseñanza de idiomas.
Estás interactuando con un estudiante que aprende el idioma '{idioma}' en nivel '{nivel}'.
Tema o contexto general: {tema}.

Instrucciones generales:
1. Responde siempre de forma pedagógica y adaptable.
2. Tu respuesta principal debe ser en el idioma objetivo ({idioma}).
3. Si el usuario pide explicaciones gramaticales, responde en español con ejemplos prácticos.
4. FORMATO OBLIGATORIO: Texto plano limpio usando saltos de línea normales y viñetas simples con guiones (-). No uses Markdown (**,#,_).
"""
    if modo == "practicas_orales":
        prompt_base += f"\nModo ACTIVO: Simulación de Rol ({prof_final})."
    elif modo == "examen":
        prompt_base += f"\nModo ACTIVO: Preparación Examen Oficial ({tipo_examen})."

    return prompt_base

# --- RUTAS DE AUTENTICACIÓN ---

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if Usuario.query.filter_by(email=email).first():
            flash('El correo ya está registrado.', 'error')
            return render_template('registro.html')

        pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        nuevo_usuario = Usuario(email=email, password_hash=pw_hash)
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        login_user(nuevo_usuario)
        return redirect(url_for('index'))
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and bcrypt.check_password_hash(usuario.password_hash, password):
            login_user(usuario)
            return redirect(url_for('index'))
        else:
            flash('Credenciales incorrectas.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- RUTAS PRINCIPALES ---

@app.route('/')
@login_required
def index():
    return render_template('index.html', usuario=current_user)

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    mensaje_usuario = request.form.get('mensaje', '')
    idioma = request.form.get('idioma', current_user.idioma)
    nivel = request.form.get('nivel', current_user.nivel)
    modo = request.form.get('modo', 'tutor_original')
    profesion = request.form.get('profesion', '')
    profesion_custom = request.form.get('profesion_custom', '')
    tipo_examen = request.form.get('tipo_examen', '')
    tema = request.form.get('tema', '')
    metodo_writing = request.form.get('metodo_writing', 'gramatica')

    texto_archivo = ""
    if 'archivo' in request.files:
        file = request.files['archivo']
        if file and file.filename != '':
            texto_archivo = extraer_texto_archivo(file)

    contenido_completo = mensaje_usuario
    if texto_archivo:
        contenido_completo += f"\n\n[Archivo adjunto]:\n{texto_archivo}"

    system_prompt = construir_prompt_sistema(
        idioma, nivel, modo, profesion, profesion_custom, tipo_examen, tema, metodo_writing
    )

    def generate():
        try:
            completion = client.chat.completions.create(
                model=MODELO_GROQ,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": contenido_completo}
                ],
                temperature=0.6,
                max_completion_tokens=2048,
                top_p=0.95,
                stream=True
            )

            for chunk in completion:
                content = chunk.choices[0].delta.content
                if content:
                    yield f"data: {json.dumps({'content': content})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/feedback', methods=['POST'])
@login_required
def guardar_feedback():
    puntuacion = request.form.get('puntuacion', type=int)
    texto = request.form.get('comentario', '').strip()

    if not puntuacion or not texto:
        return jsonify({"status": "error", "mensaje": "Completa todos los campos."}), 400

    nuevo_comentario = Comentario(user_id=current_user.id, puntuacion=puntuacion, texto=texto)
    db.session.add(nuevo_comentario)
    db.session.commit()

    return jsonify({"status": "ok", "mensaje": "¡Gracias por tu comentario!"})

@app.route('/api/examenes/<idioma>', methods=['GET'])
def obtener_examenes(idioma):
    lista = EXAMENES_OFICIALES.get(idioma.lower(), ["Examen Estándar"])
    return jsonify({"examenes": lista})

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
