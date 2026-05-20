# laundry-service-backend

FastAPI + PostgreSQL + SQLAlchemy

## CMD TO RUN:

### Without Docker NATIVELY

`fastapi dev app/main.py`

### With Docker

Build and run:

`docker compose up --build`

Run next time after the image is already built:

`docker compose up`

Stop:

`docker compose down`

Equivalent manual command:

`docker run --env-file .env.docker --add-host=host.docker.internal:host-gateway -p 8000:8000 laundry-backend`

<hr>
Note: Have to make the .env and .env.docker from the .env.example file
