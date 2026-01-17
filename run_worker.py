from app.ingestion.stream_worker import StreamWorker

if __name__ == "__main__":
    worker = StreamWorker()
    worker.run()
