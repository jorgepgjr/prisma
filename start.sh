#!/bin/bash

# Cores para o terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Iniciando o Backend (FastAPI)...${NC}"
cd backend
pipenv run uvicorn app.main:app --reload &
BACKEND_PID=$!
cd ..

echo -e "${GREEN}Iniciando o Frontend (Next.js)...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "\n======================================================="
echo -e "🚀 Serviços iniciados!"
echo -e "   - Backend: http://localhost:8000"
echo -e "   - Frontend: http://localhost:3000"
echo -e "   Pressione [CTRL+C] para encerrar ambos os serviços."
echo -e "=======================================================\n"

# Quando o usuário apertar CTRL+C, finalizamos os dois processos
trap 'echo -e "\nEncerrando serviços..."; kill $BACKEND_PID $FRONTEND_PID; exit' SIGINT

# Aguarda os processos rodarem indefinidamente
wait
