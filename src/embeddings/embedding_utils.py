import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import time 
from retrying import retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.llms.gpt_client import GPTClient
import pickle
import json 

# Define a custom wait strategy for retrying
def wait_exponential_multiplier():
    return 1000  # 1000 ms base wait time

def wait_exponential_max():
    return 10000  # 10000 ms max wait time

# Custom exception check function
def retry_on_any_exception(exception):
    print(f"An error occurred: {exception}")
    time.sleep(0.01)  # Wait for 0.01 seconds before retrying
    return True  # Always retry on any exception

@retry(stop_max_attempt_number=10, wait_exponential_multiplier=wait_exponential_multiplier(), wait_exponential_max=wait_exponential_max(), retry_on_exception=retry_on_any_exception)
def get_embedding(text, model="text-embedding-3-small"):
    embedding_client = GPTClient(model=model)
    if not text.strip():  # Ensure text is not empty or just whitespace
        raise ValueError("The text to be embedded is empty.")
    text = text.replace("\n", " ")
    embedding = embedding_client.get_embedding(text)
    if not embedding:  # Ensure embedding is not empty
        raise ValueError("The embedding is empty.")
    return embedding


def split_paragraphs(text):
    return text.split('\n\n')

def split_sentences(paragraph):
    import re
    # Split by sentence endings or new lines
    sentence_endings = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s|\n')
    return sentence_endings.split(paragraph)

# 目前不用
def process_embedding_document(text, embedding_file_path):
    paragraphs = split_paragraphs(text)
    sentence_embeddings = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for i, paragraph in enumerate(paragraphs):
            sentences = split_sentences(paragraph)
            for sentence in sentences:
                if sentence.strip():
                    futures.append(executor.submit(get_embedding_with_metadata, sentence, i, sentences))

        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    sentence_embeddings.append(result)
            except Exception as e:
                print(f"Failed to get embedding for a sentence. Error: {e}")

    with open(embedding_file_path, 'wb') as f:
        pickle.dump(sentence_embeddings, f)
    return sentence_embeddings

def get_embedding_with_metadata(sentence, paragraph_index, sentences):
    embedding = get_embedding(sentence)
    return {
        'paragraph_index': paragraph_index,
        'sentence': sentence,
        'sentences': sentences,
        'embedding': embedding
    }

# 目前按页拆的，用这个
def process_embedding_json(text_json_path, embedding_file_path):
    sentence_embeddings = []
    with open(text_json_path, "r", encoding='utf-8') as json_file:
        text_json = json.load(json_file)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for row in text_json:
            paragraph = row['full_text'] if 'full_text' in row else row['text']
            sentences = split_sentences(paragraph)
            for sentence in sentences:
                if sentence.strip():
                    futures.append(executor.submit(get_embedding_with_metadata_json, sentence, row, paragraph))

        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    sentence_embeddings.append(result)
            except Exception as e:
                print(f"Failed to get embedding for a sentence. Error: {e}")

    with open(embedding_file_path, 'wb') as f:
        pickle.dump(sentence_embeddings, f)
    print("document processing and embeddings generation completed.",embedding_file_path)
    return sentence_embeddings

def get_embedding_with_metadata_json(sentence, row, paragraph):
    embedding = get_embedding(sentence)
    return {
        'paragraph_index': row['page_num'],
        'sentence': sentence,
        'sentences': paragraph,
        'text_with_image_identifier': row['text'],
        'embedding': embedding
    }

def load_embeddings(file_path):
    with open(file_path, 'rb') as f:
        return pickle.load(f)

# sentence_embeddings = load_embeddings('embeddings.pkl')

def find_similar_paragraphs(query_sentence,embedding_path,top_n=5, threshold=0.6):
    print('prestart find_similar_paragraphs!',query_sentence)
    embeddings=load_embeddings(embedding_path)
    print('start find_similar_paragraphs!')
    query_embedding = get_embedding(query_sentence)
    similarities = []

    for item in embeddings:
        sentence_embedding = np.array(item['embedding'])
        similarity = cosine_similarity([query_embedding], [sentence_embedding])[0][0]
        if similarity >= threshold:
            similarities.append((similarity, item))

    similarities = sorted(similarities, key=lambda x: x[0], reverse=True)

    top_paragraphs = []
    seen_paragraphs = set()

    for similarity, item in similarities:
        paragraph_index = item['paragraph_index']
        if paragraph_index not in seen_paragraphs:
            top_paragraphs.append({
                'paragraph_index': paragraph_index,
                'sentence': item['sentence'],
                'similarity': similarity,
                'sentences': [embedding['sentence'] for embedding in embeddings if embedding['paragraph_index'] == paragraph_index],
                # 'text_with_image_identifier': [embedding['text_with_image_identifier'] for embedding in embeddings if embedding['paragraph_index'] == paragraph_index],
            })
            seen_paragraphs.add(paragraph_index)
        if len(top_paragraphs) >= top_n:
            break

    return top_paragraphs