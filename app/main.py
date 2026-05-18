from fastapi import FastAPI

app = FastAPI(
    title="Laundry Service API",
    version="1.0.0",
    description="API for managing laundry services, including user authentication and order processing."
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Laundry Service API!"}