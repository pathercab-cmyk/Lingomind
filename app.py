import os
import re
import json
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from openai import OpenAI

# Intentar importar librerías para extraer texto de archivos (opcional)
try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None

app = Flask(__name__)

# Configuración para subida de archivos (Modo Writing)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Máximo 16MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configuración del cliente de OpenAI
# Asegúrate de definir la variable de entorno OPENAI_API_KEY en tu sistema
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

NOMBRE_APP = "Oralis"

# Base de datos simulada en memoria para el Cuaderno de Aprendizaje
PERFILES_USUARIO = {
    "historiales": [],
    "vocabulario": {}, # Estructura: {idioma: {tema: [palabras]}}
    "gramatica": {}    # Estructura: {idioma: {nivel: [puntos]}}
}

# --- FUNCIONES AUXILIARES ---

def extraer_texto_archivo(filepath):
    """Extrae texto plano de archivos .txt, .pdf y .docx."""
    ext = filepath.split('.')[-1].lower()
    contenido = ""
    try:
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
            contenido = f"[Archivo {ext.upper()} adjuntado, pero la extracción de texto no está disponible]"
    except Exception as e:
        contenido = f"[Error al extraer texto del archivo: {str(e)}]"
    return contenido.strip()

def analizar_y_corregir_local(mensaje, idioma):
    """
    Motor local básico para detectar errores comunes y generar pistas sintácticas.
    Se usa principalmente para el 'Modo Desafío' en Writing.
    """
    msg_low = mensaje.strip().lower()
    correccion = None
    explicacion = None
    texto_subrayado = None
    pista = None

    if idioma == "en":
        # Ejemplo: I are -> I am
        if re.search(r'\bi are\b', msg_low):
            correccion = mensaje.replace("i are", "I am").replace("I are", "I am")
            explicacion = "Concordancia de sujeto: Con 'I' se usa 'am'."
            texto_subrayado = re.sub(r'\b(i are|I are)\b', r'<u class="text-danger fw-bold">\1</u>', mensaje, flags=re.IGNORECASE)
            pista = "Revisa el verbo 'to be' para la primera persona ('I')."
        # Ejemplo: he have -> he has
        elif re.search(r'\bhe have\b', msg_low):
            correccion = mensaje.replace("he have", "he has")
            explicacion = "Tercera persona singular: Usar 'has' con 'he/she/it'."
            texto_subrayado = re.sub(r'\bhe have\b', r'<u class="text-danger fw-bold">he have</u>', mensaje, flags=re.IGNORECASE)
            pista = "Revisa la conjugación de 'have' para 'he'."

    elif idioma == "de":
        # Ejemplo: ich bist -> ich bin
        if "ich bist" in msg_low:
            correccion = mensaje.replace("ich bist", "ich bin")
            explicacion = "Konjugation: Für 'ich' verwendet man 'bin'."
            texto_subrayado = mensaje.replace("ich bist", '<u class="text-danger fw-bold">ich bist</u>')
            pista = "Achte auf die Konjugation von 'sein' mit 'ich'."

    elif idioma == "es":
        # Ejemplo: yo eres -> yo soy
        if "yo eres" in msg_low:
            correccion = mensaje.replace("yo eres", "yo soy")
            explicacion = "Conjugación: Para 'yo' se usa 'soy'."
            texto_subrayado = mensaje.replace("yo eres", '<u class="text-danger fw-bold">yo eres</u>')
            pista = "Observa el verbo ser para la primera persona."

    return {
        "correccion": correccion,
        "explicacion": explicacion,
        "texto_subrayado": texto_subrayado,
        "pista": pista
    }

# --- RUTAS DE LA APLICACIÓN ---

@app.route('/')
def index():
    """Carga la página principal."""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Maneja los mensajes del chat y las solicitudes a la IA."""
    try:
        # 1. Obtención de datos (soporta multipart/form-data para archivos y JSON)
        if request.content_type and 'multipart/form-data' in request.content_type:
            mensaje_usuario = request.form.get('mensaje', '')
            idioma = request.form.get('idioma', 'en')
            nivel = request.form.get('nivel', 'B1')
            modo = request.form.get('modo', 'tutor_original') # tutor, practicas, examen, writing
            profesion = request.form.get('profesion', '')
            profesion_custom = request.form.get('profesion_custom', '')
            tipo_examen = request.form.get('tipo_examen', '')
            tema = request.form.get('tema') or 'Conversación General'
            metodo_writing = request.form.get('metodo_writing', 'gramatica')
            
            # Manejo de archivo adjunto (exclusivo Modo Writing)
            archivo_adjunto = request.files.get('archivo')
            if archivo_adjunto and archivo_adjunto.filename != '':
                filename = secure_filename(archivo_adjunto.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                archivo_adjunto.save(filepath)
                texto_extraido = extraer_texto_archivo(filepath)
                mensaje_usuario += f"\n\n[Contenido extraído del archivo '{filename}']:\n{texto_extraido}"
        else:
            # Solicitud estándar en JSON
            data = request.json or {}
            mensaje_usuario = data.get('mensaje', '')
            idioma = data.get('idioma', 'en')
            nivel = data.get('nivel', 'B1')
            modo = data.get('modo', 'tutor_original')
            profesion = data.get('profesion', '')
            profesion_custom = data.get('profesion_custom', '')
            tipo_examen = data.get('tipo_examen', '')
            tema = data.get('tema') or 'Conversación General'
            metodo_writing = data.get('metodo_writing', 'gramatica')

        if not mensaje_usuario:
            return jsonify({"status": "error", "mensaje": "Mensaje vacío"}), 400

        # 2. Definición del ROL (System Prompt) para la IA según el Modo
        
        roles_map = {
            "en": "English", "es": "Español", "fr": "Français", "de": "Deutsch",
            "it": "Italiano", "pt": "Português", "ro": "Română", "nl": "Nederlands",
            "zh": "Chino Mandarín", "ja": "Japonés", "ru": "Ruso", "ar": "Árabe"
        }
        idioma_nombre = roles_map.get(idioma, "Inglés")
        rol_practica = profesion_custom if (profesion == 'Otro' and profesion_custom) else profesion

        # LÓGICA DE PROMPTS SEGÚN MODO ACTIVO
        if modo == "tutor_original":
            # Unificación de Tutor (conversación con corrección) y Profesor (explicaciones)
            system_prompt = (
                f"Eres {NOMBRE_APP}, una IA experta en la enseñanza de idiomas. "
                f"Estás ayudando a un estudiante de nivel {nivel} a practicar {idioma_nombre}.\n"
                "COMPORTAMIENTO DUAL (TUTOR Y PROFESOR):\n"
                "1. Si el usuario te habla normalmente, actúa como TUTOR: mantén la conversación en el idioma objetivo, "
                "pero si detectas un error gramatical o de vocabulario importante, corrígelo e inclúyelo brevemente en tu respuesta.\n"
                "2. Si el usuario te pide una explicación, duda o regla gramatical (especialmente si pregunta en español), actúa como PROFESOR: "
                "EXPLICA DETALLADAMENTE LA REGLA EN ESPAÑOL, con ejemplos claros en el idioma objetivo y su traducción.\n"
                "Adapta siempre tu complejidad al nivel {nivel}."
            )
        elif modo == "practicas_orales":
            system_prompt = (
                f"Eres {NOMBRE_APP}, una IA para practicar idiomas. Simula una situación real en {idioma_nombre}. "
                f"Tu rol es: {rol_practica}. El nivel del estudiante es {nivel}. "
                f"Mantén la conversación exclusivamente en {idioma_nombre} y actúa según tu rol. "
                f"Si el estudiante comete errores, no los corrijas explícitamente para no romper la fluidez, "
                f"pero trata de usar la forma correcta en tu respuesta."
            )
        elif modo == "examen":
            system_prompt = (
                f"Eres un examinador oficial estricto para la prueba {tipo_examen} de {idioma_nombre} (Nivel {nivel}). "
                f"Manten la interacción formal y exclusiva en {idioma_nombre}. Plantea preguntas típicas del examen, "
                f"evalúa las respuestas brevemente si el formato lo requiere, y pasa a la siguiente tarea. No des explicaciones pedagógicas largas."
            )
        elif modo == "writing":
            system_prompt = (
                f"Eres {NOMBRE_APP}, un editor lingüístico avanzado enfocado en la enseñanza. "
                f"Vas a evaluar un texto escrito por un estudiante en {idioma_nombre} (Nivel {nivel}).\n"
                "INSTRUCCIONES DE RESPUESTA:\n"
                "No respondas conversacionalmente. Analiza el texto proporcionado y devuelve SIEMPRE una respuesta estructurada en formato JSON válido con las siguientes claves:\n"
                "- 'analisis': Un comentario general breve en español sobre la calidad del texto (coherencia, cohesión, vocabulario) para el nivel {nivel}.\n"
                "- 'errores': Una lista de objetos, donde cada objeto tiene: {'error': 'texto_original_erroneo', 'correccion': 'texto_corregido', 'explicacion': 'Breve explicación pedagógica en ESPAÑOL de la regla violada'}.\n"
                "Si no hay errores, la lista 'errores' debe estar vacía."
            )
        else:
            # Fallback
            system_prompt = f"Eres {NOMBRE_APP}, un asistente pedagógico para aprender {idioma_nombre} en nivel {nivel}."

        # 3. Llamada a la API de OpenAI (para Modos Estándar o análisis avanzado en Writing)
        # Nota: En un entorno de producción real, el Modo Writing método 'pistas' podría requerir lógica local o prompts específicos para no dar la solución.
        
        try:
            # Para Writing, pedimos respuesta en formato JSON
            api_format = {"type": "json_object"} if modo == "writing" else None
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": mensaje_usuario}
                ],
                response_format=api_format,
                temperature=0.7
            )
            
            api_response_content = response.choices[0].message.content
            
        except Exception as e:
            return jsonify({"status": "error", "mensaje": f"Error API OpenAI: {str(e)}"}), 500

        # 4. Procesamiento de la respuesta y Lógica de Corrección local

        # Inicializar variables de respuesta para el frontend
        respuesta_final_texto = ""
        correccion_directa = None
        explicacion_gramatical = None
        texto_subrayado_error = None
        pista_inductiva = None
        extradata = {} # Para datos específicos de Writing JSON

        if modo == "writing":
            # Procesar respuesta JSON de la API
            try:
                writing_data = json.loads(api_response_content)
                extradata = writing_data
                respuesta_final_texto = f"Análisis para nivel {nivel}: {writing_data.get('analisis', '')}"
                
                num_errores = len(writing_data.get('errores', []))
                
                # Integración de la lógica solicitada para Writing (Método Directo vs Pistas)
                if metodo_writing == "pistas":
                    if num_errores > 0:
                        # Modo Desafío: Tomamos el primer error para ejemplificar en la interfaz con pistas
                        # Nota: En producción, se necesitaría una lógica más compleja para iterar o usar análisis local.
                        # Usaremos el análisis local para 'pistas' para asegurar que NO damos la solución.
                        analisis_local = analizar_y_corregir_local(mensaje_usuario, idioma)
                        if analisis_local["pista"]:
                            respuesta_final_texto = f"He revisado tu escrito ({nivel}). He detectado errores. Te propongo un desafío: intenta corregir la zona subrayada tú mismo usando la pista."
                            texto_subrayado_error = analisis_local["texto_subrayado"]
                            pista_inductiva = analisis_local["pista"]
                        else:
                            respuesta_final_texto = f"He revisado tu escrito ({nivel}). He detectado {num_errores} errores, pero mi motor local no ha podido generar un desafío inductivo específico para el primer error. Revisa el análisis general."
                    else:
                        respuesta_final_texto = f"¡Excelente! He revisado tu escrito para el nivel {nivel} y no he encontrado errores gramaticales evidentes. ¡Buen trabajo!"
                else:
                    # Método 1: Corrección Directa (usamos los datos de la API JSON)
                    if num_errores > 0:
                        respuesta_final_texto = f"He analizado tu redacción ({nivel}). Se han detectado {num_errores} errores. A continuación tienes el detalle del primero y la corrección directa."
                        # Mostramos el primer error como principal en los recuadros de la interfaz
                        primer_error = writing_data['errores'][0]
                        correccion_directa = primer_error.get('correccion')
                        explicacion_gramatical = primer_error.get('explicacion')
                    else:
                        respuesta_final_texto = f"Tu redacción cumple satisfactoriamente con los requisitos sintácticos del nivel {nivel}. No se han detectado errores."

            except json.JSONDecodeError:
                respuesta_final_texto = "[Error en el formato de respuesta de la IA en Modo Writing. Se esperaba JSON]"

        else:
            # Modos Estándar (Tutor, Prácticas, Examen): Detección directa de errores local
            respuesta_final_texto = api_response_content
            
            # En modos estándar, siempre intentamos dar corrección directa si hay error evidente (lógica local)
            analisis_local = analizar_y_corregir_local(mensaje_usuario, idioma)
            if analisis_local["correccion"]:
                correccion_directa = analisis_local["correccion"]
                explicacion_gramatical = analisis_local["explicacion"]

        # 5. Actualización de Recursos Aprendidos (Cuaderno)
        # Lógica simulada: extraemos palabras clave si el mensaje es corto, o puntos gramaticales si hay corrección
        nuevo_vocabulario = []
        nueva_gramatica = []
        
        if len(mensaje_usuario) > 3 and len(mensaje_usuario) < 30:
            # Simulamos que palabras de mensajes cortos son vocabulario nuevo para el tema
            palabras = [p for p in mensaje_usuario.split() if len(p) > 4]
            if palabras:
                nuevo_vocabulario = [f"{palabras[0].capitalize()} ({idioma.upper()})"]

        if correccion_directa:
            # Si hubo corrección, simulamos que aprendió un punto gramatical de ese nivel
            puntos_gramatica_simulados = {
                "A1": "Presente Simple (to be)", "A2": "Pasado Simple", 
                "B1": "Present Perfect", "B2": "Condicionales", 
                "C1": "Voz Pasiva", "C2": "Matices Estilísticos"
            }
            nueva_gramatica = [f"{puntos_gramatica_simulados.get(nivel, 'Gramática')} ({nivel})"]

        # Actualizar la 'base de datos' en memoria
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

        # 6. Respuesta final al Frontend
        return jsonify({
            "status": "success",
            "respuesta": respuesta_final_texto,
            "modo": modo,
            "metodo_writing": metodo_writing,
            "correccion": correccion_directa,
            "explicacion": explicacion_gramatical,
            "texto_subrayado": texto_subrayado_error,
            "pista": pista_inductiva,
            "vocabulario": ", ".join(nuevo_vocabulario) if nuevo_vocabulario else None,
            "writing_full_data": extradata # Datos completos para uso avanzado si se desea
        })

    except Exception as e:
        return jsonify({"status": "error", "mensaje": f"Error general servidor: {str(e)}"}), 500

@app.route('/api/guardar_sesion', methods=['POST'])
def guardar_sesion():
    """Guarda una sesión de chat en el historial."""
    data = request.json or {}
    PERFILES_USUARIO["historiales"].append(data)
    return jsonify({"status": "ok", "total_guardados": len(PERFILES_USUARIO["historiales"])})

@app.route('/api/obtener_recursos_aprendidos/<idioma>', methods=['GET'])
def obtener_recursos(idioma):
    """Devuelve el vocabulario y gramática aprendidos para un idioma."""
    vocab = PERFILES_USUARIO["vocabulario"].get(idioma, {})
    gram = PERFILES_USUARIO["gramatica"].get(idioma, {})
    return jsonify({"vocabulario": vocab, "gramatica": gram})

@app.route('/api/examenes/<idioma>', methods=['GET'])
def obtener_examenes(idioma):
    """Devuelve la lista de exámenes oficiales para un idioma."""
    examenes_banco = {
        "en": ["Cambridge (FCE/CAE/CPE)", "IELTS", "TOEFL", "Linguaskill"],
        "fr": ["DELF/DALF", "TCF"],
        "de": ["Goethe-Zertifikat", "TestDaF"],
        "ro": ["RLS (Limba Română)", "Certificat Universitatea București"],
        "es": ["DELE", "SIELE"]
    }
    return jsonify({"examenes": examenes_banco.get(idioma, ["Certificación Estándar"])})

@app.route('/api/banco/<nivel>', methods=['GET'])
def obtener_banco(nivel):
    """Devuelve recursos genéricos del Banco de Recursos para un nivel."""
    # Banco de datos estático simulado
    banco_datos = {
        "B1": {
            "gramatica": ["Present Perfect", "First Conditional", "Passive Voice (basic)", "Modal Verbs (obligation)"],
            "vocabulario": ["Work & Jobs", "Travel & Transport", "Environment", "Technology"],
            "conectores": ["However", "Although", "Therefore", "In order to"],
            "fonetica": ["Schwa sound /ə/", "Past tense -ed endings", "Word stress patterns"]
        },
        "B2": {
            "gramatica": ["Narrative Tenses", "Second/Third Conditionals", "Passive Voice (advanced)", "Relative Clauses"],
            "vocabulario": ["Crime & Punishment", "Media & Society", "Health & Fitness", "Business basics"],
            "conectores": ["Nevertheless", "Furthermore", "Despite / In spite of", "Consequently"],
            "fonetica": ["Intonation in questions", "Connected speech (linking)", "Contrastive stress"]
        }
    }
    # Fallback para niveles no definidos en el banco simulado
    default_banco = {
        "gramatica": [f"Gramática {nivel}"], "vocabulario": [f"Vocabulario {nivel}"],
        "conectores": ["Basic Connectors"], "fonetica": ["Pronunciation Guide"]
    }
    return jsonify(banco_datos.get(nivel, default_banco))

if __name__ == '__main__':
    # Creación de carpeta uploads si no existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # Ejecución de la app en puerto 5000
    app.run(debug=True, port=5000)
