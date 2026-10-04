#!/bin/bash

# Cores para o terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Iniciando o Backend (FastAPI)...${NC}"
cd backend
pipenv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo -e "${BLUE}Iniciando o Face Recognition Worker (DB Polling)...${NC}"
pipenv run python worker.py --interval 3 &
WORKER_PID=$!
cd ..

echo -e "${GREEN}Iniciando o Frontend (Next.js)...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")

echo -e "\n======================================================="
echo -e "🚀 Serviços iniciados!"
echo -e "   - Backend:  http://localhost:8000 (Rede: http://${LOCAL_IP}:8000)"
echo -e "   - Worker:   Reconhecimento Facial Ativo (DB Polling)"
echo -e "   - Frontend: http://localhost:3000 (Rede: http://${LOCAL_IP}:3000)"
echo -e "   Pressione [CTRL+C] para encerrar todos os serviços."
echo -e "=======================================================\n"

# Quando o usuário apertar CTRL+C, finalizamos os processos
trap 'echo -e "\nEncerrando serviços..."; kill $BACKEND_PID $WORKER_PID $FRONTEND_PID 2>/dev/null; exit' SIGINT

# Aguarda os processos rodarem indefinidamente
wait
