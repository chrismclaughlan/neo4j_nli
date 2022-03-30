from db_management_system.db_neo4j import DBNeo4j
from query_creator.cypher_query import CypherQuery
import config

# new imports
from interpreter.nl_interpreter import NLInterpreter

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


def split_camel_case(word):
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


def process_text(text):
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


class Word:
    def __init__(self, word):
        self.word = word
        self.type = "?"
        # if self.word.pos_ in ["NOUN", "PROPN"]:
        #     self.type = "N"  # TMP "N" should indicate NODE not NOUN!

    def __str__(self):
        return self.word.text

    def __repr__(self):
        return f"[{self.word.i} {self.word}]"


class SentenceChunk:
    def __init__(self, chunk, chunk_index):
        self.index = chunk_index
        self.words = []

        self.nounIndex = None  # WARNING: is it possible to have more than one noun that wasn't merged in processing?
        for i, word in enumerate(chunk):
            w = Word(word)
            self.words.append(w)
            if chunk.root == word and chunk.root.pos_ in SPACY_NOUN_POS_TAGS:
                self.nounIndex = i

        self.command = None
        self.nodeLabels = None
        self.relationship = None
        self.property = None

        # TODO Nodes, Relationships, (Node-/Relationship) Properties, (Node-/Relationship) Parameters

    def get_noun(self):
        if self.nounIndex is None:
            raise Exception("WARNING CANNOT SET PROPERTY ON CHUNK WITHOUT NOUN")
        return self.words[self.nounIndex]

    def set_command(self, command):
        self.words[command["idx_start"]].type = "C"
        self.command = command["cypher"]

    def set_node_property(self, node_labels, property):
        assert(type(node_labels == list))
        self.get_noun().type = "P"
        self.nodeLabels = node_labels
        self.property = property

    def set_rela_property(self, rela_labels, property):
        assert(type(rela_labels) == list)
        # self.get_noun().type = "R"
        # self.relationshipLabels = rela_labels
        # self.property = property

    def set_node(self, node_labels):
        assert(type(node_labels == list))
        self.get_noun().type = "N"
        self.nodeLabels = node_labels

    def __str__(self):
        return str(self.words)  #" ".join([self.words.__str__()])

    def __repr__(self):
        return str(self.index) + str(self.words)


class Sentence:
    def __init__(self, doc):
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
                idx_start = word.word.idx
                idx_end = word.word.idx + len(word.word)
                string_to_insert = word.type + ("_" * (idx_end - idx_start - 1))
                word_types = word_types[:idx_start] + string_to_insert + word_types[idx_end + 1:]

            idx_start = nc.words[0].word.idx
            idx_end = nc.words[-1].word.idx + len(nc.words[-1].word)
            number = str(nc.index)
            string_to_insert = number + "_" * (idx_end - idx_start - len(number))  # TODO bug here if len(number) > ...
            chunk_idx = chunk_idx[:idx_start] + string_to_insert + chunk_idx[idx_end+1:]

        string += "Chunks: " + str(self.chunks) + "\n"
        string += "Sentence     (doc): " + str(self.doc) + "\n"
        string += "Word Types (N/E/A): " + word_types + "\n"
        string += "Chunk Index       : " + chunk_idx + "\n"

        return string


class Neo4JNLI:
    def __init__(self, database_uri, database_username, database_password):
        self.db = DBNeo4j(database_uri, database_username, database_password)
        #self.db = None  # to speed up init phase

    def find_match_in_db_schema(self, target_word, target_type):
        best_match = None

        similarity_matrix = []
        for each in self.db.schema[target_type]:
            similarity = target_word.similarity(each.namesReadable)
            if similarity >= NOUN_SIMILARITY_THRESHOLD:
                similarity_matrix.append(
                    {"similarity": similarity, "match": each, "match_prop": None}
                )

            for prop in each.props:
                similarity = target_word.similarity(nlp(prop))
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
        return best_match

    def find_property_value_in_db(self, value):
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

        valid_node_label = next((n for n in self.db.schema["nodes"] if n.name in node_labels), None)
        if not valid_node_label:
            return None, None

        # Check if node exists in database schema
        return node_labels, property_name

    def get_graph_components(self, sentence):
        for index, chunk in enumerate(sentence.chunks):
            if chunk.nounIndex is not None:
                target_word = chunk.get_noun().word

                # 1. Find in db schema
                best_match = self.find_match_in_db_schema(target_word, target_type="nodes")
                if best_match:
                    if best_match["match_prop"] is not None:
                        chunk.set_node_property([best_match["match"]], best_match["match_prop"])
                    else:
                        chunk.set_node([best_match["match"]])
                    continue

                # 2. Find as/in db instance
                node_labels, property_name = self.find_property_value_in_db(target_word)
                if node_labels and property_name:
                    #print("FOUND TARGET WORD", target_word, "AS PROPERTY", property_name, "FOR NODE", node_labels)
                    chunk.set_node_property(node_labels, property_name)

                # Check if attribute
                # MATCH (n) WHERE EXISTS(n.address) RETURN DISTINCT labels(n) AS node_types, COUNT(*) AS count
            else:
                # Check for relationships
                target_word = chunk.words[0].word  # TODO what goes here?
                print("Checking chunk for relationships:", chunk)

                # Check if in schema (Relationship)
                best_match = self.find_match_in_db_schema(target_word, target_type="relationships")
                if best_match:
                    if best_match["match_prop"] is not None:
                        print("FOUND RELATIONSHIP PROPERTY", chunk, target_word.word.upper())
                    else:
                        print("FOUND RELATIONSHIP", chunk, target_word.word.upper())
                    continue

                # Check if relationship property value
                pass

    def run(self):
        queries = [
            "How many Businesses that are Breweries are in Phoenix?",
            "How many stars does Mother Bunch Brewing have?",
            "How many Cities?",
            "City"
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

    def close(self):
        if self.db: self.db.close()


if __name__ == "__main__":
    nli = Neo4JNLI("bolt://localhost:7687", "username", "password")
    nli.run()
    nli.close()