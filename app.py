import os
import json
from flask import Flask, render_template, request, jsonify
from groq import Groq
import PyPDF2
import docx

app = Flask(__name__)

# Configuración del cliente oficial de Groq
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Modelo compatible de Groq (se corrigió el identificador del modelo)
MODELO_GROQ = "qwen-2.5-32b"

# Base de datos simulada en memoria
PERFILES_USUARIO = {
    "default": {
        "idioma": "en",
        "nivel": "B1",
        "modo": "tutor_original",
        "vocabulario_aprendido": {},
        "gramatica_estudiada": {}
    }
}

EXAMENES_OFICIALES = {
    "en": ["Cambridge (PET, FCE, CAE)", "IELTS", "TOEFL", "TOEIC"],
    "fr": ["DELF / DALF", "TCF", "TEF"],
    "de": ["Goethe-Zertifikat", "TestDaF", "DSH"],
    "ro": ["RLA - Romanian Language Assessment", "Certificat de Competență Lingvistică"],
    "it": ["CELI", "CILS", "PLIDA"],
    "pt": ["CAPLE", "CELPE-Bras"],
    "nl": ["CNaVT", "Inburgeringsexamen"],
    "zh": ["HSK (Hanyu Shuiping Kaoshi)"],
    "ja": ["JLPT (N5 - N1)"],
    "ru": ["TORFL / TRKI"],
    "es": ["DELE", "SIELE"],
    "ar": ["ALPT"]
}

BANCO_RECURSOS = {
    "A1": {
        "gramatica": ["Presente Simple / Ser y Estar", "Artículos y Sustantivos Básicos", "Estructura de Oraciones Simples"],
        "vocabulario": ["Saludos y Saludos Cotidianos", "Números y Horas", "Familia y Actividades Diarias"],
        "conectores": ["y", "pero", "porque"],
        "fonetica": ["Vocales básicas y sonidos iniciales"]
    },
    "A2": {
        "gramatica": ["Pasado Simple", "Comparativos y Superlativos", "Verbos Modales Básicos"],
        "vocabulario": ["Viajes y Transporte", "Compras y Comida", "Trabajo y Profesiones"],
        "conectores": ["además", "sin embargo", "entonces"],
        "fonetica": ["Terminaciones en -ed y consonantes suaves"]
    },
    "B1": {
        "gramatica": ["Tiempos Perfectos (Present Perfect)", "Condicional Primario", "Voz Pasiva Introductoria"],
        "vocabulario": ["Opiniones y Sentimientos", "Tecnología y Medio Ambiente", "Experiencias Personales"],
        "conectores": ["por lo tanto", "a pesar de", "en primer lugar"],
        "fonetica": ["Intonación de preguntas y acento léxico"]
    },
    "B2": {
        "gramatica": ["Condicionales Mixtos", "Estilo Indirecto (Reported Speech)", "Subjuntivo / Modales en Pasado"],
        "vocabulario": ["Debates y Argumentación", "Términos Académicos y Profesionales", "Expresiones Idiomáticas"],
        "conectores": ["en consecuencia", "no obstante", "por consiguiente"],
        "fonetica": ["Ritmo en oraciones complejas y enlaces fónicos"]
    },
    "C1": {
        "gramatica": ["Inversión Gramatical", "Estructuras Avanzadas de Subjuntivo", "Matices de Aspecto y Modo"],
        "vocabulario": ["Vocabulario Técnico / Formal", "Matices Semánticos Prolijos", "Sarcasmo e Ironía Fina"],
        "conectores": ["de ahí que", "en vista de lo cual", "amén de"],
        "fonetica": ["Variaciones dialectales y matices emocionales"]
    },
    "C2": {
        "gramatica": ["Dominio Sintáctico Total", "Estilo Literario y Retórico", "Flexibilidad de Expresión Nativa"],
        "vocabulario": ["Jerga Especializada", "Neologismos y Arcaísmos", "Metáforas Complejas"],
        "conectores": ["consustancialmente", "en puridad", "sin perjuicio de"],
        "fonetica": ["Fluidez absoluta equivalente a un hablante nativo culto"]
    }
}


def extraer_texto_archivo(file):
    filename = file.filename.lower()
    texto = ""
    try:
        if filename.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    texto += t + "\n"
        elif filename.endswith('.docx'):
            doc = docx.Document(file)
            for p in doc.paragraphs:
                if p.text:
                    texto += p.text + "\n"
        elif filename.endswith('.txt'):
            texto = file.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error procesando archivo: {e}")
    return texto.strip()


def construir_prompt_sistema(idioma, nivel, modo, profesion, profesion_custom, tipo_examen, tema, metodo_writing):
    prof_final = profesion_custom if profesion == "Otro" else profesion

    prompt_base = f"""Eres Oralis, una plataforma de inteligencia artificial especializada en la enseñanza de idiomas.
Estás interactuando con un estudiante que aprende el idioma con código ISO '{idioma}' en un nivel MCERL '{nivel}'.
Tema o contexto general de la sesión: {tema}.

Instrucciones generales de tono e interacción:
1. Responde siempre de forma pedagógica, motivadora y adaptable.
2. Tu respuesta principal debe ser en el idioma objetivo ({idioma}), adaptando la complejidad sintáctica al nivel {nivel}.
3. Si el usuario te hace una pregunta teórica en español o pide una explicación gramatical, explica la regla detalladamente en español y proporciona ejemplos prácticos en {idioma}.
4. FORMATO OBLIGATORIO: NO utilices ningún tipo de formato Markdown en tu respuesta. Está PROHIBIDO usar asteriscos (*), dobles asteriscos (**), almohadillas (#), guiones bajos (_) o tablas en Markdown. Presenta la respuesta en texto plano limpio usando saltos de línea normales y viñetas simples con guiones (-).
"""

    if modo == "tutor_original":
        prompt_base += """
Modo ACTIVO: Tutor / Profesor (Dual).
- Mantén una conversación fluida e interactiva en el idioma objetivo.
- Corrige sutilmente los errores que cometa el alumno.
- Si el alumno te pide aclaraciones gramaticales, asume el rol de Profesor y responde con explicaciones en español.
"""
    elif modo == "practicas_orales":
        prompt_base += f"""
Modo ACTIVO: Prácticas Orales / Simulación de Roles.
- Asume el rol de: {prof_final}.
- Simula una situación real correspondiente a ese rol (ej. una entrevista, consulta médica, check-in de hotel, etc.).
- No te salgas del personaje a menos que el usuario pida ayuda explícita.
"""
    elif modo == "examen":
        prompt_base += f"""
Modo ACTIVO: Exámenes Oficiales.
- Estás preparando al alumno para la prueba acreditada: {tipo_examen}.
- Plantea ejercicios, preguntas de Speaking/Writing tipo examen y proporciona retroalimentación formateada según los criterios de dicha prueba oficial.
"""
    elif modo == "writing":
        if metodo_writing == "pistas":
            prompt_base += """
Modo ACTIVO: Writing - Método 2 (Subrayado + Pistas).
- Analiza el texto enviado por el estudiante.
- Identifica el error principal sin darle la respuesta directa.
- Devuelve la respuesta obligatoriamente estructurada en formato JSON estricto con las siguientes claves:
  {
    "respuesta": "Tu mensaje general de ánimo o comentario en el idioma objetivo.",
    "texto_subrayado": "La frase o fragmento exacto donde está el error",
    "pista": "Una pista inductiva clara en español para que el estudiante razone y corrija el error por sí mismo."
  }
"""
        else:
            prompt_base += """
Modo ACTIVO: Writing - Método 1 (Corrección Directa).
- Revisa minuciosamente el texto proporcionado.
- Muestra la corrección directa de las faltas cometidas y explica detalladamente en español por qué se aplica esa regla.
- Devuelve la respuesta preferiblemente en formato JSON estricto con la estructura:
  {
    "respuesta": "Tu retroalimentación general sobre el texto.",
    "correccion": "El texto completamente corregido.",
    "explicacion": "Explicación detallada en español de las reglas sintácticas o gramaticales corregidas."
  }
"""

    return prompt_base


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    mensaje_usuario = request.form.get('mensaje', '')
    idioma = request.form.get('idioma', 'en')
    nivel = request.form.get('nivel', 'B1')
    modo = request.form.get('modo', 'tutor_original')
    profesion = request.form.get('profesion', '')
    profesion_custom = request.form.get('profesion_custom', '')
    tipo_examen = request.form.get('tipo_examen', '')
    tema = request.form.get('tema', '')
    metodo_writing = request.form.get('metodo_writing', 'gramatica')

    # Procesar archivo si se ha adjuntado alguno (Writing)
    texto_archivo = ""
    if 'archivo' in request.files:
        file = request.files['archivo']
        if file and file.filename != '':
            texto_archivo = extraer_texto_archivo(file)

    contenido_completo = mensaje_usuario
    if texto_archivo:
        contenido_completo += f"\n\n[Contenido del archivo adjunto]:\n{texto_archivo}"

    system_prompt = construir_prompt_sistema(
        idioma, nivel, modo, profesion, profesion_custom, tipo_examen, tema, metodo_writing
    )

    try:
        # Llamada a la API de Groq usando la SDK nativa
        completion = client.chat.completions.create(
            model=MODELO_GROQ,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": contenido_completo}
            ],
            temperature=0.6,
            max_completion_tokens=2048,
            top_p=0.95
        )

        respuesta_raw = completion.choices[0].message.content.strip()

        # Respuesta estructurada por defecto
        resultado = {
            "respuesta": respuesta_raw,
            "modo": modo,
            "metodo_writing": metodo_writing,
            "correccion": None,
            "explicacion": None,
            "texto_subrayado": None,
            "pista": None,
            "vocabulario": None
        }

        # Intentar parsear JSON en caso de que el modo haya solicitado respuesta estructurada
        if modo == "writing" or "{" in respuesta_raw:
            try:
                inicio = respuesta_raw.find("{")
                fin = respuesta_raw.rfind("}") + 1
                if inicio != -1 and fin != -1:
                    json_data = json.loads(respuesta_raw[inicio:fin])
                    resultado.update(json_data)
            except Exception:
                pass

        return jsonify(resultado)

    except Exception as e:
        print(f"Error llamando a la API de Groq: {e}")
        return jsonify({
            "respuesta": f"Lo siento, ocurrió un error al procesar tu solicitud con el modelo: {str(e)}",
            "modo": modo,
            "metodo_writing": metodo_writing
        }), 500


@app.route('/api/examenes/<idioma>', methods=['GET'])
def obtener_examenes(idioma):
    lista = EXAMENES_OFICIALES.get(idioma.lower(), ["Examen Estándar de Certificación"])
    return jsonify({"examenes": lista})


@app.route('/api/banco/<nivel>', methods=['GET'])
def obtener_banco(nivel):
    datos = BANCO_RECURSOS.get(nivel.upper(), BANCO_RECURSOS["B1"])
    return jsonify(datos)


@app.route('/api/obtener_recursos_aprendidos/<idioma>', methods=['GET'])
def obtener_recursos_aprendidos(idioma):
    perfil = PERFILES_USUARIO.get("default", {})
    return jsonify({
        "vocabulario": perfil.get("vocabulario_aprendido", {}),
        "gramatica": perfil.get("gramatica_estudiada", {})
    })


@app.route('/api/guardar_sesion', methods=['POST'])
def guardar_sesion():
    data = request.get_json()
    return jsonify({"status": "ok", "mensaje": "Sesión guardada correctamente"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
