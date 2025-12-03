import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# 1. Carregar variáveis de ambiente (Segurança)
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# 2. Configuração Inicial do Flask
app = Flask(__name__)
# Habilita CORS para que seu HTML (GitHub Pages/Local) consiga falar com este Python
CORS(app) 

# 3. Configuração do Gemini (Cérebro)
if not api_key:
    print("ERRO CRÍTICO: Chave de API do Google não encontrada no arquivo .env")
else:
    genai.configure(api_key=api_key)

# Configurações do Modelo
generation_config = {
    "temperature": 0.7,   # Criatividade (0.0 = robótico, 1.0 = criativo)
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}

safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
]

# Inicializa o modelo (Usando a versão Flash para velocidade e custo zero)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    safety_settings=safety_settings,
    system_instruction="Você é o JARVIS X, uma inteligência artificial avançada e assistente pessoal do Mestre Alisson. Suas respostas devem ser concisas, lógicas e extremamente úteis. Você tem um tom levemente formal, tecnológico, mas leal."
)

# --- ROTAS DA API ---

@app.route('/', methods=['GET'])
def health_check():
    """Rota para verificar se o servidor está online (Ping)."""
    return jsonify({
        "status": "online",
        "system": "Jarvis X Cognitive Core",
        "version": "2.0.1"
    })

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    """
    Rota principal que recebe a mensagem do usuário e retorna a resposta da IA.
    Esperado JSON: { "message": "Olá Jarvis" }
    """
    try:
        data = request.get_json()
        
        # Validação simples
        if not data or 'message' not in data:
            return jsonify({"error": "Formato inválido. Envie um JSON com o campo 'message'."}), 400
        
        user_message = data['message']
        
        # --- O PENSAMENTO (Chamada ao Gemini) ---
        # Aqui iniciamos uma sessão de chat simples (sem histórico longo por enquanto)
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(user_message)
        
        # Retorna a resposta de texto
        return jsonify({
            "response": response.text,
            "status": "success"
        })

    except Exception as e:
        print(f"Erro no processamento: {e}")
        return jsonify({"error": "Falha interna no processamento cognitivo.", "details": str(e)}), 500

# Inicialização do Servidor
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"--> INICIALIZANDO NÚCLEO JARVIS X NA PORTA {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
