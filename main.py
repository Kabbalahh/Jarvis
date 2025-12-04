import os
import datetime
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account

# --- 1. CONFIGURAÇÃO E AUTO-DIAGNÓSTICO ---
load_dotenv()
api_key_google = os.getenv("GOOGLE_API_KEY")
api_key_deepseek = os.getenv("DEEPSEEK_API_KEY")

app = Flask(__name__)
CORS(app)

print("--- INICIANDO SISTEMA JARVIS X ---")

if not api_key_google:
    print("ERRO CRÍTICO: GOOGLE_API_KEY não encontrada nas variáveis de ambiente.")
else:
    genai.configure(api_key=api_key_google)
    try:
        # Tenta listar modelos para garantir que a chave funciona e ver os nomes corretos
        print("Verificando modelos disponíveis na sua conta...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f" - Modelo disponível: {m.name}")
    except Exception as e:
        print(f"AVISO: Não foi possível listar modelos. Erro de conexão: {e}")

# --- 2. INTEGRAÇÃO COM GOOGLE DRIVE (SERVICE ACCOUNT) ---
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json' 
# Nota: No Render, Secret Files são montados em /etc/secrets/ ou na raiz dependendo da config.
# O código abaixo tenta achar o arquivo em ambos os lugares.

def get_drive_service():
    """Autentica usando a Conta de Serviço."""
    target_path = "service_account.json" # Tenta na raiz primeiro
    
    if not os.path.exists(target_path):
        # Tenta no caminho padrão de secrets do Render
        target_path = "/etc/secrets/service_account.json"
    
    if not os.path.exists(target_path):
        print(f"ERRO DE MEMÓRIA: Arquivo de credencial não encontrado em {target_path}")
        return None

    try:
        creds = service_account.Credentials.from_service_account_file(
            target_path, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"ERRO CRÍTICO DRIVE: O arquivo JSON provavelmente está incorreto. Detalhes: {e}")
        return None

def save_to_drive_log(user_msg, ai_response):
    service = get_drive_service()
    if not service:
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content_text = f"[{timestamp}]\nUSER: {user_msg}\nJARVIS: {ai_response}\n{'-'*40}\n"

    try:
        # Procura a pasta
        query = "name = 'JARVIS_MEMORY' and mimeType = 'application/vnd.google-apps.folder'"
        results = service.files().list(q=query, spaces='drive').execute()
        items = results.get('files', [])
        
        parent_id = None
        if items:
            parent_id = items[0]['id']
        else:
            print("Aviso: Pasta JARVIS_MEMORY não encontrada no Drive da Service Account.")
            # Dica: Compartilhe a pasta do seu Drive pessoal com o email que está dentro do JSON
            return

        # Cria nome do arquivo
        exact_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        final_filename = f"Log_{exact_time}.txt"
        
        from googleapiclient.http import MediaIoBaseUpload
        import io
        
        media = MediaIoBaseUpload(io.BytesIO(content_text.encode('utf-8')), mimetype='text/plain')
        file_metadata = {'name': final_filename, 'parents': [parent_id]}
        
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"SUCESSO: Memória salva no Drive ({final_filename})")
    except Exception as e:
        print(f"Erro ao gravar no Drive: {e}")

# --- 3. GERAÇÃO DE IA (CORREÇÃO DO ERRO 404) ---

def get_gemini_response(prompt):
    # Tenta hierarquia de modelos para evitar falha
    model_options = ["models/gemini-1.5-flash", "gemini-1.5-flash", "gemini-1.5-flash-001", "gemini-pro"]
    
    last_error = None

    for model_name in model_options:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            last_error = e
            print(f"Tentativa com {model_name} falhou. Tentando próximo...")
            continue
            
    # Se todos falharem
    return f"Erro no Sistema Cognitivo: {str(last_error)}"

def cognitive_router(user_message):
    if not api_key_deepseek: return "gemini"
    
    msg_lower = user_message.lower()
    triggers = ['código', 'python', 'script', 'lógica', 'algoritmo']
    if any(t in msg_lower for t in triggers):
        return "deepseek"
    return "gemini"

def get_deepseek_response(prompt):
    if not api_key_deepseek: return None
    try:
        headers = {"Authorization": f"Bearer {api_key_deepseek}", "Content-Type": "application/json"}
        data = {
            "model": "deepseek-coder",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        r = requests.post("https://api.deepseek.com/chat/completions", json=data, headers=headers)
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content']
    except:
        return None

# --- 4. ROTAS ---
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "online", "system": "Jarvis X v2.2 Auto-Fix"})

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "No JSON"}), 400
        
        user_message = data.get('message', '')
        if not user_message: return jsonify({"error": "Empty message"}), 400

        # Lógica de IA
        brain = cognitive_router(user_message)
        response_text = ""
        source = ""

        if brain == "deepseek":
            print("Usando DeepSeek...")
            response_text = get_deepseek_response(user_message)
            source = "[DeepSeek]"
            if not response_text: # Fallback
                brain = "gemini"

        if brain == "gemini":
            print("Usando Gemini...")
            response_text = get_gemini_response(user_message)
            source = "[Gemini]"

        # Salvar Memória (Sem travar o chat se der erro)
        try:
            save_to_drive_log(user_message, response_text)
        except Exception as e:
            print(f"Erro silencioso na memória: {e}")

        return jsonify({"response": response_text, "model": source})

    except Exception as e:
        print(f"ERRO FATAL NA ROTA: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
