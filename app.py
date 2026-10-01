import os
import io
import json
from flask import Flask, render_template, request, jsonify, send_file
from groq import Groq
from gtts import gTTS

# Librerías para lectura de documentos en el módulo Writing
try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None

app = Flask(__name__)

# Inicializar cliente de Groq
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

TTS_LANG_MAP = {
    'en': 'en', 'de': 'de', 'fr': 'fr', 'it': 'it',
    'pt': 'pt', 'zh': 'zh-CN', 'ja': 'ja', 'ru': 'ru', 'es': 'es'
}

@app.route('/')
def index():
    return render_template('index.html')

# =======================================================
# 1. MÓDULO CHAT (Profesor, Tutor / Profesiones, Práctica)
# =======================================================

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json or {}
    mensaje_usuario = data.get('mensaje', '')
    idioma = data.get('idioma', 'en')
    nivel = data.get('nivel', 'A1')
    modo = data.get('modo', 'profesor') # 'profesor', 'tutor', 'practica'
    profesion = data.get('profesion', 'Profesor de Idiomas')
    tema = data.get('tema', 'General')

    # --- MODO PROFESOR (Instrucción Guiada y Explicativa) ---
    if modo == 'profesor':
        system_prompt = f"""
Eres Oralis, un PROFESOR DE IDIOMAS de la Universidad de Sevilla impartiendo una lección de {idioma.upper()} (Nivel {nivel}).
Tema actual: {tema}

Tu función es enseñar el idioma desde cero o reforzar conceptos:
1. Explica brevemente la regla o vocabulario clave en español.
2. Da ejemplos claros en {idioma.upper()} con su traducción.
3. Plantea un ejercicio interactivo o pregunta para que el estudiante aplique lo aprendido.

Debes responder OBLIGATORIAMENTE en formato JSON estricto:
{{
  "modo": "profesor",
  "explicacion": "Explicación teórica pedagógica en español",
  "ejemplo": "Ejemplo relevante en {idioma.upper()} con traducción",
  "ejercicio": "Ejercicio o pregunta propuesta para el alumno",
  "respuesta": "Frase de apoyo docente en {idioma.upper()}"
}}
"""

    # --- MODO TUTOR / PROFESIONES (Simulación de Roles) ---
    elif modo == 'tutor':
        system_prompt = f"""
Eres Oralis, desempeñando el rol profesional de: {profesion.upper()} en un contexto real de aprendizaje de {idioma.upper()} (Nivel {nivel}).
Escenario/Tema: {tema}

Instrucciones:
1. Actúa como un/a {profesion} interactuando con el usuario de manera realista.
2. Explica brevemente en español algún término técnico o frase útil para esta situación.
3. Dirígete al estudiante en {idioma.upper()} manteniendo tu personaje acorde a su nivel {nivel}.

Debes responder OBLIGATORIAMENTE en formato JSON estricto:
{{
  "modo": "tutor",
  "profesion_activa": "{profesion}",
  "consejo_situacional": "Explicación del vocabulario/frase clave para este rol (en español)",
  "respuesta": "Tu frase hablada dentro del papel de {profesion} en {idioma.upper()}",
  "vocabulario_clave": "3 términos clave de este escenario"
}}
"""

    # --- MODO PRÁCTICA CONVERSACIONAL (Fluidez Continua) ---
    else:
        system_prompt = f"""
Eres Oralis, un compañero de conversación fluido en {idioma.upper()} (Nivel {nivel}).
Mantén una charla natural e inmersiva sobre: {tema}.
No interrumpas constantemente con correcciones gramaticales extensas. Muestra interés y haz preguntas abiertas.

Debes responder OBLIGATORIAMENTE en formato JSON estricto:
{{
  "modo": "practica",
  "respuesta": "Tu respuesta fluida e inmersiva en {idioma.upper()} adaptada al nivel {nivel}",
  "correccion_rapida": "Nota muy breve de corrección si cometió un error grave, o 'Todo claro'"
}}
"""

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Intervención del estudiante: {mensaje_usuario}"}
            ],
            model="qwen/qwen3.8-27b",
            response_format={"type": "json_object"}
        )
        return jsonify(json.loads(chat_completion.choices[0].message.content))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =======================================================
# 2. EVALUACIÓN Y INFORME FINAL (Modo Práctica)
# =======================================================

@app.route('/evaluar_practica', methods=['POST'])
def evaluar_practica():
    data = request.json or {}
    historial = data.get('historial', [])
    idioma = data.get('idioma', 'en')
    nivel = data.get('nivel', 'A1')

    system_prompt = f"""
Eres un evaluador lingüístico de la Universidad de Sevilla.
Analiza la siguiente conversación completa mantenida por el estudiante en {idioma.upper()} (Nivel objetivo: {nivel}).

Genera un informe final con rúbrica MCERL:
1. Puntuación general (0 a 10).
2. Fortalezas demostradas.
3. Errores recurrentes (gramática, vocabulario, sintaxis).
4. Recomendaciones específicas para mejorar.

Debes responder OBLIGATORIAMENTE en formato JSON estricto:
{{
  "puntuacion": "Nota de 0 a 10",
  "nivel_demostrado": "A1, A2, B1, B2, C1 o C2",
  "puntos_fuertes": ["Punto 1", "Punto 2"],
  "errores_principales": ["Error 1 con sugerencia", "Error 2 con sugerencia"],
  "consejos_mejora": "Resumen pedagógico para el estudiante"
}}
"""

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Historial de la sesión: {json.dumps(historial)}"}
            ],
            model="qwen/qwen3.8-27b",
            response_format={"type": "json_object"}
        )
        return jsonify(json.loads(chat_completion.choices[0].message.content))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =======================================================
# 3. MÓDULO CORRECCIÓN DE WRITING (Archivos / Texto)
# =======================================================

def extraer_texto_archivo(file):
    filename = file.filename.lower()
    if filename.endswith('.txt'):
        return file.read().decode('utf-8')
    elif filename.endswith('.pdf') and pypdf:
        reader = pypdf.PdfReader(file)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text() or ""
        return texto
    elif filename.endswith('.docx') and docx:
        doc = docx.Document(file)
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        return None

@app.route('/corregir_writing', methods=['POST'])
def corregir_writing():
    texto_escribir = request.form.get('texto', '')
    idioma = request.form.get('idioma', 'en')
    tipo_correccion = request.form.get('tipo_correccion', 'explicativa') # 'explicativa', 'senalar', 'descubrimiento'

    # Procesamiento si se sube un archivo
    if 'archivo' in request.files and request.files['archivo'].filename != '':
        archivo = request.files['archivo']
        texto_extraido = extraer_texto_archivo(archivo)
        if texto_extraido:
            texto_escribir = texto_extraido

    if not texto_escribir.strip():
        return jsonify({"error": "No se recibió ningún texto ni archivo válido."}), 400

    if tipo_correccion == 'explicativa':
        instrucciones_modo = """
Proporciona una corrección exhaustiva palabra por palabra y de estructuras. Muestra el texto corregido, los errores identificados con explicaciones gramaticales en español y consejos de estilo.
"""
    elif tipo_correccion == 'senalar':
        instrucciones_modo = """
Señala los errores resaltando la ubicación o frase incorrecta y nombrando la categoría del error (ej. Gramática, Conjugación, Vocabulario), pero sin dar la solución directamente.
"""
    else: # Modo Autodescubrimiento
        instrucciones_modo = """
Modo Autodescubrimiento: Señala en qué parte de la redacción existe un error, explica brevemente de qué trata la falla y genera una 'pista' pedagógica sin revelar la respuesta completa para que el alumno intente corregirlo solo.
"""

    system_prompt = f"""
Eres un profesor experto corrector de redacciones (Writing) en la Universidad de Sevilla para el idioma {idioma.upper()}.
{instrucciones_modo}

Debes responder OBLIGATORIAMENTE en formato JSON estricto:
{{
  "texto_original": "Texto analizado",
  "texto_corregido_sugerido": "Versión corregida (si aplica según el modo)",
  "desglose_errores": [
    {{
      "error": "Palabra o frase con fallo",
      "explicacion": "Explicación del error en español",
      "pista": "Pista para que el alumno lo intente descubrir (relevante si es modo descubrimiento)"
    }}
  ],
  "puntuacion_writing": "Nota sobre 10 con feedback general de coherencia y gramática"
}}
"""

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Writing del estudiante: {texto_escribir}"}
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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
