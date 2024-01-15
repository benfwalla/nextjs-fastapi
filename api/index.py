from fastapi import FastAPI, Response, Security
from api.helper_functions import (combine_goodreads_and_hardcover, 
                                  get_all_goodreads_user_books, 
                                  get_api_key, 
                                  get_genres_from_hardcover)

app = FastAPI()

@app.get("/api/python")
def hello_world(api_key: str = Security(get_api_key)):
    return {"message": "Hello World"}

@app.get("/api/books/{user}")
def get_user_books(user, api_key: str = Security(get_api_key)):
    # Ben Walace's Goodreads user ID is 42944663
    print(f"Collecting Goodreads Books for {user}...")
    goodreads_df = get_all_goodreads_user_books(user)
    goodreads_ids = goodreads_df['goodreads_id']

    print(f"Collecting Hardcover genres for {user}'s books...")
    hardcover_df = get_genres_from_hardcover(goodreads_ids)

    print(f"Combining Goodreads DF and Hardcover DF for {user}...")
    combined_df = combine_goodreads_and_hardcover(goodreads_df, hardcover_df)
    books_json = combined_df.to_json(orient='records')

    return Response(books_json, media_type="application/json")