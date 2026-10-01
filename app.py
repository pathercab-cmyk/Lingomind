import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

# Lectura opcional de archivos adjuntos
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

# Estructura en memoria para almacenar sesiones y progreso del estudiante
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
        # Procesamiento Multipart (Archivos en Writing) o JSON estándar
        if request.content_type and 'multipart/form-data' in request.content_type:
            mensaje = request.form.get('mensaje', '')
            idioma = request.form.get('idioma', 'en')
            nivel = request.form.get('nivel', 'B1')
            modo = request.form.get('modo', 'tutor_original')
            profesion = request.form.get('profesion', '')
            profesion_custom = request.form.get('profesion_custom', '')
            tipo_examen = request.form.get('tipo_examen', '')
            tema = request.form.get('tema') or 'Redacción Genérica'
            
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
            profesion_custom = data.get('profesion_custom', '')
            tipo_examen = data.get('tipo_examen', '')
            tema = data.get('tema') or 'Conversación General'

        # Determinar rol o profesión activa
        rol_activo = profesion_custom if (profesion == 'Otro' and profesion_custom) else profesion

        # Lógica de simulación según el modo activo
        if modo == 'practicas_orales':
            respuesta_texto = f"Simulación de Rol ({rol_activo}) en {idioma.upper()} ({nivel}): Entendido tu mensaje en el contexto profesional: '{mensaje}'."
            correccion = "Ajuste de registro profesional aplicado."
        elif modo == 'writing':
            respuesta_texto = f"Revisión de Writing ({idioma.upper()} - {nivel}): Se ha analizado tu texto ({len(mensaje)} caracteres). La estructura general es adecuada."
            correccion = "Sugerencias de mejora gramatical aplicadas."
        elif modo == 'examen':
            respuesta_texto = f"Evaluación para {tipo_examen} ({nivel}): Excelente respuesta. Mantén el uso de conectores avanzados."
            correccion = "Uso correcto de la estructura solicitada."
        else:
            respuesta_texto = f"Respuesta simulada en {idioma.upper()} ({nivel}) [Modo: {modo}]: Entendido tu mensaje: '{mensaje}'."
            correccion = "Ninguna"

        # Simulación de extracción de vocabulario y gramática aprendida
        nuevo_vocabulario = [f"ejemplo_{len(mensaje)} (traducción)"] if len(mensaje) > 3 else []
        nueva_gramatica = [f"Estructura gramatical ({nivel})"] if len(mensaje) > 3 else []

        # --- REGISTRO EN EL CUADERNO DE APRENDIZAJE ---
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
        "en": ["Cambridge B2 First (FCE)", "Cambridge C1 Advanced (CAE)", "Cambridge C2 Proficiency (CPE)", "IELTS Academic/General", "TOEFL iBT", "Linguaskill"],
        "fr": ["DELF B1", "DELF B2", "DALF C1", "DALF C2", "TCF (Test de Connaissance du Français)"],
        "de": ["Goethe-Zertifikat B1", "Goethe-Zertifikat B2", "Goethe-Zertifikat C1", "TestDaF", "ÖSD"],
        "it": ["CELI 2 (B1)", "CELI 3 (B2)", "CILS Uno (B1)", "CILS Due (B2)", "PLIDA"],
        "pt": ["PLE B1 (DEPLE)", "PLE B2 (DIPLE)", "PLE C1 (DAPLE)", "Celpe-Bras"],
        "nl": ["CNaVT (Certificaat Nederlands als Vreemde Taal)", "Inburgeringsexamen"],
        "zh": ["HSK 1 - 2", "HSK 3 - 4", "HSK 5 - 6 (Hanyu Shuiping Kaoshi)"],
        "ja": ["JLPT N5 - N4", "JLPT N3 - N2", "JLPT N1 (Japanese-Language Proficiency Test)"],
        "ru": ["TORFL / TRKI Basic", "TORFL / TRKI Level 1 (B1)", "TORFL / TRKI Level 2 (B2)"],
        "es": ["DELE B1", "DELE B2", "DELE C1", "DELE C2", "SIELE Global"],
        "ar": ["ALPT (Arabic Language Proficiency Test)", "Examen Oficial AL-ARABIYA"]
    }
    return jsonify({"examenes": examenes.get(idioma, ["Certificación Oficial Estándar"])})

@app.route('/api/banco/<nivel>', methods=['GET'])
def obtener_banco(nivel):
    banco_datos = {
        "A1": {
            "gramatica": [
                "Verbo To Be / Ser o Estar (afirmativo, negativo e interrogativo)",
                "Presente Simple: rutinas y hechos generales",
                "Artículos definidos e indefinidos (a/an, the / un, una, el, la)",
                "Pronombres personales de sujeto y adjetivos posesivos",
                "Uso de 'There is / There are' y demostrativos (this, that, these, those)"
            ],
            "vocabulario": [
                "Saludos, despedidas y fórmulas de cortesía cotidianas",
                "Números cardinales (1-100), días de la semana y meses del año",
                "Miembros de la familia y descripción física básica",
                "Objetos de la clase, hogar y ropa fundamental",
                "Nacionalidades, países y profesiones más comunes"
            ],
            "conectores": ["and (y)", "but (pero)", "because (porque)", "or (o)", "so (así que)"],
            "fonetica": [
                "Sonidos vocálicos cortos vs. largos básicos",
                "Entonación ascendente en preguntas cerradas (Yes/No questions)",
                "Pronunciación correcta de la terminación plural -s"
            ]
        },
        "A2": {
            "gramatica": [
                "Pasado Simple (verbos regulares e irregulares clave)",
                "Pasado Continuo para acciones interrumpidas",
                "Comparativos y Superlativos (adj. cortos y largos)",
                "Verbos modales básicos: Can, Could, Must, Should",
                "Futuro con 'Going to' vs. 'Will' para planes e intenciones"
            ],
            "vocabulario": [
                "Medios de transporte, direccionales y orientación en la ciudad",
                "Alimentos, bebidas, pedidos en restaurantes y compras",
                "Vocabulario de viajes, alojamiento y reservas de hotel",
                "Tiempo atmosférico, estaciones y actividades de ocio",
                "Partes del cuerpo humano, síntomas y enfermedades comunes"
            ],
            "conectores": ["also (también)", "however (sin embargo)", "then (entonces)", "besides (además)", "firstly / secondly"],
            "fonetica": [
                "Pronunciación de la terminación regular -ed (/t/, /d/, /ɪd/)",
                "Acentuación léxica de palabras de dos y tres sílabas",
                "Formas débiles en verbos auxiliares"
            ]
        },
        "B1": {
            "gramatica": [
                "Present Perfect Simple vs. Past Simple",
                "Primer y Segundo Condicional (reales e hipotéticas)",
                "Voz Pasiva básica en presente y pasado simple",
                "Estilo Indirecto (Reported Speech) básico",
                "Oraciones relativas especificativas y explicativas"
            ],
            "vocabulario": [
                "Entorno laboral, solicitudes de empleo y tareas",
                "Medios de comunicación, nuevas tecnologías y redes sociales",
                "Medio ambiente, reciclaje y clima",
                "Rasgos de carácter, emociones y relaciones interpersonales",
                "Entretenimiento, eventos culturales y pasatiempos"
            ],
            "conectores": ["although (aunque)", "in order to (para)", "therefore (por lo tanto)", "as a result", "on the other hand"],
            "fonetica": [
                "Uso de la vocal neutra Schwa (/ə/) en sílabas átonas",
                "Ritmo del habla basado en palabras de contenido",
                "Entonación descendente para preguntas abiertas (WH-)"
            ]
        },
        "B2": {
            "gramatica": [
                "Tercer Condicional y Condicionales Mixtos",
                "Tiempos verbales perfectos continuos",
                "Verbos Modales de deducción y especulación pasada",
                "Voz Pasiva avanzada e Impersonal",
                "Estructuras causativas (have/get something done) y Gerundio/Infinitivo"
            ],
            "vocabulario": [
                "Economía, negocios, finanzas personales y consumo",
                "Educación universitaria e investigación académica",
                "Salud mental, bienestar y estilos de vida",
                "Criminalidad, leyes, justicia y debate social",
                "Phrasal Verbs frecuentes de nivel intermedio-alto"
            ],
            "conectores": ["nevertheless (a pesar de ello)", "furthermore (además)", "despite (a pesar de)", "consequently", "in contrast"],
            "fonetica": [
                "Conexión léxica (Connected Speech: Linking, Assimilation)",
                "Contrastes de acento principal y secundario",
                "Diferenciación de pares mínimos consonánticos"
            ]
        },
        "C1": {
            "gramatica": [
                "Inversión Gramatical tras adverbios negativos/restrictivos",
                "Cláusulas de participio activo, pasivo y perfecto",
                "Subjuntivo formal y fórmulas de deseo/insistencia",
                "Estructuras de hendidura (Cleft sentences)",
                "Uso avanzado de determinantes y modificadores enfáticos"
            ],
            "vocabulario": [
                "Jerga científica, tecnológica e innovación bioética",
                "Política internacional, diplomacia y globalización",
                "Arte, literatura, crítica estética y análisis cultural",
                "Vocabulario académico formal de investigación",
                "Modismos avanzados y colocaciones léxicas refinadas"
            ],
            "conectores": ["notwithstanding", "on the grounds that", "albeit", "in light of", "conversely"],
            "fonetica": [
                "Modulación del tono para denotar ironía o cautela",
                "Manejo fluido de la acentuación tonal (Tonic Placement)",
                "Naturalidad en la pronunciación veloz"
            ]
        },
        "C2": {
            "gramatica": [
                "Dominio total de matices estilísticos y registros literarios",
                "Consistencia total en estructuras complejas anidadas",
                "Flexibilidad sintáctica absoluta para la reorganización del discurso",
                "Manejo avanzado de ambigüedad calculada y eufemismos",
                "Estructuras persuasivas complejas para oratoria formal"
            ],
            "vocabulario": [
                "Léxico erudito, terminología especializada y neologismos",
                "Recursos estilísticos, metáforas elaboradas y proverbios",
                "Vocabulario de negociación de alto nivel y retórica",
                "Sinónimos de alta precisión para matices sutiles",
                "Expresiones idiomáticas nativas de alta especificidad"
            ],
            "conectores": ["be that as it may", "by the same token", "insofar as", "to the extent that", "notwithstanding the fact that"],
            "fonetica": [
                "Comprensión y producción natural de diversos acentos dialectales",
                "Gestión magistral del ritmo y pausas dramáticas",
                "Fluidez y entonación de nivel nativo educado"
            ]
        }
    }
    return jsonify(banco_datos.get(nivel, {
        "gramatica": ["Gramática General"],
        "vocabulario": ["Vocabulario General"],
        "conectores": ["Conectores Básicos"],
        "fonetica": ["Guía Fonética"]
    }))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
