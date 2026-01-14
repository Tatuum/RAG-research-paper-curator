from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan for the API.
    """
    print("Starting up the API...")
    # Create database tables on startup
    from src.db.postgresql import Base, engine

    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables ready!")
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
