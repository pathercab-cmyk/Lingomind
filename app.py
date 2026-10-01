import os
import io
import json
from flask import Flask, render_template, request, jsonify, send_file
from groq import Groq
from gtts import gTTS

# Lectura opcional de archivos para Writing
try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None

app = Flask(__name__)

# Cliente de Groq
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Mapa completo de idiomas para gTTS (Text-to-Speech)
TTS_LANG_MAP = {
    'en': 'en', 'fr': 'fr', 'de': 'de', 'it': 'it', 'pt': 'pt',
    'zh': 'zh-CN', 'ja': 'ja', 'ru': 'ru', 'es': 'es', 'ar': 'ar'
}

# Estructura de exámenes por idioma según el marco universitario (US)
EXAMENES_CONFIG = {
    'en': ['Cambridge (PET, FCE, CAE, CPE)', 'IELTS', 'TOEFL iBT', 'Linguaskill', 'Acreditación US (B1/B2)'],
    'fr': ['DELF (A1-B2)', 'DALF (C1-C2)', 'TCF', 'Acreditación US (B1/B2)'],
    'de': ['Goethe-Zertifikat', 'TestDaF', 'DSH', 'Acreditación US (B1/B2)'],
    'it': ['CELI', 'CILS', 'PLIDA', 'Acreditación US (B1/B2)'],
    'pt': ['CAPLE (PLE)', 'CELPE-Bras', 'Acreditación US (B1/B2)'],
    'zh': ['HSK (Nivel 1 al 6)', 'HSKK (Oral)'],
    'ja': ['JLPT / Noken (N5 al N1)'],
    'ru': ['TORFL / TRKI (A1 a C2)'],
    'es': ['DELE', 'SIELE']
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/examenes/<idioma>')
def obtener_examenes(idioma):
    examenes = EXAMENES_CONFIG.get(idioma, ['Acreditación Oficial Universitaria'])
    return jsonify({"examenes": examenes})


# =======================================================
# 1. CHAT PRINCIPAL (TUTOR ORIGINAL, PROFESOR, PRÁCTICAS ORALES, EXÁMENES)
# =======================================================

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json or {}
    mensaje_usuario = data.get('mensaje', '')
    idioma = data.get('idioma', 'en')
    nivel = data.get('nivel', 'B1')
    modo = data.get('modo', 'tutor_original') 
    # Modos: 'tutor_original', 'profesor', 'practicas_orales', 'examen', 'conversacion'
    profesion = data.get('profesion', 'General')
    tema = data.get('tema', 'General')
    tipo_examen = data.get('tipo_examen', 'Acreditación US')

    if modo == 'tutor_original':
        system_prompt = f"""
Eres Oralis, el TUTOR PERSONAL Y GUÍA ACADÉMICO ORIGINAL de idiomas de la Universidad de Sevilla.
Idioma objetivo: {idioma.upper()}
Nivel MCERL del alumno: {nivel}

Tu rol como Tutor Original:
1. Responde de forma amable, cercana y motivadora en {idioma.upper()} adaptado estrictamente al nivel {nivel}.
2. Evalúa de forma continua el progreso, corrige errores sutilmente y ofrece guía académica clara en español.
3. Propón preguntas de seguimiento para mantener viva la interacción pedagógica.

Responde OBLIGATORIAMENTE en JSON estricto:
{{
  "respuesta": "Tu respuesta fluida en {idioma.upper()}",
  "correccion": "Corrección detallada del mensaje del estudiante en español (o 'Todo correcto')",
  "explicacion": "Explicación pedagógica, gramatical o de uso natural en español",
  "vocabulario": "Palabras clave destacadas con traducción",
  "gramatica": "Sugerencia gramatical o refuerzo del nivel {nivel}"
}}
"""
    elif modo == 'profesor':
        system_prompt = f"""
Eres Oralis, CATEDRÁTICO Y PROFESOR DE IDIOMAS en la Universidad de Sevilla.
Impartes una clase estructurada de {idioma.upper()} (Nivel {nivel}). Tema: {tema}.

Instrucciones:
1. Explica la lección teórica o concepto clave en español de forma académica pero accesible.
2. Da ejemplos en {idioma.upper()} con traducción.
3. Plantea una pequeña pregunta/ejercicio al alumno para comprobar su asimilación.

Responde OBLIGATORIAMENTE en JSON estricto:
{{
  "respuesta": "Explicación magistral del tema en español",
  "correccion": "Análisis de la respuesta previa del alumno o 'Todo correcto'",
  "explicacion": "Ejemplos prácticos en {idioma.upper()} traducidos",
  "vocabulario": "Vocabulario formal/técnico del tema",
  "gramatica": "Regla gramatical central explicada"
}}
"""
    elif modo == 'practicas_orales':
        system_prompt = f"""
Eres Oralis, facilitador de PRÁCTICAS ORALES Y SIMULACIÓN PROFESIONAL en la Universidad de Sevilla.
Rol/Profesión simulada: {profesion.upper()} | Idioma: {idioma.upper()} | Nivel: {nivel}
Situación/Escenario: {tema}

Instrucciones:
1. Actúa 100% en tu papel de {profesion} interactuando con el usuario en {idioma.upper()}.
2. Incluye observaciones pragmáticas en español sobre el registro formal/informal y modismos profesionales.

Responde OBLIGATORIAMENTE en JSON estricto:
{{
  "respuesta": "Intervención en {idioma.upper()} dentro del rol de {profesion}",
  "correccion": "Corrección de vocabulario técnico o expresión en español",
  "explicacion": "Consejo de etiqueta profesional o comunicación efectiva oral",
  "vocabulario": "Términos profesionales específicos utilizados",
  "gramatica": "Estructuras orales habituales en este ámbito"
}}
"""
    elif modo == 'examen':
        system_prompt = f"""
Eres un EXAMINADOR OFICIAL de la Universidad de Sevilla preparando al alumno para el EXAMEN: {tipo_examen}.
Idioma: {idioma.upper()} | Nivel: {nivel}

Instrucciones:
1. Simula una prueba oficial (Speaking/Use of Language) siguiendo las pautas reales del examen {tipo_examen}.
2. Evalúa según los criterios oficiales (Fluidez, Gramática, Léxico, Pronunciación/Acento).

Responde OBLIGATORIAMENTE en JSON estricto:
{{
  "respuesta": "Pregunta o tarea de examen oficial en {idioma.upper()}",
  "correccion": "Feedback estilo examen oficial (puntos perdidos/ganados)",
  "explicacion": "Estrategia o tip para aprobar la prueba de {tipo_examen}",
  "vocabulario": "Léxico avanzado exigido en esta prueba",
  "gramatica": "Estructuras requeridas para obtener máxima nota"
}}
"""
    else: # Conversación Libre
        system_prompt = f"""
Eres Oralis, compañero de conversación de idiomas (Universidad de Sevilla).
Idioma: {idioma.upper()} | Nivel: {nivel}

Responde OBLIGATORIAMENTE en JSON estricto:
{{
  "respuesta": "Respuesta amigable en {idioma.upper()}",
  "correccion": "Corrección puntual en español",
  "explicacion": "Explicación breve de la corrección",
  "vocabulario": "Palabras útiles empleadas",
  "gramatica": "Punto gramatical relevante"
}}
"""

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Mensaje del estudiante: {mensaje_usuario}"}
            ],
            model="qwen/qwen3.8-27b",
            response_format={"type": "json_object"}
        )
        return jsonify(json.loads(chat_completion.choices[0].message.content))
    except Exception as e:
        return jsonify({
            "respuesta": "Listening to you... Let's keep practicing!",
            "correccion": "Se produjo un ajuste temporal en la conexión.",
            "explicacion": str(e),
            "vocabulario": "Practice, Speaking, University",
            "gramatica": "Present Continuous"
        }), 500


# =======================================================
# 2. EVALUACIÓN DE SESIÓN E HISTORIAL COMPLETO
# =======================================================

@app.route('/evaluar_practica', methods=['POST'])
def evaluar_practica():
    data = request.json or {}
    historial = data.get('historial', [])
    idioma = data.get('idioma', 'en')
    nivel = data.get('nivel', 'B1')

    system_prompt = f"""
Eres el Director del Departamento de Evaluación Lingüística de la Universidad de Sevilla.
Analiza la conversación sostenida en {idioma.upper()} (Nivel objetivo {nivel}).

Emite un informe técnico de evaluación en JSON estricto:
{{
  "puntuacion": "Nota numérica de 0 a 10",
  "nivel_demostrado": "A1, A2, B1, B2, C1 o C2 según el MCERL",
  "puntos_fuertes": "Fortalezas mostradas por el alumno",
  "errores_principales": "Desglose de errores recurrentes",
  "consejos_mejora": "Plan de estudio recomendado para la Universidad de Sevilla"
}}
"""
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Historial completo de la sesión: {json.dumps(historial)}"}
            ],
            model="qwen/qwen3.8-27b",
            response_format={"type": "json_object"}
        )
        return jsonify(json.loads(chat_completion.choices[0].message.content))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =======================================================
# 3. CORRECCIÓN DE WRITING (TEXTO Y DOCUMENTOS)
# =======================================================

def extraer_texto_archivo(file):
    filename = file.filename.lower()
    if filename.endswith('.txt'):
        return file.read().decode('utf-8')
    elif filename.endswith('.pdf') and pypdf:
        reader = pypdf.PdfReader(file)
        return "".join([p.extract_text() or "" for p in reader.pages])
    elif filename.endswith('.docx') and docx:
        doc = docx.Document(file)
        return "\n".join([p.text for p in doc.paragraphs])
    return None

@app.route('/corregir_writing', methods=['POST'])
def corregir_writing():
    texto = request.form.get('texto', '')
    idioma = request.form.get('idioma', 'en')
    tipo_correccion = request.form.get('tipo_correccion', 'explicativa')

    if 'archivo' in request.files and request.files['archivo'].filename != '':
        archivo = request.files['archivo']
        texto_extraido = extraer_texto_archivo(archivo)
        if texto_extraido:
            texto = texto_extraido

    if not texto.strip():
        return jsonify({"error": "No se recibió texto ni documento válido."}), 400

    system_prompt = f"""
Eres Corrector Oficial de Ensayos y Redacciones de la Universidad de Sevilla para {idioma.upper()}.
Modo de revisión: {tipo_correccion}.

Responde OBLIGATORIAMENTE en JSON estricto:
{{
  "puntuacion_writing": "Calificación sobre 10",
  "texto_corregido_sugerido": "Redacción pulida y mejorada",
  "desglose_errores": [
    {{
      "error": "Expresión errónea",
      "explicacion": "Motivo gramatical o léxico del error en español",
      "pista": "Sugerencia o pista para corregir"
    }}
  ]
}}
"""
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Redacción enviada: {texto}"}
            ],
            model="qwen/qwen3.8-27b",
            response_format={"type": "json_object"}
        )
        return jsonify(json.loads(chat_completion.choices[0].message.content))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =======================================================
# 4. AUDIO / SINTETIZADOR DE VOZ (TTS)
# =======================================================

@app.route('/tts', methods=['POST'])
def text_to_speech():
    try:
        data = request.json or {}
        texto = data.get('texto', '')
        idioma = data.get('idioma', 'en')
        lang_code = TTS_LANG_MAP.get(idioma, 'en')
        
        tts = gTTS(text=texto, lang=lang_code)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return send_file(fp, mimetype='audio/mpeg')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =======================================================
# 5. ANIMIND (RECOMENDADOR DE ANIME)
# =======================================================

@app.route('/animind')
def animind():
    return render_template('animind.html')

@app.route('/animind/recomendar', methods=['POST'])
def recomendar_anime():
    data = request.json or {}
    mensaje_voz = data.get('mensaje_voz', '')

    system_prompt = """
Eres AniMind, recomendador inteligente de anime.
Responde OBLIGATORIAMENTE en JSON estricto:
{
  "titulo": "Título de la obra",
  "sinopsis_corta": "Resumen conciso",
  "razon_recomendacion": "Por qué encaja con el usuario",
  "plataformas": [
    {
      "nombre": "Plataforma de streaming",
      "audios": ["Audio original", "Doblajes"],
      "subtitulos": ["Subtítulos disponibles"]
    }
  ]
}
"""
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Consulta: {mensaje_voz}"}
            ],
            model="qwen/qwen3.8-27b",
            response_format={"type": "json_object"}
        )
        return jsonify(json.loads(chat_completion.choices[0].message.content))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
