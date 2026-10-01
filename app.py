import os
import io
import json
from flask import Flask, render_template, request, jsonify, send_file
from groq import Groq
from gtts import gTTS

# Librerías opcionales para lectura de archivos
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

TTS_LANG_MAP = {
    'en': 'en', 'de': 'de', 'fr': 'fr', 'it': 'it',
    'pt': 'pt', 'zh': 'zh-CN', 'ja': 'ja', 'ru': 'ru', 'es': 'es'
}

@app.route('/')
def index():
    return render_template('index.html')

# =======================================================
# 1. CHAT UNIFICADO (PROFESOR, TUTOR/ROLES Y PRÁCTICA)
# =======================================================

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json or {}
    mensaje_usuario = data.get('mensaje', '')
    idioma = data.get('idioma', 'en')
    nivel = data.get('nivel', 'B1')
    modo = data.get('modo', 'conversacion') # 'profesor', 'tutor', 'conversacion', 'examen'
    profesion = data.get('profesion', 'Profesor de Idiomas')
    tema = data.get('tema', 'General')
    tipo_examen = data.get('tipo_examen', '')

    if modo == 'profesor':
        system_prompt = f"""
Eres Oralis, PROFESOR DE IDIOMAS de la Universidad de Sevilla.
Estás impartiendo una lección estructurada de {idioma.upper()} (Nivel {nivel}).
Tema actual: {tema}

Instrucciones pedagógicas:
1. Explica el concepto de forma clara en español.
2. Aporta ejemplos claros en {idioma.upper()} con traducción.
3. Propón un ejercicio práctico corto para verificar comprensión.

Responde OBLIGATORIAMENTE en JSON estricto:
{{
  "respuesta": "Explicación clara del tema en español",
  "correccion": "Todo correcto",
  "explicacion": "Ejemplos en {idioma.upper()} con traducción",
  "vocabulario": "Vocabulario clave enseñado",
  "gramatica": "Ejercicio propuesto para el alumno"
}}
"""
    elif modo == 'tutor':
        system_prompt = f"""
Eres Oralis, desempeñando el rol profesional de: {profesion.upper()} en {idioma.upper()} (Nivel {nivel}).
Escenario: {tema}

Instrucciones:
1. Habla en {idioma.upper()} adaptado a nivel {nivel} en tu papel de {profesion}.
2. Añade un consejo en español sobre cómo desenvolverse en esta situación profesional.

Responde OBLIGATORIAMENTE en JSON estricto:
{{
  "respuesta": "Frase de {profesion} en {idioma.upper()}",
  "correccion": "Consejo de actuación o corrección en español",
  "explicacion": "Explicación del vocabulario situacional",
  "vocabulario": "3 términos clave de esta profesión",
  "gramatica": "Estructura formal/útil para este contexto"
}}
"""
    else:
        # Modo Conversación Libre o Examen (Estructura Original intacta)
        system_prompt = f"""
Eres Oralis, un tutor de idiomas de la Universidad de Sevilla.
Idioma actual de práctica: {idioma.upper()}
Nivel MCERL del estudiante: {nivel}
Modo actual: {modo.upper()}{f' (Examen: {tipo_examen})' if modo == 'examen' else ''}

Debes responder OBLIGATORIAMENTE en formato JSON estricto sin bloques de markdown:
{{
  "respuesta": "Tu respuesta en el idioma objetivo ({idioma.upper()}) adaptada al nivel {nivel}",
  "correccion": "Corrección puntual del mensaje del usuario (en español) si cometió errores, o 'Todo correcto'",
  "explicacion": "Explicación clara en español de la corrección o consejos pedagógicos",
  "vocabulario": "Contexto: palabra1, palabra2 (vocabulario clave usado en tu respuesta)",
  "gramatica": "Tema: Regla o estructura gramatical relevante destacada"
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
            "respuesta": "I received your message! Let's continue practicing.",
            "correccion": "Ocurrió un detalle al procesar la evaluación.",
            "explicacion": str(e),
            "vocabulario": "General: practice, conversation",
            "gramatica": "General: Present Continuous"
        }), 500


# =======================================================
# 2. EVALUACIÓN Y INFORME DE PRÁCTICA (Historial)
# =======================================================

@app.route('/evaluar_practica', methods=['POST'])
def evaluar_practica():
    data = request.json or {}
    historial = data.get('historial', [])
    idioma = data.get('idioma', 'en')
    nivel = data.get('nivel', 'B1')

    system_prompt = f"""
Eres un evaluador lingüístico experto de la Universidad de Sevilla.
Analiza el siguiente historial de conversación en {idioma.upper()} (Nivel objetivo: {nivel}).

Genera un informe pedagógico con formato JSON estricto:
{{
  "puntuacion": "Puntuación de 0 a 10",
  "nivel_demostrado": "A1, A2, B1, B2, C1 o C2",
  "puntos_fuertes": "Aspectos destacados de la conversación",
  "errores_principales": "Errores de gramática o vocabulario cometidos",
  "consejos_mejora": "Recomendaciones prácticas para avanzar"
}}
"""
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Historial de conversación: {json.dumps(historial)}"}
            ],
            model="qwen/qwen3.8-27b",
            response_format={"type": "json_object"}
        )
        return jsonify(json.loads(chat_completion.choices[0].message.content))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =======================================================
# 3. CORRECCIÓN DE WRITING (Texto y Archivos)
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
        return jsonify({"error": "No se recibió texto ni archivo válido."}), 400

    system_prompt = f"""
Eres un profesor corrector de redacciones (Writing) de la Universidad de Sevilla para {idioma.upper()}.
Modo de corrección: {tipo_correccion} (explicativa = palabra por palabra, senalar = señalar tipo de error, descubrimiento = dar pistas pedagógicas sin revelar todo).

Responde OBLIGATORIAMENTE en formato JSON estricto:
{{
  "puntuacion_writing": "Nota de 0 a 10",
  "texto_corregido_sugerido": "Propuesta de versión corregida",
  "desglose_errores": [
    {{
      "error": "Palabra/frase con error",
      "explicacion": "Explicación en español del fallo",
      "pista": "Pista para que el alumno lo descubra solo"
    }}
  ]
}}
"""
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Texto de redacción: {texto}"}
            ],
            model="qwen/qwen3.8-27b",
            response_format={"type": "json_object"}
        )
        return jsonify(json.loads(chat_completion.choices[0].message.content))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =======================================================
# 4. SINTETIZADOR DE VOZ (TTS)
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
# 5. RUTAS DE ANIMIND (Recomendador de Anime)
# =======================================================

@app.route('/animind')
def animind():
    return render_template('animind.html')

@app.route('/animind/recomendar', methods=['POST'])
def recomendar_anime():
    data = request.json or {}
    mensaje_voz = data.get('mensaje_voz', '')

    system_prompt = """
Eres AniMind, una IA experta recomendadora de anime.
Analiza la petición por voz del usuario y recomienda el anime ideal.
Debes responder OBLIGATORIAMENTE en formato JSON estricto:
{
  "titulo": "Nombre del anime",
  "sinopsis_corta": "Resumen rápido de 2 frases",
  "razon_recomendacion": "Por qué encaja con la petición",
  "plataformas": [
    {
      "nombre": "Crunchyroll",
      "audios": ["Japonés", "Español"],
      "subtitulos": ["Español", "Inglés"]
    }
  ]
}
"""
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Petición por voz: {mensaje_voz}"}
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
