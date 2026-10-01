import os
import re
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

# MOTOR DE ANÁLISIS DE ERRORES Y GENERACIÓN DE PISTAS
def analizar_y_corregir_mensaje(mensaje, idioma, metodo_writing="gramatica"):
    msg_low = mensaje.strip().lower()
    correccion = None
    explicacion = None
    texto_subrayado = None
    pista = None

    if idioma == "en":
        if re.search(r'\bi are\b', msg_low):
            correccion = mensaje.replace("i are", "I am").replace("I are", "I am")
            explicacion = "Concordancia de sujeto: Con el pronombre 'I' se debe usar el verbo 'am', no 'are' ('I am great')."
            texto_subrayado = re.sub(r'\b(i are|I are)\b', r'<u class="text-danger fw-bold">\1</u>', mensaje, flags=re.IGNORECASE)
            pista = "Fíjate en el verbo auxiliar después de 'I'. ¿Es 'are' la forma correcta del verbo 'to be' para la primera persona?"

        elif re.search(r'\bhe have\b', msg_low):
            correccion = mensaje.replace("he have", "he has")
            explicacion = "Tercera persona singular: Se debe usar 'has' con 'he/she/it' ('he has')."
            texto_subrayado = re.sub(r'\bhe have\b', r'<u class="text-danger fw-bold">he have</u>', mensaje, flags=re.IGNORECASE)
            pista = "Revisa la conjugación del verbo 'to have' para la tercera persona del singular (he/she/it)."

        elif re.search(r'\bshe have\b', msg_low):
            correccion = mensaje.replace("she have", "she has")
            explicacion = "Tercera persona singular: Se debe usar 'has' con 'he/she/it' ('she has')."
            texto_subrayado = re.sub(r'\bshe have\b', r'<u class="text-danger fw-bold">she have</u>', mensaje, flags=re.IGNORECASE)
            pista = "Recuerda cómo cambia el verbo 'have' al hablar de 'she'."

    elif idioma == "de":
        if "ich bist" in msg_low:
            correccion = mensaje.replace("ich bist", "ich bin")
            explicacion = "Konjugation: Für die erste Person 'ich' verwendet man 'bin' ('ich bin')."
            texto_subrayado = mensaje.replace("ich bist", '<u class="text-danger fw-bold">ich bist</u>')
            pista = "Achte auf die Konjugation von 'sein' mit dem Pronomen 'ich'."

    elif idioma == "ro":
        if "eu ești" in msg_low:
            correccion = mensaje.replace("eu ești", "eu sunt")
            explicacion = "Acordul verbului: Pentru persoana I singular 'eu' se folosește 'sunt'."
            texto_subrayado = mensaje.replace("eu ești", '<u class="text-danger fw-bold">eu ești</u>')
            pista = "Verifică forma verbului 'a fi' pentru prima persoană (eu)."

    elif idioma == "es":
        if "yo eres" in msg_low:
            correccion = mensaje.replace("yo eres", "yo soy")
            explicacion = "Conjugación: Para la primera persona 'yo' se utiliza 'soy'."
            texto_subrayado = mensaje.replace("yo eres", '<u class="text-danger fw-bold">yo eres</u>')
            pista = "Observa el verbo ser conjugado con el pronombre 'yo'."

    return {
        "correccion": correccion,
        "explicacion": explicacion,
        "texto_subrayado": texto_subrayado,
        "pista": pista
    }

def generar_respuesta_natural(idioma, nivel, modo, rol_activo, mensaje, metodo_writing=None, tiene_error=False):
    if modo == "writing":
        if metodo_writing == "pistas":
            if tiene_error:
                return f"[Modo Desafío - {nivel}]: He detectado uno o más errores en tu escrito. Revisa la sección subrayada e intenta corregirlo tú mismo utilizando la pista."
            else:
                return f"[Modo Desafío - {nivel}]: ¡Excelente trabajo! No he encontrado errores gramaticales evidentes en tu texto."
        else:
            if tiene_error:
                return f"[Corrección Directa - {nivel}]: He revisado tu redacción. Abajo encontrarás el análisis detallado con las correcciones necesarias."
            else:
                return f"[Corrección Directa - {nivel}]: Tu redacción está bien construida y cumple con las normas sintácticas de nivel {nivel}."

    respuestas = {
        "de": {
            "saludo": "Hallo! Mir geht es sehr gut, danke der Nachfrage. Wie kann ich dir heute beim Deutschlernen helfen?",
            "conversacion": "Das klingt interessant! Erzähl mir mehr darüber.",
            "practica": f"Guten Tag! Als {rol_activo} helfe ich Ihnen sehr gerne weiter. Was kann ich heute für Sie tun?"
        },
        "ro": {
            "saludo": "Salut! Eu sunt foarte bine, mulțumesc! Cum te pot ajuta astăzi să exersezi limba română?",
            "conversacion": f"Sună foarte interesant! La nivelul {nivel}, este important să exersăm fraze fluide.",
            "practica": f"Bună ziua! În calitate de {rol_activo}, vă stau la dispoziție. Cu ce vă pot ajuta astăzi?"
        },
        "en": {
            "saludo": "Hello! I'm doing great, thank you. How can I help you practice your English today?",
            "conversacion": "That sounds great! Tell me more about that or how your day is going.",
            "practica": f"Hello! As a {rol_activo}, I'm ready to assist you. How can I help you today?"
        },
        "fr": {
            "saludo": "Bonjour ! Je vais très bien, merci. Comment puis-je vous aider à pratiquer le français aujourd'hui ?",
            "conversacion": "C'est très intéressant ! Racontez-moi en un peu plus.",
            "practica": f"Bonjour ! En tant que {rol_activo}, je suis à votre service. Que puis-je faire pour vous ?"
        },
        "es": {
            "saludo": "¡Hola! Estoy muy bien, gracias por preguntar. ¿En qué te gustaría practicar hoy?",
            "conversacion": "¡Qué bien! Cuéntame un poco más sobre eso.",
            "practica": f"¡Buenos días! Como {rol_activo}, estoy aquí para atenderle. ¿En qué puedo ayudarle hoy?"
        }
    }

    idioma_cfg = respuestas.get(idioma, respuestas["en"])
    msg_low = mensaje.lower()

    if "hallo" in msg_low or "wie geht" in msg_low or "hello" in msg_low or "salut" in msg_low or "hola" in msg_low or "bonjour" in msg_low:
        return idioma_cfg["saludo"]
    elif modo == "practicas_orales":
        return idioma_cfg["practica"]
    else:
        return idioma_cfg["conversacion"]

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
            profesion_custom = request.form.get('profesion_custom', '')
            tipo_examen = request.form.get('tipo_examen', '')
            tema = request.form.get('tema') or 'Redacción Genérica'
            metodo_writing = request.form.get('metodo_writing', 'gramatica')
            
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
            metodo_writing = data.get('metodo_writing', 'gramatica')

        rol_activo = profesion_custom if (profesion == 'Otro' and profesion_custom) else profesion

        resultado_analisis = analizar_y_corregir_mensaje(mensaje, idioma, metodo_writing)
        tiene_error = resultado_analisis["correccion"] is not None

        respuesta_texto = generar_respuesta_natural(idioma, nivel, modo, rol_activo, mensaje, metodo_writing, tiene_error)

        nuevo_vocabulario = [f"término_clave ({idioma.upper()})"] if len(mensaje) > 3 else []
        nueva_gramatica = [f"Análisis de redacción ({metodo_writing})"] if modo == 'writing' else [f"Estructura comunicativa ({nivel})"]

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
            "metodo_writing": metodo_writing,
            "correccion": resultado_analisis["correccion"],
            "explicacion": resultado_analisis["explicacion"],
            "texto_subrayado": resultado_analisis["texto_subrayado"],
            "pista": resultado_analisis["pista"],
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
        "ro": ["Examenul de Limba Română ca Limbă Străină (RLS)", "Certificat de Competență Lingvistică - Universitatea din București", "TESTAL Română"],
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
