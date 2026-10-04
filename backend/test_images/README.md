# Pasta de Imagens de Teste

Coloque aqui os arquivos de imagem que você deseja testar no fluxo de reconhecimento facial (formatos suportados: `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`, `.avif`).

### Como processar essas imagens:
1. **Pela Interface Web (Recomendado)**:
   Acesse a tela administrativa em `http://localhost:3000/admin/processing` e clique no botão **"Importar Pasta de Testes"**, depois em **"Iniciar Processamento Agora"**.
2. **Via Terminal**:
   ```bash
   cd backend
   pipenv run python ingest_test.py
   ```
   E para processar:
   ```bash
   pipenv run python worker.py --once
   ```
