from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Estructura en memoria para almacenar sesiones y progreso del estudiante
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
        # -------------------------------------------------------------------
        respuesta_texto = f"Respuesta simulada en {idioma.upper()} ({nivel}) [Modo: {modo}]: Entendido tu mensaje: '{mensaje}'."
        correccion = "Ninguna"
        explicacion = ""
        
        # Simulación de extracción de vocabulario y gramática
        nuevo_vocabulario = [f"ejemplo_{len(mensaje)} (traducción)"] if len(mensaje) > 3 else []
        nueva_gramatica = [f"Estructura gramatical ({nivel})"] if len(mensaje) > 3 else []

        # --- REGISTRO AUTOMÁTICO EN EL CUADERNO ---
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
    # BANCO COMPLETO DE EXÁMENES OFICIALES POR IDIOMA
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
    return jsonify({
        "gramatica": [f"Estructuras Clave ({nivel})", f"Conectores y Oraciones Subordinadas ({nivel})"],
        "vocabulario": [f"Vocabulario Profesional ({nivel})", f"Expresiones Cotidianas ({nivel})"]
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
