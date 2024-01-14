from fastapi import FastAPI, Response
from api.helper_functions import get_all_goodreads_user_books

app = FastAPI()

@app.get("/api/python")
def hello_world():
    return {"message": "Hello World"}

@app.get("/api/books/{user}")
def get_user_books(user):
    books_json = get_all_goodreads_user_books(user)
    return Response(books_json, media_type="application/json")