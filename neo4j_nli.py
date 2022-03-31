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


# class Word:
#     def __init__(self, token: spacy_Token):
#         self.token = token
#         self.dbMatch = None
#         self.type = "?"
#         # if self.word.pos_ in ["NOUN", "PROPN"]:
#         #     self.type = "N"  # TMP "N" should indicate NODE not NOUN!
#
#         # new
#         self.dbRole = None
#
#     def set_command(self, command: Command) -> None:
#         self.dbRole = command
#         self.type = "C"
#
#     def set_node(self, node: Node) -> None:
#         self.dbRole = node
#         self.type = "N"
#
#     def set_relationship(self, relationship: Relationship) -> None:
#         self.dbRole = relationship
#         self.type = "R"
#
#     def set_property(self, property: Property) -> None:
#         self.dbRole = property
#         self.type = "P"
#
#     def set_parameter(self, parameter: Parameter) -> None:
#         self.dbRole = parameter
#         self.type = "p"
#
#     def __str__(self):
#         return self.token.text
#
#     def __repr__(self):
#         return f"[{self.token.i} {self.token}]"


class Span:
    def __init__(self, span):
        self.span: spacy_Span = span
        self.spanL: Union[Span, None] = None
        self.spanR: Union[Span, None] = None

        self.match = None
        self.matchTried = False

        self.numNouns = 0
        for token in span:
            if token.pos_ in SPACY_NOUN_POS_TAGS:
                self.numNouns += 1

    def __len__(self):
        return len(self.span)

    def __str__(self):
        return self.span.text

    def __repr__(self):
        return self.span.text

    def get_match_char(self):
        if self.match: return self.match.visualisationChar
        else: return "?"


    @staticmethod
    def get_all_spans(span):
        all_spans = []

        if span.spanL and span.spanR:
            all_spans.extend(Span.get_all_spans(span.spanL))
            all_spans.extend(Span.get_all_spans(span.spanR))
        else:
            all_spans.append(span)
        # if span.span:
        #     all_spans.append(span)
        # else:
        #     all_spans.extend(Span.get_all_spans(span.spanL))
        #     all_spans.extend(Span.get_all_spans(span.spanR))
        return all_spans

    def split(self):
        if not self.span:
            #print("CANNOT SPLIT SPAN: NO SPAN TO SPLIT!")
            return False

        if len(self.span) < 2:
            #print("CANNOT SPLIT SPAN: SPAN LEN < 2")
            return False

        if len(self.span) == 2:
            span1 = self.span[:1]
            span2 = self.span[1:]
        else:
            root = self.span.root
            noun_index = []
            for token in self.span:
                noun_index.append(token.i)
            nii = noun_index.index(root.i)
            range1 = noun_index[:nii]
            range2 = noun_index[nii:]
            span1 = self.span.doc[range1[0]:range1[-1] + 1]
            span2 = self.span.doc[range2[0]:range2[-1] + 1]

        self.spanL = Span(span1)
        self.spanR = Span(span2)
        self.span = None
        return True


class Sentence:
    def __init__(self, doc: spacy_Doc):
        self.doc: spacy_Doc = doc
        self.spans: list[Span] = []

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
        for chunk in sentence_in_chunks:
            self.spans.append(Span(chunk))

    def get_all_spans(self):
        all_spans = []
        for span in self.spans:
            all_spans.extend(Span.get_all_spans(span))
        return all_spans

    def __str__(self):
        """Visualise sentence and it's components"""
        string = self.doc.text + "\n"

        all_spans = self.get_all_spans()

        for i, s in enumerate(all_spans):
            string += str(i) + ("_" * (len(s.span.text)))
        string += "\n"

        for s in all_spans:
            string += s.get_match_char() + ("_" * (len(s.span.text)))
        string += "\n"

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

    sentence = Sentence(doc)
    #
    # if command is not None:
    #     sentence.chunks[0].set_command(command)

    return sentence  # TODO mutliple sentences...


class Neo4JNLI:
    def __init__(self, database_uri: str, database_username: str, database_password: str):
        self.db = DBNeo4j(database_uri, database_username, database_password)
        #self.db = None  # to speed up init phase

    def find_match(self, target_span: spacy_Span, target_list: list[Union[Node, Relationship]]) -> Union[Command, Node, Relationship, Property, Parameter, None]:
        # 1. Check if matching a Command
        # for each in COMMANDS:
        #     print(each[0], "<-command?->", target_span.text.lower())
        #     if each[0] == target_span.text.lower():
        #         return Command(each[1])

        # 2. Check if matching a Node / Property
        similarity_matrix = []
        for each in target_list:
            similarity = target_span.similarity(each.namesReadable)
            if similarity >= NOUN_SIMILARITY_THRESHOLD:
                similarity_matrix.append(
                    {"similarity": similarity, "match": each, "match_prop": None}
                )

            for prop in each.properties:
                similarity = target_span.similarity(nlp(prop.name))
                if similarity >= NOUN_SIMILARITY_THRESHOLD:
                    similarity_matrix.append(
                        {"similarity": similarity, "match": each, "match_prop": prop}
                    )

        if len(similarity_matrix) > 0:
            best_match = similarity_matrix[0]
            if len(similarity_matrix) > 1:
                similarity_matrix.sort(key=lambda dic: dic["similarity"], reverse=True)

                # If top 2 choices equal, give priority to Node!  # TODO prompt user? Eg. "Is ... a property or a node?"
                if (similarity_matrix[0]["similarity"] == similarity_matrix[1]["similarity"]):
                    print("Equal similarity! Prioritising Node (last dict shown to the right)!", similarity_matrix[0], "<->", similarity_matrix[1])
                    if (similarity_matrix[1]["match_prop"] is None):
                        best_match = similarity_matrix[1]

            if best_match["match_prop"]: return best_match["match_prop"]
            elif best_match["match"]: return best_match["match"]

        # 3. Check if matching a Parameter
        parameter = self.find_parameter_in_db(target_span.text)
        if parameter:
            return parameter

        return None

    def find_parameter_in_db(self, parameter: str) -> Union[Parameter, None]:
        """Value is string"""
        query = f"""
MATCH (m) WHERE any(key in keys(m) WHERE m[key] =~ '(?i){parameter}')
RETURN DISTINCT REDUCE 
(values = [], key IN keys(m) | 
CASE
WHEN m[key] =~ '(?i){parameter}' THEN values + key
ELSE values
END
) AS property_names, labels(m) AS node_labels
        """
        result = self.db.query(query)
        if len(result) == 0:
            return None

        if len(result) > 1:
            # TODO Overall idea is to score each element with certain criteria:
            # 1. Priority to node with direct connection to prev/next node in sentence
            # 2. Priority to highest count (or lowest?)
            pass

        node_labels: list[str] = result[0]["node_labels"]
        property_names: list[str] = result[0]["property_names"]

        for node in self.db.schema.nodes:
            if node.label in node_labels:
                for prop in node.properties:
                    if prop.name in property_names:
                        return Parameter(parameter, prop)

        return None

    def find_command(self, target_span: spacy_Span) -> Union[Command, None]:
        for c in Command.translations:
            if c["text"] == target_span.text.lower():
                return Command(c)
        return None

    def run(self) -> None:
        queries = [
            "How many Cities?",
            "City",
            "How many Businesses that are Breweries are in Phoenix?",
            "How many stars does Mother Bunch Brewing have?",
            "How many businesses are in the category Breweries?",
        ]

        while queries:
            natural_language_query = queries.pop()
            sentence = process_text(natural_language_query)
            cypher_query = CypherQuery()
            while True:
                # Get all sub-spans
                all_spans = sentence.get_all_spans()

                did_change = False
                for each in all_spans:
                    # If match or failed to find a match, skip and leave for later evaluation (relationships...)
                    # ALso, if no nouns present in span, leave for later evaluation (relationships...)
                    if each.match or each.matchTried:
                        continue
                    each.matchTried = True

                    if each.numNouns < 1:
                        command = self.find_command(each.span)
                        if command:
                            each.match = command
                            continue
                    else:
                        match = self.find_match(each.span, self.db.schema.nodes)
                        if match:
                            each.match = match
                            continue

                    did_split = each.split()
                    if did_split:
                        did_change = True

                if not did_change:
                    break
            print(sentence)

    def close(self) -> None:
        if self.db: self.db.close()


if __name__ == "__main__":
    nli = Neo4JNLI("bolt://localhost:7687", "username", "password")
    nli.run()
    nli.close()