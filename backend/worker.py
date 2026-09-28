import time
import signal
import logging
import argparse
import traceback

from app import db
from app.face_service import FaceAnalysisEngine, process_image_batch

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Worker] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("worker")

running = True


def signal_handler(signum, frame):
    global running
    logger.info("Sinal de encerramento recebido. Finalizando worker graciosamente...")
    running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    parser = argparse.ArgumentParser(description="Worker de Reconhecimento Facial e Clusterização (DB Polling)")
    parser.add_argument("--interval", type=int, default=3, help="Intervalo de polling em segundos (default: 3)")
    parser.add_argument("--batch-size", type=int, default=10, help="Tamanho do lote de imagens por busca (default: 10)")
    parser.add_argument("--once", action="store_true", help="Executa apenas uma rodada de processamento e encerra")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Iniciando Worker de Reconhecimento Facial (DB Polling)")
    logger.info(f"Intervalo: {args.interval}s | Batch Size: {args.batch_size} | Modo Único: {args.once}")
    logger.info("=" * 60)

    # Inicializa o modelo de IA antecipadamente
    FaceAnalysisEngine.get_instance()

    while running:
        session = db.SessionLocal()
        try:
            processed = process_image_batch(session, batch_size=args.batch_size)
            if processed > 0:
                logger.info(f"Processamento concluído: {processed} imagem(ns) no lote.")
            if args.once:
                break
        except Exception as e:
            logger.error(f"Erro inesperado no loop do worker: {e}\n{traceback.format_exc()}")
        finally:
            session.close()

        time.sleep(args.interval)

    logger.info("Worker finalizado.")


if __name__ == "__main__":
    main()
