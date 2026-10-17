from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "estacao.db"

app = Flask(__name__, static_folder="static")


def conectar_banco():
    conexao = sqlite3.connect(DB_PATH)
    conexao.row_factory = sqlite3.Row
    return conexao


def criar_banco():
    with conectar_banco() as conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS leituras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                temperatura REAL,
                umidade REAL,
                luminosidade INTEGER,
                latitude REAL,
                longitude REAL
            )
        """)


@app.get("/")
def pagina_inicial():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/readings")
def receber_leitura():
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify({"erro": "Envie os dados em formato JSON."}), 400

    station_id = dados.get("station_id")

    if not isinstance(station_id, str) or not station_id.strip():
        return jsonify({"erro": "O campo station_id é obrigatório."}), 400

    try:
        temperatura = float(dados["temperatura"])
        umidade = float(dados["umidade"])
        luminosidade = int(dados["luminosidade"])
        latitude = float(dados["latitude"])
        longitude = float(dados["longitude"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"erro": "Há campos ausentes ou inválidos."}), 400

    if not -40 <= temperatura <= 85:
        return jsonify({"erro": "Temperatura fora da faixa aceita."}), 400

    if not 0 <= umidade <= 100:
        return jsonify({"erro": "Umidade deve estar entre 0 e 100."}), 400

    if not 0 <= luminosidade <= 4095:
        return jsonify({"erro": "Luminosidade deve estar entre 0 e 4095."}), 400

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return jsonify({"erro": "Coordenadas inválidas."}), 400

    timestamp = datetime.now(timezone.utc).isoformat()

    with conectar_banco() as conexao:
        cursor = conexao.execute("""
            INSERT INTO leituras (
                station_id, timestamp, temperatura, umidade,
                luminosidade, latitude, longitude
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            station_id.strip(),
            timestamp,
            temperatura,
            umidade,
            luminosidade,
            latitude,
            longitude
        ))

        leitura_id = cursor.lastrowid

    return jsonify({
        "ok": True,
        "id": leitura_id,
        "timestamp": timestamp
    }), 201


@app.get("/api/readings")
def listar_leituras():
    try:
        limite = int(request.args.get("limit", "50"))
    except ValueError:
        limite = 50

    limite = max(1, min(limite, 500))

    with conectar_banco() as conexao:
        linhas = conexao.execute("""
            SELECT station_id, timestamp, temperatura, umidade,
                   luminosidade, latitude, longitude
            FROM leituras
            ORDER BY id DESC
            LIMIT ?
        """, (limite,)).fetchall()

    return jsonify([dict(linha) for linha in reversed(linhas)])


@app.post("/api/demo")
def criar_leitura_demo():
    """Cria uma leitura fictícia para experimentar o dashboard."""
    dados = {
        "station_id": "estacao-demo",
        "temperatura": 24.5,
        "umidade": 62,
        "luminosidade": 1800,
        "latitude": -23.5505,
        "longitude": -46.6333
    }

    timestamp = datetime.now(timezone.utc).isoformat()

    with conectar_banco() as conexao:
        conexao.execute("""
            INSERT INTO leituras (
                station_id, timestamp, temperatura, umidade,
                luminosidade, latitude, longitude
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            dados["station_id"],
            timestamp,
            dados["temperatura"],
            dados["umidade"],
            dados["luminosidade"],
            dados["latitude"],
            dados["longitude"]
        ))

    return jsonify({"ok": True, "mensagem": "Leitura de demonstração criada."}), 201


@app.get("/api/health")
def verificar_api():
    return jsonify({"ok": True})


if __name__ == "__main__":
    criar_banco()
    app.run(host="127.0.0.1", port=5000, debug=True)
    