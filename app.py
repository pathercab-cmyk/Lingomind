import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

# Opcional para lectura de documentos (si no están instaladas las librerías, lee archivos .txt normalmente)
try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Máximo 16MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

PERFILES_USUARIO = {
    "historiales": [],
    "vocabulario": {},
    "gramatica": {}
}

def extraer_texto_archivo(filepath):
    ext = filepath.split('.')[-1].lower()
    contenido = ""
    if ext == 'txt':
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            contenido = f.read()
    elif ext == 'pdf' and pypdf:
        reader = pypdf.PdfReader(filepath)
        for page in reader.pages:
            contenido += page.extract_text() or ""
    elif ext == 'docx' and docx:
        doc = docx.Document(filepath)
        contenido = "\n".join([p.text for p in doc.paragraphs])
    else:
        contenido = f"[Archivo {ext.upper()} adjuntado correctamente]"
    return contenido.strip()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        # Soporte para envio multipart (archivos) o json
        if request.content_type and 'multipart/form-data' in request.content_type:
            mensaje = request.form.get('mensaje', '')
            idioma = request.form.get('idioma', 'en')
            nivel = request.form.get('nivel', 'B1')
            modo = request.form.get('modo', 'tutor_original')
            profesion = request.form.get('profesion', '')
            tipo_examen = request.form.get('tipo_examen', '')
            tema = request.form.get('tema') or 'Redacción Generica'
            
            archivo_adjunto = request.files.get('archivo')
            texto_extraido = ""
            if archivo_adjunto and archivo_adjunto.filename != '':
                filename = secure_filename(archivo_adjunto.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                archivo_adjunto.save(filepath)
                texto_extraido = extraer_texto_archivo(filepath)
                mensaje += f"\n\n[Contenido del archivo '{filename}']:\n{texto_extraido}"

        else:
            data = request.json or {}
            mensaje = data.get('mensaje', '')
            idioma = data.get('idioma', 'en')
            nivel = data.get('nivel', 'B1')
            modo = data.get('modo', 'tutor_original')
            profesion = data.get('profesion', '')
            tipo_examen = data.get('tipo_examen', '')
            tema = data.get('tema') or 'Conversación General'

        # --- RESPUESTA Y CORRECCIÓN (INTEGRACIÓN IA) ---
        if modo == 'writing':
            respuesta_texto = f"Revisión de Writing ({idioma.upper()} - {nivel}): Se ha analizado tu texto ({len(mensaje)} caracteres). La estructura general es adecuada."
            correccion = "Sugerencias de mejora gramatical aplicadas."
        else:
            respuesta_texto = f"Respuesta en {idioma.upper()} ({nivel}) [Modo: {modo}]: {mensaje[:100]}..."
            correccion = "Ninguna"

        nuevo_vocabulario = [f"palabra_{len(mensaje)} (traducción)"] if len(mensaje) > 10 else []
        nueva_gramatica = [f"Estructura avanzada ({nivel})"] if len(mensaje) > 10 else []

        # Registro en perfil
        if idioma not in PERFILES_USUARIO["vocabulario"]:
            PERFILES_USUARIO["vocabulario"][idioma] = {}
        if tema not in PERFILES_USUARIO["vocabulario"][idioma]:
            PERFILES_USUARIO["vocabulario"][idioma][tema] = []

        for word in nuevo_vocabulario:
            if word not in PERFILES_USUARIO["vocabulario"][idioma][tema]:
                PERFILES_USUARIO["vocabulario"][idioma][tema].append(word)

        if idioma not in PERFILES_USUARIO["gramatica"]:
            PERFILES_USUARIO["gramatica"][idioma] = {}
        if nivel not in PERFILES_USUARIO["gramatica"][idioma]:
            PERFILES_USUARIO["gramatica"][idioma][nivel] = []

        for gram in nueva_gramatica:
            if gram not in PERFILES_USUARIO["gramatica"][idioma][nivel]:
                PERFILES_USUARIO["gramatica"][idioma][nivel].append(gram)

        return jsonify({
            "status": "success",
            "respuesta": respuesta_texto,
            "correccion": correccion,
            "vocabulario": ", ".join(nuevo_vocabulario) if nuevo_vocabulario else None
        })

    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route('/api/guardar_sesion', methods=['POST'])
def guardar_sesion():
    data = request.json or {}
    PERFILES_USUARIO["historiales"].append(data)
    return jsonify({"status": "ok", "total": len(PERFILES_USUARIO["historiales"])})

@app.route('/api/obtener_recursos_aprendidos/<idioma>', methods=['GET'])
def obtener_recursos(idioma):
    vocab = PERFILES_USUARIO["vocabulario"].get(idioma, {})
    gram = PERFILES_USUARIO["gramatica"].get(idioma, {})
    return jsonify({"vocabulario": vocab, "gramatica": gram})

@app.route('/api/examenes/<idioma>', methods=['GET'])
def obtener_examenes(idioma):
    examenes = {
        "en": ["Cambridge B2 First (FCE)", "Cambridge C1 Advanced (CAE)", "Cambridge C2 Proficiency (CPE)", "IELTS Academic/General", "TOEFL iBT"],
        "fr": ["DELF B1", "DELF B2", "DALF C1", "DALF C2"],
        "de": ["Goethe-Zertifikat B1", "Goethe-Zertifikat B2", "TestDaF"],
        "it": ["CELI 2 (B1)", "CELI 3 (B2)", "CILS Uno (B1)", "CILS Due (B2)"],
        "pt": ["PLE B1 (DEPLE)", "PLE B2 (DIPLE)", "Celpe-Bras"],
        "es": ["DELE B1", "DELE B2", "DELE C1", "SIELE Global"]
    }
    return jsonify({"examenes": examenes.get(idioma, ["Certificación Oficial Estándar"])})

@app.route('/api/banco/<nivel>', methods=['GET'])
def obtener_banco(nivel):
    banco_datos = {
        "A1": {"gramatica": ["Verbo To Be", "Presente Simple"], "vocabulario": ["Saludos", "Números"]},
        "A2": {"gramatica": ["Pasado Simple", "Verbos Modales"], "vocabulario": ["Viajes", "Comida"]},
        "B1": {"gramatica": ["Present Perfect", "Condicionales"], "vocabulario": ["Trabajo", "Tecnología"]},
        "B2": {"gramatica": ["Reported Speech", "Passive Voice"], "vocabulario": ["Medio Ambiente", "Educación"]},
        "C1": {"gramatica": ["Inversión Gramatical", "Subjuntivo"], "vocabulario": ["Vocabulario Académico", "Finanzas"]},
        "C2": {"gramatica": ["Estructuras Literarias"], "vocabulario": ["Debate Filosófico", "Modismos"]}
    }
    return jsonify(banco_datos.get(nivel, {"gramatica": ["Gramática Básica"], "vocabulario": ["Vocabulario General"]}))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
