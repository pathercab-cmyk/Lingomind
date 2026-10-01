from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Estructura en memoria para almacenar sesiones y progreso del estudiante
# (Se conservan todos los elementos originales y se asegura el soporte extendido)
PERFILES_USUARIO = {
    "historiales": [], # Almacena chats guardados
    "vocabulario": {}, # Formato: { "en": { "Viajes": ["boarding pass - tarjeta de embarque"] } }
    "gramatica": {}    # Formato: { "en": { "B1": ["Present Perfect continuous"] } }
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json or {}
        mensaje = data.get('mensaje', '')
        idioma = data.get('idioma', 'en')
        nivel = data.get('nivel', 'B1')
        modo = data.get('modo', 'tutor_original')
        profesion = data.get('profesion', '')
        tipo_examen = data.get('tipo_examen', '')
        tema = data.get('tema') or 'Conversación General'

        # -------------------------------------------------------------------
        # AQUÍ INTEGRAS TU LLAMADA A LA IA (OpenAI, Gemini, etc.)
        # Manteniendo todos los parámetros recibidos sin descartar nada.
        # -------------------------------------------------------------------
        respuesta_texto = f"Respuesta simulada en {idioma.upper()} ({nivel}) [Modo: {modo}]: Entendido tu mensaje: '{mensaje}'."
        correccion = "Ninguna"
        explicacion = ""
        
        # Simulación de extracción de vocabulario y gramática del mensaje
        nuevo_vocabulario = [f"ejemplo_{len(mensaje)} (traducción)"] if len(mensaje) > 3 else []
        nueva_gramatica = [f"Estructura gramatical ({nivel})"] if len(mensaje) > 3 else []

        # --- REGISTRO AUTOMÁTICO EN EL CUADERNO (Adición conservadora) ---
        # Vocabulario por Contexto
        if idioma not in PERFILES_USUARIO["vocabulario"]:
            PERFILES_USUARIO["vocabulario"][idioma] = {}
        if tema not in PERFILES_USUARIO["vocabulario"][idioma]:
            PERFILES_USUARIO["vocabulario"][idioma][tema] = []

        for word in nuevo_vocabulario:
            if word not in PERFILES_USUARIO["vocabulario"][idioma][tema]:
                PERFILES_USUARIO["vocabulario"][idioma][tema].append(word)

        # Gramática por Nivel
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
            "explicacion": explicacion,
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
        "en": ["Cambridge B2 First", "Cambridge C1 Advanced", "IELTS Academic", "TOEFL iBT"],
        "es": ["DELE B1", "DELE B2", "DELE C1", "SIELE"],
        "fr": ["DELF B1", "DELF B2", "DALF C1"],
        "de": ["Goethe-Zertifikat B1", "Goethe-Zertifikat B2", "TestDaF"]
    }
    return jsonify({"examenes": examenes.get(idioma, ["Examen Oficial Estándar"])})

@app.route('/api/banco/<nivel>', methods=['GET'])
def obtener_banco(nivel):
    return jsonify({
        "gramatica": [f"Estructuras Clave ({nivel})", f"Conectores y Oraciones Subordinadas ({nivel})"],
        "vocabulario": [f"Vocabulario Profesional ({nivel})", f"Expresiones Cotidianas ({nivel})"]
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
