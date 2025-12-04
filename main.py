import os
import datetime
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# --- 1. CONFIGURAÇÃO INICIAL ---
load_dotenv()
api_key_google = os.getenv("GOOGLE_API_KEY")
api_key_deepseek = os.getenv("DEEPSEEK_API_KEY")

app = Flask(__name__)
CORS(app)

# Configuração da IA
if api_key_google:
    genai.configure(api_key=api_key_google)

# --- 2. SISTEMA DE MEMÓRIA (DRIVE COM TOKEN.JSON) ---
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    # Procura o token injetado pelo Render
    token_paths = ["/etc/secrets/token.json", "token.json"]
    token_path = next((p for p in token_paths if os.path.exists(p)), None)

    if not token_path:
        print("ALERTA: Arquivo token.json não encontrado nos Secret Files.")
        return None

    try:
        # Carrega a credencial do Mestre Alisson
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Erro ao ler token.json: {e}")
        return None

def save_to_drive_log(user_msg, ai_response):
    service = get_drive_service()
    if not service: return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_content = f"[{timestamp}]\nUSER: {user_msg}\nJARVIS: {ai_response}\n{'-'*40}\n"

    try:
        # 1. Verifica se a pasta JARVIS_MEMORY existe
        query = "name = 'JARVIS_MEMORY' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(q=query, spaces='drive').execute()
        items = results.get('files', [])
        
        folder_id = None
        if items:
            folder_id = items[0]['id']
        else:
            # Se não existir, cria (Agora temos permissão!)
            file_metadata = {
                'name': 'JARVIS_MEMORY',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=file_metadata, fields='id').execute()
            folder_id = folder.get('id')
            print("Pasta JARVIS_MEMORY criada automaticamente.")

        # 2. Salva o Log
        from googleapiclient.http import MediaIoBaseUpload
        import io
        
        filename = f"Log_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        media = MediaIoBaseUpload(io.BytesIO(log_content.encode('utf-8')), mimetype='text/plain')
        
        service.files().create(
            body={'name': filename, 'parents': [folder_id]},
            media_body=media,
            fields='id'
        ).execute()
        print(f"MEMÓRIA SALVA COM SUCESSO: {filename}")

    except Exception as e:
        print(f"FALHA NA GRAVAÇÃO DO DRIVE: {e}")

# --- 3. SISTEMA COGNITIVO (IA) ---

def get_gemini_response(prompt):
    # Lista de prioridade baseada nos seus logs
    # O 'gemini-flash-latest' apareceu como disponível no seu teste anterior
    models_to_try = [
        "models/gemini-1.5-flash", 
        "models/gemini-flash-latest",
        "gemini-1.5-flash"
    ]
    
    last_error = ""
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Tentativa com {model_name} falhou. Tentando próximo...")
            last_error = str(e)
            continue
            
    return f"Erro Crítico de IA: Não foi possível conectar a nenhum modelo. Detalhes: {last_error}"

def cognitive_router(msg):
    if api_key_deepseek and any(x in msg.lower() for x in ['código', 'python', 'lógica']):
        return "deepseek"
    return "gemini"

# --- 4. ROTAS ---
@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "online", "memory": "Active", "auth": "User Token"})

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "No message"}), 400
            
        user_msg = data['message']
        brain = cognitive_router(user_msg)
        
        response_text = ""
        source_tag = ""
        
        # Roteamento
        if brain == "gemini":
            response_text = get_gemini_response(user_msg)
            source_tag = "[Gemini]"
        else:
            # Fallback para Gemini se DeepSeek não estiver configurado
            response_text = get_gemini_response(user_msg)
            source_tag = "[Gemini]"

        # Salvar na Memória (Background)
        save_to_drive_log(user_msg, response_text)

        return jsonify({"response": response_text, "model": source_tag})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
