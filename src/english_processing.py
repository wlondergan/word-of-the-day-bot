from nltk.stem.snowball import EnglishStemmer
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet

stemmer = EnglishStemmer()

def shortest_available_stem(word: str):
    return stemmer.stem(word)

def _tokenize_message(msg: str):
    try:
        return word_tokenize(msg)
    except:
        return msg.split(' ') #if the real human tokenizer fails, default to naive tokenization instead
    
def _real_english_word(word: str) -> bool:
    return len(wordnet.synsets(word.lower())) > 0
    
def get_word_of_the_day(msg: str) -> str | None:
    msg_tokens = _tokenize_message(msg)
    if len(msg_tokens) > 0:
        first_word = msg_tokens[0].lower()
        if (len(msg_tokens) == 1 or msg_tokens[1][0] == '(') and _real_english_word(first_word):
            return first_word
    return None