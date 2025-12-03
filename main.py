import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# 1. Configuração Inicial
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
app = Flask(__name__)
CORS(app)

# 2. Configuração do Gemini
if not api_key:
    print("ERRO: API Key não encontrada.")
else:
    genai.configure(api_key=api_key)

# Função para criar o modelo com a versão correta encontrada no log
def get_model():
    config = {
        "temperature": 0.7,
        "max_output_tokens": 2048,
    }
    
    # ATUALIZAÇÃO: Usando a versão 2.5 Flash que apareceu explicitamente no seu log
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash", 
        generation_config=config,
        system_instruction="Você é o JARVIS X, assistente do Mestre Alisson. Responda de forma concisa, tecnológica e direta."
    )

model = get_model()

# --- ROTAS ---
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "online", "version": "v1.4 Stable"})

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({"error": "Mensagem vazia"}), 400

        # Gera a resposta
        response = model.generate_content(user_message)
        
        return jsonify({
            "response": response.text,
            "status": "success"
        })

    except Exception as e:
        error_msg = str(e)
        print(f"ERRO GERAÇÃO: {error_msg}")
        return jsonify({"error": "Falha no processamento", "details": error_msg}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
