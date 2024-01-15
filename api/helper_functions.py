import json
import os
import warnings

import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

# Load environment variables and set pandas options
load_dotenv()
warnings.filterwarnings('ignore')
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)
pd.set_option('display.max_colwidth', None)

# Set constants for environment variables
HARDCOVER_BEARER_TOKEN = os.getenv('HARDCOVER_BEARER_TOKEN')
BOOKBLEND_API_KEY = os.getenv("BOOKBLEND_API_KEY")

# API key header setup
api_key_header = APIKeyHeader(name="X-API-Key")

def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    if api_key_header == BOOKBLEND_API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="401: Invalid API Key",
    )


def get_goodreads_user_books_by_page(user, page_num=1):
    url = f'https://www.goodreads.com/review/list/{user}?page={page_num}'
    
    # Read the html table
    goodreads = pd.read_html(url, attrs={'id': 'books'}, extract_links='body', displayed_only=False)

    # Process the DataFrame
    user_books = goodreads[0]
    user_books = user_books[['title', 'author', 'pages', 'rating', 'ratings', 'pub', 'votes']]
    user_books['goodreads_id'] = user_books['title'].apply(lambda x: x[1]).str.extract(r'(\d+)')
    
    for column in user_books.columns[:-1]:
        user_books[column] = user_books[column].apply(lambda x: x[0])

    user_books['title'] = user_books['title'].apply(lambda x: x.replace('title ', '', 1))
    user_books['author'] = user_books['author'].apply(lambda x: x.replace('author ', '', 1)).apply(lambda x: x.replace(' *', '', 1))
    user_books['pages'] = pd.to_numeric(user_books['pages'].str.extract(r'(\d+)')[0], errors='coerce')
    user_books['rating'] = pd.to_numeric(user_books['rating'].str.extract(r'(\d+\.\d+)')[0], errors='coerce')
    user_books['ratings'] = pd.to_numeric(user_books['ratings'].str.replace(',', '').str.extract(r'(\d+)')[0], errors='coerce')
    
    # I just want "pub" to be the year. But, it can get crazy with a bunch of different date formats
    user_books['pub'] = user_books['pub'].apply(lambda x: x.replace('date pub ', '', 1))
    user_books['pub'] = pd.to_numeric(user_books['pub'].str.extract(r'(?:\b\d{1,2},\s)?(\d{1,4})\b')[0], errors='coerce')
    
    # So, the "votes" column is weird. It actually has a "# times read  x" value, which I am using to get the x value, then convert to a boolean
    user_books.rename(columns={'votes': 'read?'}, inplace=True)
    user_books['read?'] = pd.to_numeric(user_books['read?'].str.extract(r'(\d+)')[0], errors='coerce')
    user_books['read?'] = user_books['read?'] > 0

    return user_books

def get_all_goodreads_user_books(user):

    page_num = 1
    all_books_df = pd.DataFrame()

    while True:
        print(f'Fetching {user}\'s Page {page_num}...')
        books_on_page = get_goodreads_user_books_by_page(user, page_num)
        if books_on_page.empty:
            print(f'Page {page_num} is empty.')
            break
        all_books_df = pd.concat([all_books_df, books_on_page], ignore_index=True)
        page_num += 1

    return all_books_df

def get_genres_from_hardcover(goodreads_ids):
    url = "https://hardcover-production.hasura.app/v1/graphql"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {HARDCOVER_BEARER_TOKEN}'
    }
    
    # Convert the Series or list of IDs to the required string format
    ids_string = ', '.join(f'"{id_}"' for id_ in goodreads_ids)

    # Construct the GraphQL query
    query = f"""
    query GetBookByGoodreadsIDs {{
      book_mappings(
        where: {{platform: {{id: {{_eq: 1}}}}, external_id: {{_in: [{ids_string}]}}}}
      ) {{
        external_id
        book {{
          taggings {{
            tag {{
              tag
            }}
          }}
        }}
      }}
    }}
    """

    payload = json.dumps({"query": query, "variables": {}})
    response = requests.post(url, headers=headers, data=payload).json()

    books_json = response['data']['book_mappings']
    flattened_data = []

    # Iterate through each book entry in the JSON
    for entry in books_json:
        book_id = entry['external_id']
        
        # Flatten the taggings into a single string separated by commas
        tags = [tag['tag']['tag'] for tag in entry['book']['taggings']]
        
        # Append the flattened data to the list
        flattened_data.append({'external_id': book_id, 'tags': tags})

    genres_df = pd.DataFrame(flattened_data)

    return genres_df

def combine_goodreads_and_hardcover(goodreads_df, hardcover_df):
    return pd.merge(goodreads_df, hardcover_df, left_on='goodreads_id', right_on='external_id', how='left')
