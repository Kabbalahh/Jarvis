import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# --- CONFIGURAÇÕES ---
# Escopo: Permissão para ler e criar arquivos
SCOPES = ['https://www.googleapis.com/auth/drive.file']
MEMORY_ROOT_NAME = "JARVIS_X_MEMORY"

def authenticate_drive():
    """Realiza a autenticação segura do usuário via Browser."""
    creds = None
    # O arquivo token.pickle armazena o acesso do usuário e é criado automaticamente após o primeiro login
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    # Se não houver credenciais válidas, faça o login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Requer o arquivo credentials.json (baixado do Google Cloud Console)
            if not os.path.exists('credentials.json'):
                print("ERRO: Arquivo 'credentials.json' não encontrado.")
                print("Por favor, baixe o JSON do OAuth 2.0 no Google Cloud Console.")
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Salva as credenciais para a próxima execução
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

def create_folder(service, folder_name, parent_id=None):
    """Cria uma pasta no Google Drive se ela não existir."""
    
    # 1. Verifica se a pasta já existe
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
        
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])

    if not items:
        # 2. Se não existe, cria
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
            
        folder = service.files().create(body=file_metadata, fields='id').execute()
        print(f"✅ Pasta Criada: {folder_name} (ID: {folder.get('id')})")
        return folder.get('id')
    else:
        # 3. Se existe, retorna o ID existente
        print(f"ℹ️ Pasta já existe: {folder_name}")
        return items[0]['id']

def main():
    print("--- INICIANDO PROTOCOLO DE MEMÓRIA FÍSICA ---")
    service = authenticate_drive()
    
    if not service:
        return

    # 1. Cria a Pasta Raiz (O "Cérebro" no Drive)
    root_id = create_folder(service, MEMORY_ROOT_NAME)

    # 2. Cria as Sub-regiões da Memória
    structure = [
        "01_Logs_Conversas",      # Memória Episódica (o que foi conversado)
        "02_Conhecimento_Base",   # Memória Semântica (fatos, PDFs, livros)
        "03_Preferencias_Usuario",# Memória de Personalização
        "04_Codigos_Python"       # Capacidade de auto-análise
    ]

    for subfolder in structure:
        create_folder(service, subfolder, root_id)

    print("\n--- ESTRUTURA DE MEMÓRIA CONCLUÍDA COM SUCESSO ---")
    print(f"Verifique seu Google Drive: Pasta '{MEMORY_ROOT_NAME}'")

if __name__ == '__main__':
    main()
