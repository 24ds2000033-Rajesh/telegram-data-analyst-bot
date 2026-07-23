from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "FastAPI is running on Vercel"}
