from spacy.tokens.doc import Doc as spacy_Doc
from spacy.tokens import Token as spacy_Token
from typing import Union

#from interpreter.nl_interpreter import NLInterpreter
import config
nlp = config.nlp


# TODO merge with neo4j_nli.py process_text(...)
def split_camel_case(word: spacy_Token):
    """Takes as input type class spacey.tokens.token.Token
    Returns list of words (type=str) contained inside original word
    Returns None if not camelCase"""
    if word.is_lower or word.is_upper: return None  # fixes ["R", "E", "V", "E", "I", "W"]

    words = []  # Will contain every each separated word
    text = word.text

    # Create new word for every capital letter found in word. Exception being words containing "."
    current_word = text[0]
    for letter in text[1:]:
        if not letter.istitle() or current_word[-1] == ".":
            current_word += letter
        elif len(current_word) == 0:
            current_word = letter
        else:
            words.append(current_word)
            current_word = letter
    words.append(current_word)

    if len(words) == 1: return None  # Occurs when eg. word == "What"

    return words


def process_text(text: str) -> spacy_Doc:
    """Splits text into tokens"""
    doc = nlp(text)

    # Clean document - Split tokens that are formatted as camelCase
    with doc.retokenize() as retokeniser:
        for index, token in enumerate(doc):
            words = split_camel_case(token)
            if words:
                heads = []
                for i, word in enumerate(words):
                    heads.append((token, i,))
                retokeniser.split(token, words, heads=heads)

    return doc


class Command:

    # Translations from natural language phrase into CYPHER commands
    # TODO replace todos!
    translations = (
        {
            "text": "how many",
            "as_node": "COUNT",
            "as_prop": "SUM",
        },
        {
            "text": "highest",
            "as_node": "ORDER BY % DESC",
            "as_prop": "TODO",
        },
        {
            "text": "lowest",
            "as_node": "ORDER BY",
            "as_prop": "TODO",
        },
        {
            "text": "average",
            "as_node": "AVG",
            "as_prop": "TODO",
        },
    )

    def __init__(self, cypher_dict: dict):
        self.cypher_dict = cypher_dict
        self.visualisationChar = "C"

    def __str__(self): return str(self.cypher_dict)

    def __repr__(self): return str(self.cypher_dict)


class Property:
    def __init__(self, name: str, parent):
        self.name = name
        self.parent = parent
        self.visualisationChar = "P"

    def __str__(self): return self.name

    def __repr__(self): return self.name

    def __eq__(self, other):
        return self.parent == other.parent and self.name == other.name


class Parameter:
    def __init__(self, value: str, parent: Property):
        self.value = value
        self.parent = parent
        self.visualisationChar = "p"


class BaseClass:
    def __init__(self, name: str, props: list[Property] = None):
        self.properties = props if props is not None else []  # List of strings

        name_readable = ""
        for i, token in enumerate(process_text(name)):
            if not token.is_punct:
                if i == 0: name_readable += token.text.lower()
                else: name_readable += " " + token.text.lower()
        self.namesReadable: spacy_Doc = nlp(name_readable)

    def add_property(self, property_name: str) -> None:
        _property = Property(property_name, self)
        if _property not in self.properties:
            self.properties.append(_property)

    def get_property(self, name: str) -> Union[Property, None]:
        for prop in self.properties:
            if prop.name == name:
                return prop
        return None


class Node(BaseClass):
    def __init__(self, label: str, props: list[str] = None):
        self.label = label
        super().__init__(label, props)
        self.visualisationChar = "N"

    def __eq__(self, other):
        return isinstance(other, Node) and self.label == other.label

    def __repr__(self):
        # Format similar to CYPHER
        if not self.properties: return "(" + self.label + ")"

        props = ""
        for each in self.properties: props += "'" + str(each) + "', "
        props = props[:-2]

        return "(" + self.label + " {" + props + "})"


class Relationship(BaseClass):
    def __init__(self, type: str, source: str, target: str, props: list[str] = None):
        self.type = type
        super().__init__(type, props)
        self.visualisationChar = "R"
        
        self.nodeSource = source
        self.nodeTarget = target

    def __eq__(self, other):
        return isinstance(other, Relationship) and self.type == other.type

    def __repr__(self):
        # Format similar to CYPHER
        if not self.properties: return f"({self.nodeSource})-[:{self.type}]->({self.nodeTarget})"
        
        props = ""
        for each in self.properties: props += "'" + str(each) + "', "
        props = " {" + props[:-2] + "}"
        
        return f"({self.nodeSource})-[:{self.type}{props}]->({self.nodeTarget})"
