from fastapi import FastAPI
from app.routers.auth_router import router as auth_router

app = FastAPI(
    title="Laundry Service API",
    version="1.0.0",
    description="API for managing laundry services, including user authentication and order processing."
)

app.include_router(auth_router)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Laundry Service API!"}