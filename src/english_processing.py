from nltk.stem.snowball import EnglishStemmer
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet
import enchant

stemmer = EnglishStemmer()
d_us = enchant.Dict('en_US')
d_gb = enchant.Dict('en_GB')

def shortest_available_stem(word: str):
    return stemmer.stem(word)

def _tokenize_message(msg: str):
    try:
        return word_tokenize(msg)
    except:
        return msg.split(' ') #if the real human tokenizer fails, default to naive tokenization instead
    
def _real_english_word(word: str, blacklist, whitelist) -> bool:
    return word != '' and word not in blacklist and (d_us.check(word) or d_gb.check(word) or word in whitelist)

def is_word_candidate(msg: str) -> bool:
    msg_tokens = _tokenize_message(msg)
    return (len(msg_tokens) == 1 or msg_tokens[1][0] == '(')
    
def get_word_of_the_day(msg: str, blacklist, whitelist) -> str | None:
    msg_tokens = _tokenize_message(msg)
    if len(msg_tokens) > 0:
        first_word = msg_tokens[0].lower()
        if is_word_candidate(msg) and _real_english_word(first_word, blacklist, whitelist):
            return first_word
    return None