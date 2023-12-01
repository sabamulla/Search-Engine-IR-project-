import eel
import os
import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.metrics import edit_distance
import json
from nltk.metrics import edit_distance
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


eel.init("web")

# Define the directory where your 10 documents are located
document_directory = 'CharlesDarwinDataset/'


# Function to search for a keyword or sentence in the documents
@eel.expose
def search_documents(keyword):
    found_in_documents = []
    document_scores = {}

    for filename in os.listdir(document_directory):
        if filename.endswith('.txt'):
            file_path = os.path.join(document_directory, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                content_lower = content.lower()
                keyword_lower = keyword.lower()
                if keyword_lower in content_lower:
                    found_in_documents.append(filename)
                    # Calculate relevance score based on the number of keyword occurrences
                    relevance_score = content_lower.count(keyword_lower)
                    document_scores[filename] = relevance_score

    # Sort documents by relevance score and document ID
    sorted_documents = sorted(found_in_documents, key=lambda x: (-document_scores[x], x))

    return sorted_documents, document_scores


inverted_index = {}

@eel.expose  # Expose this function to JavaScript
def construct_inverted_index():
    
    global inverted_index
    # Loading NLTK resources
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('wordnet')

    # Data Loading
    folder_path = 'CharlesDarwinDataset/'
    documents = []
    doc_ids = []

    for idx, filename in enumerate(os.listdir(folder_path)):
        with open(os.path.join(folder_path, filename), 'r') as file:
            documents.append(file.read())
            doc_ids.append(idx)

    # Tokenization, Stopword Removal, Lemmatization
    lemmatizer = WordNetLemmatizer()
    stop_words = set(stopwords.words('english'))

    cleaned_documents = []
    for doc in documents:
        tokens = nltk.word_tokenize(doc)
        clean_tokens = [lemmatizer.lemmatize(token.lower()) for token in tokens if token.isalpha() and token.lower() not in stop_words]
        cleaned_documents.append(clean_tokens)

    # Inverted Index Construction
    inverted_index = {}
    for idx, doc_tokens in enumerate(cleaned_documents):
        for token in doc_tokens:
            if token in inverted_index:
                if idx not in inverted_index[token]['postings']:
                    inverted_index[token]['postings'].append(idx)
                    inverted_index[token]['doc_freq'] += 1
            else:
                inverted_index[token] = {'postings': [idx], 'doc_freq': 1}

    # Convert inverted index to a pandas DataFrame for tabular display
    index_data = []
    for token, values in inverted_index.items():
        doc_freq = values['doc_freq']
        postings = ', '.join(map(str, values['postings']))
        index_data.append([token, doc_freq, postings])

    index_df = pd.DataFrame(index_data, columns=['Tokens', 'Document Frequency', 'Postings'])


        
    return inverted_index, index_df.to_dict(orient='split') 


@eel.expose
def construct_bigram_index(inverted_index):
    bigram_index = {}  # Define the bigram_index dictionary

    for token in inverted_index.keys():
        bigrams = [token[i:i+2] for i in range(len(token) - 1)]
        for bigram in bigrams:
            if bigram in bigram_index:
                bigram_index[bigram].append(token)
            else:
                bigram_index[bigram] = [token]

    # Convert bigram index to a list of lists for tabular display
    bigram_index_data = []
    for bigram, tokens in bigram_index.items():
        tokens_str = ', '.join(tokens)
        bigram_index_data.append([bigram, tokens_str])

    # Sort bigram index data by bigram for consistent display
    bigram_index_data.sort(key=lambda x: x[0])

    return bigram_index_data  # Return as a list of lists


@eel.expose
def correct_spelling(query, vocabulary, num_neighbors=5):
    neighbors = []
    for term in vocabulary:
        distance = edit_distance(query, term)
        neighbors.append((term, distance))

    neighbors.sort(key=lambda x: x[1])
    corrected_query = neighbors[0][0]

    nearest_terms = neighbors[:num_neighbors]
    
    print(corrected_query)
    print(nearest_terms)
    
    return corrected_query, nearest_terms

permuterm_index={}

def generate_permuterm(term):
    permuterms = []
    term = term + "$"
    for i in range(len(term)):
        permuterms.append(term[i:] + term[:i])
    return permuterms

@eel.expose
def construct_permuterm_index():
    global permuterm_index
    
    permuterm_index = {}
    for token in inverted_index.keys():
        permuterms = generate_permuterm(token)
        for permuterm in permuterms:
            permuterm_index[permuterm] = token
    
    # Convert permuterm index to a list of tuples for easy transfer to JavaScript
    permuterm_list = [(permuterm, term) for permuterm, term in permuterm_index.items()]
    
    return permuterm_index, permuterm_list


@eel.expose
def query_permuterm(wildcard_query):
    
    permuterms = []
    wildcard_query = wildcard_query + "$"
    for i in range(len(wildcard_query)):
        permuterms.append(wildcard_query[i:] + wildcard_query[:i])
        wild_query = permuterms[i]
        if wild_query[-1] == "*":
            return wild_query

@eel.expose
def search_permuterm(wildcard_permuterm):
    # global permuterm_index
    
    # Remove the trailing wildcard character
    wildcard_permuterm = wildcard_permuterm[:len(wildcard_permuterm) - 1]

    querylen = len(wildcard_permuterm)
    documents = ["AnimalBehaviors.txt", "EmotionalStates.txt", "AnimalCommunication.txt", "ExpressionPrinciples.txt", "ExpressionPrinciplesConcluded.txt", "ExpressionPrinciplesContinued.txt", "HumanEmotions.txt", "InnerQualities.txt", "NegativeEmotions.txt", "PositiveEmotions.txt"]
    permutermKeys = permuterm_index.keys()

    matching_documents = []

    for token in permutermKeys:
        if wildcard_permuterm == token[:querylen]:
            if permuterm_index[token] in inverted_index:
                fileIndex = inverted_index[permuterm_index[token]]['postings']
                for i in fileIndex:
                    matching_documents.append({
                        "term": permuterm_index[token],
                        "document": documents[i]
                    })

    if matching_documents:
        return matching_documents
    else:
        return "Word not Found"

    return wildcard_permuterm


def create_soundex(name):
    name = name.upper()
    soundex = name[0]
    dictionary = {"BFPV": "1", "CGJKQSXZ": "2", "DT": "3", "L": "4", "MN": "5", "R": "6", "AEIOUHWY": "0"}

    for char in name[1:]:
        for key in dictionary.keys():
            if char in key:
                code = dictionary[key]
                if code != soundex[-1]:
                    soundex += code

    soundex = soundex.replace("0", "")
    soundex = soundex.ljust(4, "0")
    return soundex


# Expose Python function to JavaScript
@eel.expose
def search_soundex_term(term):
    term_soundex = create_soundex(term)
    print(term_soundex)
    
    text_dict = {}
    data = list(inverted_index.keys())  # Replace with your dataset

    for i in data:
        x = create_soundex(i)
        if x in text_dict:
            text_dict[x].append(i)
        else:
            text_dict[x] = [i]
    matching_words = text_dict.get(term_soundex, [])
    print(matching_words)
    return term_soundex, matching_words


@eel.expose
def calculate_cosine_similarity(query, directory):
    # Get a list of document file paths in the directory
    files = [os.path.join(directory, i) for i in os.listdir(directory)]

    # Read and preprocess the documents
    documents = []
    for file in files:
        with open(file, 'r') as f:
            text = f.read().lower()
            documents.append(text)

    # Create a TF-IDF vectorizer
    tfidf_vectorizer = TfidfVectorizer()

    # Compute the TF-IDF matrix for the documents
    tfidf_matrix = tfidf_vectorizer.fit_transform(documents)

    # Calculate the cosine similarity scores between the query and documents
    query_vector = tfidf_vectorizer.transform([query])
    cosine_scores = cosine_similarity(query_vector, tfidf_matrix)

    # Sort the documents by cosine similarity score in descending order
    sorted_indices = np.argsort(cosine_scores[0])[::-1]

    ranked_documents = []
    for rank, index in enumerate(sorted_indices):
        document_name = os.path.basename(files[index])
        score = cosine_scores[0][index]
        ranked_documents.append((rank + 1, document_name, score))

    return ranked_documents


@eel.expose
def perform_precision_recall(query):
    directory = "CharlesDarwinDataset"
    results = calculate_cosine_similarity(query, directory)
    return results


location = os.listdir('CharlesDarwinDataset/')
retrieved_documents = {}

# Read and preprocess the documents
for i in location:
    path = 'CharlesDarwinDataset/' + i
    with open(path, 'r', encoding='utf-8') as file:
        data = file.read().lower()
        data = data.replace('\n', ' ').replace('\t', ' ')
        retrieved_documents[i] = data

@eel.expose
def search_and_evaluate(query, relevant_documents):
    extras = ['!', '@', '#', '$', "%", "^", "&", "*", "(", ")", "<", ">", ",", ".", "[", "]", "{", "}", "_"]

    if any(char in query for char in extras):
        for char in extras:
            query = query.replace(char, '')

    all_retrieved_documents_names = []

    query_words = query.lower().split()

    for key, value in retrieved_documents.items():
        document_words = value
        if any(char in document_words for char in extras):
            for char in extras:
                document_words = document_words.replace(char, '')
        document_words = document_words.lower().split(" ")

        if all(word in document_words for word in query_words):
            all_retrieved_documents_names.append(key)

    def calculate_cosine_similarity(query_vector, document_vectors):
        similarity_scores = cosine_similarity(query_vector, document_vectors)
        return similarity_scores

    def evaluate_search_results(query, retrieved_documents, relevant_documents):
        vectorizer = TfidfVectorizer()
        vectorizer.fit(retrieved_documents + [query])
        query_vector = vectorizer.transform([query])
        document_vectors = vectorizer.transform(retrieved_documents)

        similarity_scores = calculate_cosine_similarity(query_vector, document_vectors)

        ranked_results = [doc for _, doc in sorted(zip(similarity_scores[0], retrieved_documents), reverse=True)]

        tp = len(set(ranked_results) & set(relevant_documents))
        fp = len(set(ranked_results) - set(relevant_documents))
        fn = len(set(relevant_documents) - set(ranked_results))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f_measure = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        print(f"Ranked Results: {ranked_results}")
        print(f"Precision: {precision}")
        print(f"Recall: {recall}")
        print(f"F-measure: {f_measure}")

        return ranked_results, precision, recall, f_measure

    return all_retrieved_documents_names,relevant_documents, evaluate_search_results(query, all_retrieved_documents_names, relevant_documents)





@eel.expose
def search(query):
    directory = "CharlesDarwinDataset"
    files = [os.path.join(directory, i) for i in os.listdir(directory)]
    documents = []

    for i in range(len(files)):
        with open(files[i], "r") as f1:
            data1 = f1.read().lower()
            documents.append(data1)

    relevant_indices = []  # Indices of relevant documents
    non_relevant_indices = []  # Indices of non-relevant documents

    feedback = [1, 2, -1, 3, -1, 4, 8, 1, -1, 0]
    relevant_doc = []
    non_relevant_doc = []

    for i in range(len(feedback)):
        if feedback[i] == -1:
            non_relevant_indices.append(i)  # Corrected
            non_relevant_doc.append(files[i])
        else:
            relevant_doc.append(files[i])
            relevant_indices.append(i)  # Corrected

    tfidf_vectorizer = TfidfVectorizer()
    tfidf_matrix = tfidf_vectorizer.fit_transform(documents)

    # Calculate the initial cosine similarity scores
    initial_similarity_scores = cosine_similarity(tfidf_vectorizer.transform([query]), tfidf_matrix)[0]

    alpha = 1.0
    beta = 0.75
    gamma = 0.15

    feedback_vector = (
        alpha * tfidf_vectorizer.transform([query]) +
        beta * np.mean(tfidf_matrix[relevant_indices], axis=0) -
        gamma * np.mean(tfidf_matrix[non_relevant_indices], axis=0)
    )

    feedback_vector = np.asarray(feedback_vector)

    updated_similarity_scores = cosine_similarity(feedback_vector, tfidf_matrix)[0]

    sorted_indices = np.argsort(updated_similarity_scores)[::-1]
    sorted_documents = [files[i] for i in sorted_indices]

    results = [f"Rank {i + 1}: {os.path.basename(doc)}" for i, doc in enumerate(sorted_documents[:10])]

    # Return the top 10 documents
    return results
# sorted_documents[:10]


# Start Eel with the web folder and your HTML file
eel.start("new.html", size=(1000, 600))

