import os
import google.generativeai as genai
import requests  # Necessário para chamar a DeepSeek via HTTP
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# --- 1. CONFIGURAÇÃO INICIAL ---
load_dotenv()
api_key_google = os.getenv("GOOGLE_API_KEY")
api_key_deepseek = os.getenv("DEEPSEEK_API_KEY")

app = Flask(__name__)
CORS(app)

# Validação de Chaves
if not api_key_google:
    print("ALERTA: Google API Key não encontrada.")
else:
    genai.configure(api_key=api_key_google)

if not api_key_deepseek:
    print("ALERTA: DeepSeek API Key não encontrada (Modo DeepSeek desativado).")

# --- 2. CONFIGURAÇÃO DOS MODELOS ---

# Modelo A: Gemini (Velocidade e Contexto Geral)
def get_gemini_model():
    config = {
        "temperature": 0.7,
        "max_output_tokens": 2048,
    }
    # Mantendo a versão que você validou
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash", 
        generation_config=config,
        system_instruction="Você é o JARVIS X, assistente do Mestre Alisson. Responda de forma concisa, tecnológica e direta."
    )

# Modelo B: DeepSeek (Raciocínio Lógico e Código)
def call_deepseek_api(prompt):
    try:
        headers = {
            "Authorization": f"Bearer {api_key_deepseek}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-coder", # Ou "deepseek-chat"
            "messages": [
                {"role": "system", "content": "Você é o Jarvis X, focado em lógica e programação avançada."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2 # Menor temperatura para precisão
        }
        
        response = requests.post("https://api.deepseek.com/chat/completions", json=data, headers=headers)
        response.raise_for_status()
        
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Erro no DeepSeek, fallback para Gemini: {e}")
        return None # Retorna None para forçar o uso do Gemini como backup

# --- 3. O CÉREBRO (ROUTER LÓGICO) ---
def cognitive_router(user_message):
    """
    Analisa a mensagem para decidir qual 'lóbulo' do cérebro usar.
    """
    msg_lower = user_message.lower()
    
    # Palavras-chave que acionam o pensamento lógico (DeepSeek)
    triggers_logica = ['código', 'python', 'script', 'matemática', 'lógica', 'algoritmo', 'refatore', 'bug']
    
    # Verifica se precisa de raciocínio complexo
    if any(trigger in msg_lower for trigger in triggers_logica) and api_key_deepseek:
        return "deepseek"
    
    return "gemini"

# --- 4. ROTAS ---
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "online", 
        "version": "v2.0 Hybrid Brain",
        "modules": ["Gemini Flash", "DeepSeek Logic"]
    })

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({"error": "Mensagem vazia"}), 400

        # 1. Roteamento (Decisão)
        chosen_model = cognitive_router(user_message)
        response_text = ""
        source_tag = ""

        # 2. Execução
        if chosen_model == "deepseek":
            print(f"Log: Acionando DeepSeek para: {user_message[:20]}...")
            response_text = call_deepseek_api(user_message)
            source_tag = "[DeepSeek Logic]"
            
            # Fallback: Se o DeepSeek falhar (retornar None), usa o Gemini
            if not response_text:
                chosen_model = "gemini" # Muda a flag para cair no bloco abaixo

        if chosen_model == "gemini":
            print(f"Log: Acionando Gemini para: {user_message[:20]}...")
            model = get_gemini_model()
            response_obj = model.generate_content(user_message)
            response_text = response_obj.text
            source_tag = "[Gemini Flash]"

        # 3. Resposta Final
        return jsonify({
            "response": response_text,
            "used_model": source_tag, # Útil para debug no frontend
            "status": "success"
        })

    except Exception as e:
        error_msg = str(e)
        print(f"ERRO CRÍTICO: {error_msg}")
        return jsonify({"error": "Falha no sistema cognitivo", "details": error_msg}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
