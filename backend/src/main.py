from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health", status_code=200)
async def health_check():
    """
    Returns an 'ok' message with a 200 status code to indicate the service is running.
    """
    return {"status": "ok"}