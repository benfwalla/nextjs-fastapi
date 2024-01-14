import pandas as pd
import warnings
from dotenv import load_dotenv
import os

load_dotenv()
hardcover_bearer_token = os.getenv('HARDCOVER_BEARER_TOKEN')

warnings.filterwarnings('ignore')

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)
pd.set_option('display.max_colwidth', None)

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

    return all_books_df.to_json(orient='records')
