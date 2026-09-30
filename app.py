from flask import Flask, render_template, request, jsonify
from tutor import obtener_respuesta_tutor

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    mensaje = data.get('mensaje', '')
    idioma = data.get('idioma', 'en')
    nivel = data.get('nivel', 'B1')
    modo = data.get('modo', 'conversacion')
    tipo_examen = data.get('tipo_examen', 'Cambridge')

    respuesta_raw = obtener_respuesta_tutor(mensaje, idioma, nivel, modo, tipo_examen)
    partes = respuesta_raw.split('|')

    respuesta = partes[0].strip() if len(partes) > 0 else "Error al procesar la respuesta."
    correccion = partes[1].strip() if len(partes) > 1 else ""
    explicacion = partes[2].strip() if len(partes) > 2 else ""
    vocabulario = partes[3].strip() if len(partes) > 3 else ""

    return jsonify({
        'respuesta': respuesta,
        'correccion': correccion,
        'explicacion': explicacion,
        'vocabulario': vocabulario
    })

if __name__ == '__main__':
    app.run(debug=True)
    app.run(debug=True)
