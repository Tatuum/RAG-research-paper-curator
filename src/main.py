from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan for the API.
    """
    print("Starting up the API...")

    yield

    print("Shutting down the API...")
    # Cleanup
   


app = FastAPI(
    title="Scientific Paper Curator API",
    description="Personal scientific paper curator with RAG capabilities",
    version="0.1.0",
    lifespan=lifespan,
)

@app.get("/")
async def root():
    return {"message": "Hello World"}
