# ExamGuard Team 3 — Kafka + Docker setup (Windows)

This adds an optional Kafka transport to the existing Team 3 project. The existing JSONL event store, audit service, integrity summary, and tests remain in place.

## 1. Requirements
- Docker Desktop installed and running.
- Python 3.10+ installed.
- VS Code terminal opened in the `examguard_team3` project root.

## 2. Start Kafka
In PowerShell, from the folder containing `docker-compose.yml`:

```powershell
docker compose up -d
docker compose ps
docker compose logs -f kafka
```

Wait for Kafka to finish starting. Press `Ctrl+C` to stop viewing logs (this does not stop Kafka).

## 3. Install Python dependency
Use the same Python interpreter you use for the project:

```powershell
python -m pip install -r requirements.txt
```

## 4. Create the Kafka topic
Run this from the project root:

```powershell
docker exec examguard-kafka /opt/kafka/bin/kafka-topics.sh --create --if-not-exists --topic exam-events --bootstrap-server localhost:9092
```

Check the topic:

```powershell
docker exec examguard-kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
```

Expected topic name: `exam-events`.

## 5. Start the consumer first
Open Terminal 1 in VS Code (project root):

```powershell
python -m examguard.kafka_consumer
```

Leave it running. It listens for events and saves validated events to `data/kafka_received_events.jsonl`.

## 6. Send a test event
Open Terminal 2 in VS Code (same project root):

```powershell
python -m examguard.kafka_producer
```

The producer sends a schema-validated `FACE_ABSENT` mock event. Terminal 1 should print that it received and saved the event.

Note: the consumer uses a Kafka consumer group and commits offsets. For repeated tests, the newly sent event should appear while the consumer is running. If you restart the consumer, it normally resumes from the group's last committed offset.

## 7. Run the original project demo
From the project root:

```powershell
python main.py
```

To clear previous JSONL demo data before running (this deletes `data/events.jsonl` and `data/audit.jsonl`):

```powershell
python main.py --reset
```

Do not use `--reset` if you need to keep existing demo records.

## 8. Run automated tests

```powershell
python -m unittest discover -s tests -v
```

## 9. Stop Kafka
When finished:

```powershell
docker compose down
```

This stops and removes the container but does not delete the source files. To remove Kafka's stored data as well, a persistent Docker volume would need to be configured; this demo currently uses the container's own storage.

## Troubleshooting

- **`docker` is not recognized:** install Docker Desktop and reopen PowerShell/VS Code.
- **Cannot connect to Docker:** start Docker Desktop and wait until its engine is running.
- **Connection refused at `localhost:9092`:** check `docker compose ps` and `docker compose logs kafka`; wait for Kafka startup.
- **`NoBrokersAvailable`:** Kafka may still be starting, or Docker is not running.
- **`No module named kafka`:** run `python -m pip install -r requirements.txt`.
- **`No module named examguard`:** run commands from the project root (`examguard_team3`), not from inside the `examguard` folder.
- **Port 9092 is already allocated:** stop the other service using port 9092 before starting this compose stack.

## What the new files do
- `docker-compose.yml`: starts a single-node Kafka broker in Docker for local development.
- `requirements.txt`: declares the Python Kafka client dependency.
- `examguard/kafka_producer.py`: creates a valid mock `IntegrityEvent` and publishes it to `exam-events`.
- `examguard/kafka_consumer.py`: reads messages, validates them against the project's `IntegrityEvent` model, and stores accepted messages in `data/kafka_received_events.jsonl`.
- `data/kafka_received_events.jsonl`: generated output file; it appears after the first message is received.

This is a local development demo, not a production-secure Kafka deployment. It uses plaintext listeners and mock examination events.
