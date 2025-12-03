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
    
    # --- AUTO-DIAGNÓSTICO AO INICIAR ---
    print("--- INICIANDO DIAGNÓSTICO DE MODELOS ---")
    try:
        print(f"Chave configurada (primeiros 5 carac): {api_key[:5]}...")
        print("Listando modelos disponíveis para esta chave:")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f" - Encontrado: {m.name}")
    except Exception as e:
        print(f"ERRO CRÍTICO NO DIAGNÓSTICO: {e}")
    print("----------------------------------------")

# Função para criar o modelo com fallback
def get_model():
    # Tenta configurações diferentes para garantir funcionamento
    config = {
        "temperature": 0.7,
        "max_output_tokens": 2048,
    }
    
    # Tenta usar o modelo Flash (mais rápido), se falhar, o código avisará
    # Usando o nome técnico 'gemini-1.5-flash-latest' que é mais robusto
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash-latest", 
        generation_config=config,
        system_instruction="Você é o JARVIS X, assistente do Mestre Alisson. Responda de forma concisa e tecnológica."
    )

model = get_model()

# --- ROTAS ---
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "online", "version": "v1.3 Diagnostic"})

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
        # Se der erro 404 aqui, veremos no log qual modelo ele tentou
        error_msg = str(e)
        print(f"ERRO GERAÇÃO: {error_msg}")
        
        # Tenta fallback para um modelo mais antigo se o Flash falhar
        if "404" in error_msg:
            return jsonify({"response": "Mestre, o modelo Flash não foi encontrado. Verifique os logs do Render para ver a lista de modelos disponíveis (gemini-pro, etc).", "error_code": "MODEL_404"})
            
        return jsonify({"error": "Falha no processamento", "details": error_msg}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
