import os
import datetime
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account # NOVA IMPORTAÇÃO

# --- 1. CONFIGURAÇÃO INICIAL ---
load_dotenv() # Carrega vars locais se existirem
api_key_google = os.getenv("GOOGLE_API_KEY")
api_key_deepseek = os.getenv("DEEPSEEK_API_KEY")

app = Flask(__name__)
CORS(app)

# Configura IA Google
if api_key_google:
    genai.configure(api_key=api_key_google)

# --- 2. CONEXÃO SEGURA GOOGLE DRIVE (SERVICE ACCOUNT) ---
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service_account.json' # O arquivo que está no "Secret Files" do Render

def get_drive_service():
    """Autentica usando a Conta de Serviço (Server-side puro)."""
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            print(f"ERRO: Arquivo {SERVICE_ACCOUNT_FILE} não encontrado.")
            return None

        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Erro na autenticação Drive: {e}")
        return None

def save_to_drive_log(user_msg, ai_response):
    service = get_drive_service()
    if not service:
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Conteúdo a ser salvo
    content_text = f"[{timestamp}]\nUSER: {user_msg}\nJARVIS: {ai_response}\n{'-'*40}\n"

    # 1. Encontrar a pasta 'JARVIS_MEMORY' (Compartilhada com o Robô)
    # Nota: O robô só vê pastas que você compartilhou com o email dele
    query = "name = 'JARVIS_MEMORY' and mimeType = 'application/vnd.google-apps.folder'"
    results = service.files().list(q=query, spaces='drive').execute()
    items = results.get('files', [])
    
    parent_id = None
    if items:
        parent_id = items[0]['id']
    else:
        # Se o robô não achar a pasta, ele cria na raiz DELE (não na sua)
        # Por isso o Passo 4 abaixo é crucial.
        print("Aviso: Pasta JARVIS_MEMORY não encontrada. Verifique o compartilhamento.")
        return

    # 2. Criar/Atualizar Log
    filename = f"Log_{datetime.datetime.now().strftime('%Y-%m-%d')}.txt"
    
    # Verifica se arquivo já existe
    query_file = f"name = '{filename}' and '{parent_id}' in parents"
    results_file = service.files().list(q=query_file).execute()
    files = results_file.get('files', [])

    from googleapiclient.http import MediaIoBaseUpload
    import io

    # Como API de Drive não edita TXT fácil, criamos um novo arquivo com timestamp no nome
    # para evitar sobrescrever (Melhor para MVP)
    exact_time = datetime.datetime.now().strftime('%H-%M-%S')
    final_filename = f"Log_{exact_time}.txt"
    
    media = MediaIoBaseUpload(io.BytesIO(content_text.encode('utf-8')), mimetype='text/plain')
    file_metadata = {'name': final_filename, 'parents': [parent_id]}
    
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"Memória salva: {final_filename}")

# --- 3. CÉREBRO HÍBRIDO ---
def cognitive_router(user_message):
    msg_lower = user_message.lower()
    # Gatilhos para DeepSeek
    triggers_logica = ['código', 'python', 'script', 'matemática', 'lógica', 'algoritmo']
    if any(trigger in msg_lower for trigger in triggers_logica) and api_key_deepseek:
        return "deepseek"
    return "gemini"

def get_gemini_response(prompt):
    model = genai.GenerativeModel("gemini-1.5-flash") # Usando versão estável
    response = model.generate_content(prompt)
    return response.text

def get_deepseek_response(prompt):
    # (Sua lógica anterior do DeepSeek aqui)
    # Simplificada para o exemplo:
    return None 

# --- 4. ROTAS ---
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "online", "mode": "Serverless Secure"})

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    data = request.get_json()
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({"error": "No message"}), 400

    # Lógica de escolha
    brain = cognitive_router(user_message)
    response_text = ""
    
    if brain == "deepseek":
        # response_text = call_deepseek_api(user_message) 
        # Se falhar ou não implementado no exemplo:
        response_text = get_gemini_response(user_message)
    else:
        response_text = get_gemini_response(user_message)

    # Salva na nuvem (Assíncrono idealmente, mas síncrono aqui para garantir)
    try:
        save_to_drive_log(user_message, response_text)
    except Exception as e:
        print(f"Erro memória: {e}")

    return jsonify({"response": response_text})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
