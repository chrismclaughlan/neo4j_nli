from spacy.tokens import Token as spacy_Token
from spacy.tokens.doc import Doc as spacy_Doc
from typing import Union
from config import nlp


def split_camel_case(word: spacy_Token) -> Union[list[str], None]:
    if word.is_lower or word.is_upper: return None

    merged_words: list[str] = []  # Will contain every each separated word

    words: list[str] = []
    text: str = word.text

    # Create new word for every capital letter found in word. Exception being words containing "."
    current_word: str = text[0]
    for letter in text[1:]:
        if not letter.istitle() or current_word[-1] == ".":
            current_word += letter
        else:
            words.append(current_word)
            current_word = letter
    words.append(current_word)

    if len(words) == 1:
        return None  # Occurs when eg. word == "What"

    # merge_capital_letters eg. ['handle', 'R', 'D', 'F', 'Types'] -> ['handle', 'RDF', 'Types']
    for word in words:
        has_previous_word = merged_words is not None
        current_word_is_single_capital = len(word) == 1 and word[0].istitle()

        if has_previous_word and current_word_is_single_capital:
            previous_word_ends_with_capital = merged_words[-1][-1].istitle()

            if previous_word_ends_with_capital:
                merged_words[-1] += word
                continue

        merged_words.append(word)

    return merged_words


def process_text(text: str) -> spacy_Doc:
    """Splits text into tokens"""
    doc: spacy_Doc = nlp(text)

    # Clean document - Split tokens that are formatted as camelCase
    with doc.retokenize() as retokeniser:
        # Split tokens from camelCase in doc
        for index, token in enumerate(doc):
            words = split_camel_case(token)
            if words:
                heads = []
                for i, word in enumerate(words):
                    heads.append( (token, i,) )
                retokeniser.split(token, words, heads=heads)

    return doc  # TODO mutliple sentences...
