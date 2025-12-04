import os
import datetime
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account

# --- 1. CONFIGURAÇÃO ---
load_dotenv()
api_key_google = os.getenv("GOOGLE_API_KEY")
api_key_deepseek = os.getenv("DEEPSEEK_API_KEY")

app = Flask(__name__)
CORS(app)

# Configuração Gemini
if api_key_google:
    genai.configure(api_key=api_key_google)

# --- 2. MEMÓRIA DRIVE (Service Account) ---
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    # Tenta achar o arquivo secreto em locais padrão do Render ou Raiz
    possible_paths = ["/etc/secrets/service_account.json", "service_account.json"]
    creds_path = next((p for p in possible_paths if os.path.exists(p)), None)

    if not creds_path:
        print("ALERTA MEMÓRIA: service_account.json não encontrado.")
        return None

    try:
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Erro na credencial: {e}")
        return None

def save_to_drive_log(user_msg, ai_response):
    service = get_drive_service()
    if not service: return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_content = f"[{timestamp}]\nUSER: {user_msg}\nJARVIS: {ai_response}\n{'-'*40}\n"

    try:
        # Busca pasta JARVIS_MEMORY
        query = "name = 'JARVIS_MEMORY' and mimeType = 'application/vnd.google-apps.folder'"
        results = service.files().list(q=query, spaces='drive').execute()
        items = results.get('files', [])
        
        if not items:
            print("Erro: Pasta JARVIS_MEMORY não encontrada (Verifique compartilhamento com email do robô).")
            return
            
        folder_id = items[0]['id']
        
        # Salva Arquivo
        from googleapiclient.http import MediaIoBaseUpload
        import io
        
        filename = f"Log_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        media = MediaIoBaseUpload(io.BytesIO(log_content.encode('utf-8')), mimetype='text/plain')
        
        service.files().create(
            body={'name': filename, 'parents': [folder_id]},
            media_body=media,
            fields='id'
        ).execute()
        print(f"MEMÓRIA SALVA: {filename}")
        
    except Exception as e:
        print(f"FALHA GRAVAÇÃO DRIVE: {e}")
        # Importante: Não paramos o código, apenas logamos o erro.

# --- 3. INTELIGÊNCIA (Modelo Ajustado) ---

def get_gemini_response(prompt):
    # LISTA ATUALIZADA COM BASE NO SEU LOG (04/Dez/2025)
    # Prioridade: Flash Latest (Rápido e Confirmado) -> Pro Latest -> Fallbacks
    priority_models = [
        "models/gemini-flash-latest", 
        "models/gemini-pro-latest",
        "models/gemini-1.5-flash",
        "gemini-1.5-flash"
    ]
    
    last_error = ""
    
    for model_name in priority_models:
        try:
            print(f"Tentando modelo: {model_name}...")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Falha no {model_name}. Tentando próximo...")
            last_error = str(e)
            continue
            
    return f"Erro Cognitivo Total. Detalhes: {last_error}"

def cognitive_router(msg):
    # Lógica simples para decidir entre DeepSeek e Gemini
    if api_key_deepseek and any(x in msg.lower() for x in ['código', 'python', 'lógica']):
        return "deepseek"
    return "gemini"

# --- 4. ROTAS ---
@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "online", "version": "v2.3 Fixed"})

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "No message"}), 400
            
        user_msg = data['message']
        brain = cognitive_router(user_msg)
        
        response_text = ""
        source = ""
        
        # Tentativa DeepSeek (Se configurado)
        if brain == "deepseek":
            # (Adicione sua lógica DeepSeek aqui se tiver a chave)
            # Fallback para Gemini se não tiver implementação
            brain = "gemini"

        # Execução Gemini
        if brain == "gemini":
            response_text = get_gemini_response(user_msg)
            source = "[Gemini]"

        # Salvar Memória (Em background, sem travar resposta)
        save_to_drive_log(user_msg, response_text)

        return jsonify({"response": response_text, "model": source})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
