from fastapi import FastAPI

@app.get("/api/python")
def hello_world():
    return {"message": "Hello World"}