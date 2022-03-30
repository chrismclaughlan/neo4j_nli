from spacy.tokens.doc import Doc as spacy_Doc
from spacy.tokens import Token as spacy_Token
from spacy.tokens.span import Span as spacy_Span
from typing import Union, Tuple

from db_management_system.db_neo4j import DBNeo4j
from db_management_system.types import Command, Node, Relationship, Property, Parameter
from query_creator.cypher_query import CypherQuery
import config

# # new imports
# from interpreter.nl_interpreter import NLInterpreter

nlp = config.nlp

# Translations from natural language phrase into CYPHER commands
# TODO replace todos!
COMMANDS = [
    (
        "how many", {"NODE": "COUNT", "PROP": "SUM"}
    ),
    (
        "highest", {"NODE": "ORDER BY % DESC", "PROP": "TODO"},
    ),
    (
        "lowest", {"NODE": "ORDER BY", "PROP": "TODO"},
    ),
    (
        "average", {"NODE": "AVG", "PROP": "TODO"},
    )
]

SPACY_NOUN_POS_TAGS = ["NOUN", "PROPN"]

NOUN_SIMILARITY_THRESHOLD = 0.75


# class NounPhrase:
#     def __init__(self, phrase):
#         self.noun = phrase.root                                 # token
#         self.nounType = self.noun.pos_                          # string
#         self.context = phrase.text.replace(self.noun.text, "")  # string
#         self.phrase = phrase                                    # span?
#
#         self.command = ""
#         for command in COMMANDS:
#             if command[0] in self.context.lower():
#                 self.command = command[1]
#                 break
#
#         # WIP
#         self.phraseIsInstance = False
#         self.nounIsInSchema = False
#
#     def __str__(self): return self.phrase.text
#
#     def __repr__(self):
#         """Highlights noun in phrase as UPPERCASE"""
#         return self.phrase.text.lower().replace(self.noun.text.lower(), self.noun.text.upper())


def split_camel_case(word: spacy_Token) -> Union[list, None]:
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


class Word:
    def __init__(self, token: spacy_Token):
        self.token = token
        self.dbMatch = None
        self.type = "?"
        # if self.word.pos_ in ["NOUN", "PROPN"]:
        #     self.type = "N"  # TMP "N" should indicate NODE not NOUN!

        # new
        self.dbRole = None

    def set_command(self, command: Command) -> None:
        self.dbRole = command
        self.type = "C"

    def set_node(self, node: Node) -> None:
        self.dbRole = node
        self.type = "N"

    def set_relationship(self, relationship: Relationship) -> None:
        self.dbRole = relationship
        self.type = "R"

    def set_property(self, property: Property) -> None:
        self.dbRole = property
        self.type = "P"

    def set_parameter(self, parameter: Parameter) -> None:
        self.dbRole = parameter
        self.type = "p"

    def __str__(self):
        return self.token.text

    def __repr__(self):
        return f"[{self.token.i} {self.token}]"


class SentenceChunk:
    def __init__(self, chunk: spacy_Span, chunk_index: int):
        self.index = chunk_index
        self.words = []

        self.nounIndex = None  # WARNING: is it possible to have more than one noun that wasn't merged in processing?
        for i, word in enumerate(chunk):
            w = Word(word)
            self.words.append(w)
            if chunk.root == word and chunk.root.pos_ in SPACY_NOUN_POS_TAGS:
                self.nounIndex = i

        #self.dbRole: Union[Node, Relationship, Property, Parameter, None] = None
        # TODO Place within words not chunk!

    def get_noun(self) -> Word:
        if self.nounIndex is None:
            raise Exception("WARNING CANNOT SET PROPERTY ON CHUNK WITHOUT NOUN")
        return self.words[self.nounIndex]

    def set_command(self, command: dict) -> None:
        self.words[command["idx_start"]].type = "C"
        self.command = command["cypher"]  # TODO

    # def set_property(self, property: Property) -> None:
    #     self.get_noun().type = "P"
    #     self.dbRole = property
    #
    # def set_parameter(self, something): pass  # TODO
    #
    # def set_rela_property(self, rela_labels: list, property) -> None:  # TODO property: Property?
    #     # self.get_noun().type = "R"
    #     # self.relationshipLabels = rela_labels
    #     # self.property = property
    #     pass
    #
    # def set_node(self, node: Node) -> None:
    #     self.get_noun().type = "N"
    #     self.dbRole = node
    #
    # def set_relationship(self, relationship: Relationship) -> None:
    #     pass

    def __str__(self):
        return str(self.words)  #" ".join([self.words.__str__()])

    def __repr__(self):
        return str(self.index) + str(self.words)


class Sentence:
    def __init__(self, doc: spacy_Doc):
        self.doc = doc
        self.chunks = []

        # Include non-noun chunks in chunks
        chunks = list(self.doc.noun_chunks)

        # Filter out unwanted noun phrases
        for each in chunks:
            if each.root.pos_ not in SPACY_NOUN_POS_TAGS: chunks.remove(each)

        assert(len(chunks) > 0)

        sentence_in_chunks = [chunks[0]]
        for index, chunk in enumerate(chunks[1:]):
            idx_this_start = chunk[0].i
            idx_prev_end = chunks[index][-1].i
            between_chunk = self.doc[idx_prev_end+1:idx_this_start]
            if between_chunk:
                sentence_in_chunks.append(between_chunk)
            sentence_in_chunks.append(chunk)

        for chunk_index, chunk in enumerate(sentence_in_chunks):
            self.chunks.append(SentenceChunk(chunk, chunk_index))

    def __str__(self):
        """Visualise sentence and it's components"""
        string = ""

        word_types = " " * (len(self.doc.text) + 1)
        chunk_idx = " " * (len(self.doc.text) + 1)
        for nc in self.chunks:
            for word in nc.words:
                idx_start = word.token.idx
                idx_end = word.token.idx + len(word.token)
                string_to_insert = word.type + ("_" * (idx_end - idx_start - 1))
                word_types = word_types[:idx_start] + string_to_insert + word_types[idx_end + 1:]

            idx_start = nc.words[0].token.idx
            idx_end = nc.words[-1].token.idx + len(nc.words[-1].token)
            number = str(nc.index)
            string_to_insert = number + "_" * (idx_end - idx_start - len(number))  # TODO bug here if len(number) > ...
            chunk_idx = chunk_idx[:idx_start] + string_to_insert + chunk_idx[idx_end+1:]

        string += "Chunks: " + str(self.chunks) + "\n"
        string += "Sentence     (doc): " + str(self.doc) + "\n"
        string += "Word Types (N/E/A): " + word_types + "\n"
        string += "Chunk Index       : " + chunk_idx + "\n"

        return string


def process_text(text: str) -> Sentence:
    """Splits text into tokens"""
    doc = nlp(text)

    # Clean document - Split tokens that are formatted as camelCase
    with doc.retokenize() as retokeniser:
        # if len(doc) > 1:

        # Split words with camelCase
        for index, token in enumerate(doc):
            words = split_camel_case(token)
            if words:
                heads = []
                for i, word in enumerate(words):
                    heads.append( (token, i,) )
                retokeniser.split(token, words, heads=heads)

        # Merge sequential nouns
        for noun_chunk in doc.noun_chunks:
            sequential_nouns = []
            for index, token in enumerate(noun_chunk):
                if token.pos_ in SPACY_NOUN_POS_TAGS:
                    sequential_nouns.append(token)
                else:  # If non-noun encountered in chunk, end sequential nouns
                    if sequential_nouns:
                        retokeniser.merge(doc[sequential_nouns[0].i:sequential_nouns[-1].i+1])
                    sequential_nouns = []
            if sequential_nouns:  # After iterating chunk, check if sequentual nouns encountered not ended mid-chunk
                retokeniser.merge(doc[sequential_nouns[0].i:sequential_nouns[-1].i + 1])

        # Get context from first noun chunk
        first_noun_chunk = list(doc.noun_chunks)[0]
        context_chunks = [[]]
        for index, word in enumerate(first_noun_chunk):
            if word.pos_ not in SPACY_NOUN_POS_TAGS:
                context_chunks[-1].append(word)
            elif index < len(first_noun_chunk) - 1:
                context_chunks.append([])
        # Find command in first noun chunk context and merge these into one token
        command = None
        for context_chunk in context_chunks:
            if command is not None: break  # There can only be one command! (?)
            text = " ".join(map(str, context_chunk))
            for each in COMMANDS:
                if each[0] in text.lower():
                    idx_start = context_chunk[0].i
                    idx_end = context_chunk[-1].i
                    retokeniser.merge(doc[idx_start:idx_end + 1])
                    command = {"idx_start": idx_start, "cypher": each[1]}
                    break

    sentence = Sentence(doc)

    if command is not None:
        sentence.chunks[0].set_command(command)

    return sentence  # TODO mutliple sentences...


class Neo4JNLI:
    def __init__(self, database_uri: str, database_username: str, database_password: str):
        self.db = DBNeo4j(database_uri, database_username, database_password)
        #self.db = None  # to speed up init phase

    @staticmethod
    def find_match(target_word: Word, target_list: list[Union[Node, Relationship]]) -> Union[Node, Relationship, Property, None]:
        best_match = None

        target_token = target_word.token

        similarity_matrix = []
        for each in target_list:
            similarity = target_token.similarity(each.namesReadable)
            if similarity >= NOUN_SIMILARITY_THRESHOLD:
                similarity_matrix.append(
                    {"similarity": similarity, "match": each, "match_prop": None}
                )

            for prop in each.properties:
                similarity = target_token.similarity(nlp(prop.name))
                if similarity >= NOUN_SIMILARITY_THRESHOLD:
                    similarity_matrix.append(
                        {"similarity": similarity, "match": each, "match_prop": prop}
                    )

        if len(similarity_matrix) > 0:
            best_match = similarity_matrix[0]
            if len(similarity_matrix) > 1:
                similarity_matrix.sort(key=lambda dic: dic["similarity"], reverse=True)

                # If top 2 choices equal, give priority to Node!  # TODO prompt user? Eg. "Is ... a property or a node?"
                if (similarity_matrix[0]["similarity"] == similarity_matrix[1]["similarity"]) \
                        and (similarity_matrix[1]["match_prop"] is not None):
                    best_match = similarity_matrix[1]

            if best_match["match_prop"]: return best_match["match_prop"]
            elif best_match["match"]: return best_match["match"]

        return None

    def find_property_value_in_db(self, value: str) -> Union[Tuple[dict, dict], Tuple[None, None]]:
        """Value is string"""
        query = f"""
WITH '{value}' AS property
MATCH (m) WHERE any(key in keys(m) WHERE m[key] = property)
RETURN DISTINCT REDUCE 
(values = [], key IN keys(m) | 
CASE
WHEN m[key] = property THEN values + key
ELSE values
END
) AS property_name, labels(m) AS node_labels
        """
        result = self.db.query(query)
        if len(result) == 0:
            return None, None

        if len(result) > 1:
            # TODO Overall idea is to score each element with certain criteria:
            # 1. Priority to node with direct connection to prev/next node in sentence
            # 2. Priority to highest count (or lowest?)
            pass

        property_name = result[0]["property_name"]
        node_labels = result[0]["node_labels"]

        valid_node_label = next((n for n in self.db.schema.nodes if n.label in node_labels), None)
        if not valid_node_label:
            return None, None

        # Check if node exists in database schema
        return node_labels, property_name

    def get_graph_components(self, sentence: Sentence) -> None:
        for index, chunk in enumerate(sentence.chunks):
            if chunk.nounIndex is not None:
                target_word: Word = chunk.get_noun()

                # 1. Find in db schema
                match = self.find_match(target_word, self.db.schema.nodes)
                if isinstance(match, Node):
                    target_word.set_node(match)
                elif isinstance(match, Property):
                    target_word.set_property(match)
                continue

                # 2. Find as/in db instance TODO
                # node_labels, property_name = self.find_property_value_in_db(str(target_word))
                # if node_labels and property_name:
                #     #print("FOUND TARGET WORD", target_word, "AS PROPERTY", property_name, "FOR NODE", node_labels)
                #     parameter = Parameter()
                #     chunk.set_parameter(parameter)

                # Check if attribute
                # MATCH (n) WHERE EXISTS(n.address) RETURN DISTINCT labels(n) AS node_types, COUNT(*) AS count
            else:
                # Check for relationships
                target_word: Word = chunk.words[0]  # TODO what goes here?

                # Check if in schema (Relationship)
                match = self.find_match(target_word, self.db.schema.relationships)
                if isinstance(match, Relationship):
                    target_word.set_relationship(match)
                elif isinstance(match, Property):
                    target_word.set_property(match)
                continue
                # TODO
                # if best_match:
                #     if best_match["match_prop"] is not None:
                #         print("FOUND RELATIONSHIP PROPERTY", chunk, target_word.text.upper())
                #     else:
                #         print("FOUND RELATIONSHIP", chunk, target_word.text.upper())
                #     continue

                # Check if relationship property value
                pass

    def run(self) -> None:
        queries = [
            "How many Businesses that are Breweries are in Phoenix?",
            "How many stars does Mother Bunch Brewing have?",
            "How many Cities?",
            "City",
            "How many businesses are in the category breweries?"
        ]

        while queries:
            cypher_query = CypherQuery()

            natural_language_query = queries.pop()

            # Process natural language text
            sentence = process_text(natural_language_query)
            self.get_graph_components(sentence)
            print(sentence)  # temp

            for chunk in sentence.chunks:
                pass

    def close(self) -> None:
        if self.db: self.db.close()


if __name__ == "__main__":
    nli = Neo4JNLI("bolt://localhost:7687", "username", "password")
    nli.run()
    nli.close()