from spacy.tokens.doc import Doc as spacy_Doc
from spacy.tokens import Token as spacy_Token
from typing import Union

#from interpreter.nl_interpreter import NLInterpreter
from processing import process_text
from config import nlp


VARIABLE_NAMES = [
    "aa", "bb", "cc", "dd"
]


def create_names_readable(text: str) -> spacy_Doc:
    name_readable = ""
    for i, token in enumerate(process_text(text)):
        if not token.is_punct:
            if i == 0:
                name_readable += token.text#.lower()
            else:
                name_readable += " " + token.text#.lower()

    r = nlp(name_readable)

    #print("BEFORE", text, "\nAFTER", r)

    return r


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
            "text": "how much",
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
    def __init__(self, name: str, parent: Union['Node', 'Relationship']):
        self.name: str = name
        self.parent: Node = parent
        self.visualisationChar: str = "P"
        self.namesReadable: spacy_Doc = create_names_readable(name)

    def __str__(self):
        return str(self.parent)
        # if isinstance(self.parent, Node):
        #     return f"({self.parent.label} {{{self.name}: '?'}})"
        # return self.name  # TODO relationships

    def __repr__(self): return self.name

    def __eq__(self, other):
        return self.parent == other.parent and self.name == other.name


class Parameter:
    def __init__(self, value: str, parent: Property):
        self.value = value
        self.parent = parent
        self.visualisationChar = "p"
        #self.namesReadable: spacy_Doc = create_names_readable(value)  # ??

    def __str__(self):
        if isinstance(self.parent.parent, Node):
            node = f"{self.parent.parent.variableName}:{self.parent.parent.label}"
            return f"({node} {{{self.parent.name}: '{self.value}'}})"
        return self.value  # TODO relationships


class BaseClass:
    def __init__(self, name: str, variable_name: str, props: list[Property] = None):
        self.properties = props if props is not None else []  # List of strings
        self.namesReadable = create_names_readable(name)
        self.variableName = variable_name

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
    def __init__(self, label: str, variable_name: str, props: list[str] = None):
        self.label = label
        super().__init__(label, variable_name, props)
        self.visualisationChar = "N"

    def __eq__(self, other):
        return isinstance(other, Node) and self.label == other.label

    def __repr__(self):
        # # Format similar to CYPHER
        # if not self.properties: return "(" + self.label + ")"
        #
        # props = ""
        # for each in self.properties: props += "'" + str(each) + "', "
        # props = props[:-2]
        #
        # return "(" + self.label + " {" + props + "})"
        return f"({self.variableName}:{self.label})"


class Relationship(BaseClass):
    def __init__(self, type: str, variable_name: str, source: str, target: str, props: list[str] = None):
        self.type = type
        super().__init__(type, variable_name, props)
        self.visualisationChar = "R"
        
        self.nodeSource = source
        self.nodeTarget = target

    def is_relationship_between(self, a: Union[Node, Property], b: Union[Node, Property]) \
        -> str:
        """If (first)->(second) return first; if (first)<-(second) return second; else None"""
        node_a: Node = a if isinstance(a, Node) else a.parent
        node_b: Node = b if isinstance(b, Node) else b.parent

        if self.nodeSource == node_a.label and self.nodeTarget == node_b.label:
            return "a"
        elif self.nodeSource == node_b.label and self.nodeTarget == node_a.label:
            return "b"
        return ""

    def __eq__(self, other):
        return isinstance(other, Relationship) and self.type == other.type

    def __repr__(self):
        # # Format similar to CYPHER
        # if not self.properties: return f"({self.nodeSource})-[:{self.type}]->({self.nodeTarget})"
        #
        # props = ""
        # for each in self.properties: props += "'" + str(each) + "', "
        # props = " {" + props[:-2] + "}"
        #
        # return f"({self.nodeSource})-[:{self.type}{props}]->({self.nodeTarget})"
        return f"[{self.variableName}:{self.type}]"


# TODO base class for all types/matches?
class Match:
    def __init__(self,
                 match: Union[Command, Node, Property, Parameter, Relationship],
                 confidence: float):
        self.match: Union[Command, Node, Property, Parameter, Relationship] = match
        self.confidence: float = confidence

    def __str__(self):
        return f"{self.match} <> {self.confidence}"

    def __repr__(self):
        return f"{self.match} <> {self.confidence}"
