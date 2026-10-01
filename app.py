import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

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
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

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
        if request.content_type and 'multipart/form-data' in request.content_type:
            mensaje = request.form.get('mensaje', '')
            idioma = request.form.get('idioma', 'en')
            nivel = request.form.get('nivel', 'B1')
            modo = request.form.get('modo', 'tutor_original')
            profesion = request.form.get('profesion', '')
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
            tipo_examen = data.get('tipo_examen', '')
            tema = data.get('tema') or 'Conversación General'

        if modo == 'writing':
            respuesta_texto = f"Revisión de Writing ({idioma.upper()} - {nivel}): Se ha analizado tu texto ({len(mensaje)} caracteres). La estructura general es adecuada."
            correccion = "Sugerencias de mejora gramatical aplicadas."
        else:
            respuesta_texto = f"Respuesta en {idioma.upper()} ({nivel}) [Modo: {modo}]: {mensaje[:100]}..."
            correccion = "Ninguna"

        nuevo_vocabulario = [f"palabra_{len(mensaje)} (traducción)"] if len(mensaje) > 10 else []
        nueva_gramatica = [f"Estructura avanzada ({nivel})"] if len(mensaje) > 10 else []

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
    # BANCO DE RECURSOS EXTENDIDO POR NIVEL MCERL
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
            "conectores": [
                "and (y)", "but (pero)", "because (porque)", "or (o)", "so (así que)"
            ],
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
                "Verbos modales básicos: Can, Could, Must, Should (habilidad, permiso, consejo)",
                "Futuro con 'Going to' vs. 'Will' para planes e intenciones"
            ],
            "vocabulario": [
                "Medios de transporte, direccionales y orientación en la ciudad",
                "Alimentos, bebidas, pedidos en restaurantes y compras",
                "Vocabulario de viajes, alojamiento y reservas de hotel",
                "Tiempo atmosférico, estaciones y actividades de ocio",
                "Partes del cuerpo humano, síntomas y enfermedades comunes"
            ],
            "conectores": [
                "also (también)", "however (sin embargo)", "then (entonces)", "besides (además)", "firstly / secondly (en primer lugar)"
            ],
            "fonetica": [
                "Pronunciación de la terminación regular -ed (/t/, /d/, /ɪd/)",
                "Acentuación léxica de palabras de dos y tres sílabas",
                "Aproximación a las formas débiles en verbos auxiliares"
            ]
        },
        "B1": {
            "gramatica": [
                "Present Perfect Simple vs. Past Simple (experiencias temporales)",
                "Primer y Segundo Condicional (situaciones reales e hipotéticas)",
                "Voz Pasiva básica en presente y pasado simple",
                "Estilo Indirecto (Reported Speech): cambios de tiempo verbal básico",
                "Oraciones relativas especificativas y explicativas (who, which, where, whose)"
            ],
            "vocabulario": [
                "Entorno laboral, solicitudes de empleo y descripción de tareas",
                "Medios de comunicación, nuevas tecnologías y redes sociales",
                "Medio ambiente, reciclaje, clima y problemas ambientales",
                "Rasgos de carácter, emociones y relaciones interpersonales",
                "Entretenimiento, eventos culturales y pasatiempos"
            ],
            "conectores": [
                "although / even though (aunque)", "in order to (para / con el fin de)", "therefore (por lo tanto)", "as a result (como resultado)", "on the other hand (por otro lado)"
            ],
            "fonetica": [
                "Uso de la vocal neutra Schwa (/ə/) en sílabas átonas",
                "Ritmo del habla basado en palabras de contenido y de función",
                "Entonación descendente para afirmaciones y preguntas abiertas (WH-)"
            ]
        },
        "B2": {
            "gramatica": [
                "Tercer Condicional y Condicionales Mixtos (arrepentimientos e hipótesis pasadas)",
                "Tiempos verbales perfectos continuos (Present/Past Perfect Continuous)",
                "Verbos Modales de deducción y especulación pasada (must have, can't have, might have)",
                "Voz Pasiva avanzada e Impersonal (It is said that..., He is believed to...)",
                "Estructuras causativas (have/get something done) y verbos seguidos de Gerundio/Infinitivo"
            ],
            "vocabulario": [
                "Economía, negocios, finanzas personales y consumo responsable",
                "Educación universitaria, investigación académica y métodos de estudio",
                "Salud mental, bienestar, estilos de vida y medicina moderna",
                "Criminalidad, leyes, justicia y debate social",
                "Expresiones idiomáticas complejas (Phrasal Verbs frecuentes de nivel intermedio-alto)"
            ],
            "conectores": [
                "nevertheless (a pesar de ello)", "futhermore / moreover (además / más aún)", "despite / in spite of (a pesar de)", "consequently (en consecuencia)", "in contrast (en contraste)"
            ],
            "fonetica": [
                "Conexión léxica (Connected Speech: Linking, Assimilation, Elision)",
                "Contrastes de acento principal y secundario en oraciones complejas",
                "Diferenciación precisa entre pares mínimos consonánticos y vocálicos"
            ]
        },
        "C1": {
            "gramatica": [
                "Inversión Gramatical tras adverbios negativos/restrictivos (Seldom, Rarely, Hardly...)",
                "Cláusulas de participio activo, pasivo y perfecto (Having finished..., Built in...)",
                "Subjuntivo formal y fórmulas de deseo/insistencia (I'd rather you didn't..., It is crucial that...)",
                "Estructuras de hendidura (Cleft sentences: What I love about it is..., It was John who...)",
                "Uso avanzado de determinantes, cuantificadores y modificadores enfáticos"
            ],
            "vocabulario": [
                "Jerga científica, tecnológica, innovación y debate bioético",
                "Política internacional, diplomacia, globalización y socioeconomía",
                "Arte, literatura, crítica estética y análisis cultural",
                "Vocabulario académico formal de investigación y redacción de ensayos",
                "Modismos avanzados, Phrasal Verbs matizados y colocaciones léxicas refinadas"
            ],
            "conectores": [
                "notwithstanding (no obstante)", "on the grounds that (bajo el argumento de que)", "albeit (si bien / aunque)", "in light of (a la luz de)", "conversely (por el contrario)"
            ],
            "fonetica": [
                "Modulación del tono y la entonación para denotar ironía, énfasis o cautela",
                "Manejo fluido de la acentuación tonal según el foco de información (Tonic Placement)",
                "Naturalidad en la pronunciación veloz sin pérdida de inteligibilidad"
            ]
        },
        "C2": {
            "gramatica": [
                "Dominio total de matices estilísticos, arcaísmos útiles y registros literarios",
                "Consistencia total en estructuras complejas anidadas y condensadas",
                "Flexibilidad sintáctica absoluta para la reorganización del discurso según intención",
                "Manejo avanzado de ambigüedad calculada, metáforas gramaticales y eufemismos",
                "Estructuras persuasivas complejas de nivel nativo para la oratoria formal"
            ],
            "vocabulario": [
                "Léxico erudito, terminología especializada multidisciplinar y neologismos",
                "Recursos estilísticos, metáforas elaboradas, proverbios y referencias culturales profundas",
                "Vocabulario de negociación de alto nivel, arbitraje y retórica parlamentaria",
                "Sinónimos de alta precisión para matices sutiles de sentido o registro",
                "Expresiones idiomáticas nativas de alta especificidad o raigambre cultural"
            ],
            "conectores": [
                "be that as it may (sea como fuere)", "by the same token (del mismo modo)", "insofar as (en la medida en que)", "to the extent that (hasta el punto de que)", "notwithstanding the fact that (a pesar del hecho de que)"
            ],
            "fonetica": [
                "Comprensión y producción natural de diversos acentos y variedades dialectales",
                "Gestión magistral del ritmo, las pausas dramáticas y los matices afectivos",
                "Fluidez y entonación indistinguible de la de un hablante nativo educado"
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
