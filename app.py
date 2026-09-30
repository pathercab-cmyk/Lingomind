from flask import Flask, render_template, request, jsonify, send_file
import os
import io
import json
from gtts import gTTS
import google.generativeai as genai

app = Flask(__name__)

# Configuración de API Key para Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Mapeo de códigos de idioma para TTS
TTS_LANG_MAP = {
    'en': 'en',
    'de': 'de',
    'fr': 'fr',
    'it': 'it',
    'pt': 'pt',
    'zh': 'zh-CN',
    'ja': 'ja',
    'ru': 'ru',
    'es': 'es'
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    mensaje_usuario = data.get('mensaje', '')
    idioma = data.get('idioma', 'en')
    nivel = data.get('nivel', 'B1')
    modo = data.get('modo', 'conversacion')
    tipo_examen = data.get('tipo_examen', '')

    system_prompt = f"""
    Eres Oralis, un tutor de idiomas de la Universidad de Sevilla.
    Idioma actual de práctica: {idioma.upper()}
    Nivel MCERL del estudiante: {nivel}
    Modo actual: {modo.upper()} {f' (Examen: {tipo_examen})' if modo == 'examen' else ''}

    Debes responder en formato JSON estricto con esta estructura:
    {{
        "respuesta": "Tu respuesta en el idioma objetivo ({idioma.upper()}) adaptada al nivel {nivel}",
        "correccion": "Corrección puntual del mensaje del usuario (en español) si cometió errores, o '¡Todo correcto!' si estuvo impecable",
        "explicacion": "Explicación clara en español de la corrección o consejos pedagógicos",
        "vocabulario": "Contexto: palabra1, palabra2 (vocabulario clave usado en tu respuesta)",
        "gramatica": "Tema: Regla o estructura gramatical relevante destacada"
    }}
    """

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        chat_session = model.start_chat()
        response = chat_session.send_message(f"{system_prompt}\n\nMensaje del estudiante: {mensaje_usuario}")
        
        # Limpieza por si la respuesta trae marcas Markdown
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        json_data = json.loads(clean_text)
        return jsonify(json_data)

    except Exception as e:
        print("Error al procesar con Gemini:", e)
        return jsonify({
            "respuesta": f"I received your message! Let's continue practicing.",
            "correccion": "No se pudo procesar la evaluación detallada en este momento.",
            "explicacion": "Asegúrate de que la clave GEMINI_API_KEY esté correctamente configurada en Render.",
            "vocabulario": "General: practice, conversation",
            "gramatica": "General: Present Continuous"
        })

@app.route('/tts', methods=['POST'])
def text_to_speech():
    try:
        data = request.json
        texto = data.get('texto', '')
        idioma = data.get('idioma', 'en')

        lang_code = TTS_LANG_MAP.get(idioma, 'en')
        
        tts = gTTS(text=texto, lang=lang_code)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)

        return send_file(fp, mimetype='audio/mpeg')

    except Exception as e:
        print("Error en servicio TTS:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
