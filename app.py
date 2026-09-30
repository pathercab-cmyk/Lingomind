import os
import io
import json
from flask import Flask, render_template, request, jsonify, send_file
from groq import Groq
from gtts import gTTS

app = Flask(__name__)

# Inicializar cliente de Groq con la clave de entorno
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

# Mapeo de códigos de idioma para TTS (gTTS)
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
    # Carga la interfaz gráfica completa (index.html)
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json or {}
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

    Debes responder OBLIGATORIAMENTE en formato JSON estricto sin bloques de markdown:
    {{
        "respuesta": "Tu respuesta en el idioma objetivo ({idioma.upper()}) adaptada al nivel {nivel}",
        "correccion": "Corrección puntual del mensaje del usuario (en español) si cometió errores, o '¡Todo correcto!' si estuvo impecable",
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
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )

        respuesta_raw = chat_completion.choices[0].message.content
        json_data = json.loads(respuesta_raw)
        return jsonify(json_data)

    except Exception as e:
        print("Error al procesar con Groq:", e)
        return jsonify({
            "respuesta": f"I received your message! Let's continue practicing.",
            "correccion": "Ocurrió un detalle al procesar la evaluación.",
            "explicacion": str(e),
            "vocabulario": "General: practice, conversation",
            "gramatica": "General: Present Continuous"
        })

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
        print("Error en servicio TTS:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
