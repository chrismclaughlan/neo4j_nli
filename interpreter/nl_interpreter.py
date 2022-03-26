import config

nlp = config.nlp


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


class NLInterpreter:
    def __init__(self, schema):
        self.schema = schema

    def noun_similarity_in_schema(self, noun):
        nodes = self.schema["nodes"]
        assert(type(nodes) == list)
        assert(len(nodes) > 1)

        similarity_matrix = []
        for each in nodes:  # NOUNS WONT REALLY BE EDGES/RELATIONSHIPS IN GRAPH SO ONLY ITERATE NODES
            #names_readable = " ".join(each.namesReadable)
            similarity = noun.similarity(each.namesReadable)  # TODO .LEMMA?
            similarity_matrix.append((each, similarity,))

        similarity_matrix.sort(key=lambda tup: tup[1], reverse=True)
        return similarity_matrix

        # threshold = 0.75
        # return similarity_matrix[0][1] >= threshold
        # else:
        #     # TODO Handle bad input! No bad code injections!
        #     # query(f"MATCH (node) WHERE node.name = '{text}'")
        #     # if found:
        #     # ... pass
        #     # else:
        #     # .... # try from similarity matrix?
        #     pass

        # print("closest 3 matches for:", noun)
        # print("#1 =", similarity_matrix[0])
        # print("#2 =", similarity_matrix[1])
        # print("#3 =", similarity_matrix[2])
        #
        # # TODO MATCH (m)--(City) WHERE m.name = "Breweries" RETURN m LIMIT 10 ????
        # # TODO
        # # OPTIONS:
        # # - Try find Node/Edge(/Attr?) that matches text exactly (from schema)
        # #   (similarity) 'Breweries' <-> 'Brewery': is threshold above 0.8? ...
        # # - Try find Node/Edge instance that matches text exactly (from db)
        # #   (Node) MATCH (m) WHERE m.name = "Breweries" RETURN m
        # #   (Rela) X not necessary I think but: MATCH (n)-[e]->(n2) WHERE type(e) = "WROTE_TIP" RETURN e LIMIT 1


    def is_command_phrase(self, text):
        """Checks whether text is a common phrase that can be translated to CYPHER,
        for example: 'How many' -> COUNT(...)."""
        return False

    def recognise_graph_components(self, text):
        n, e, a = [], [], []

        nodes, relationships = self.schema["nodes"], self.schema["relationships"]
        print(nodes)

        doc = self.process_text(text)

        print("noun chunks", list(doc.noun_chunks))

        # TODO change "key": ... to "index_of_noun": ... ? OR context = noun_chunk.replace(noun.text, "")
        #                                                     here question is how to remove noun from noun_chunk
        chunks = {"noun_phrases": [], "proper_noun_phrases": []}
        for noun_chunk in doc.noun_chunks:
            print("NOUN_CHUNK.ROOT", noun_chunk.root)
            if noun_chunk.root.pos_ == "NOUN":
                chunks["noun_phrases"].append({"key": noun_chunk.root, "context": noun_chunk})
            elif noun_chunk.root.pos_ == "PROPN":
                chunks["proper_noun_phrases"].append({"key": noun_chunk.root, "context": noun_chunk})
            else:
                print("WARNING COULD NOT RECOGNISE NOUN_CHUNK.ROOT.POS_", noun_chunk.root.pos_)

        # chunks["noun_phrases"].append({"key": nlp("cities"), "context": "WIP"})  # test
        # chunks["noun_phrases"].append({"key": nlp("reviews"), "context": "WIP"})  # test

        # newv

        # chunks = {
        #     "noun_phrases": [
        #         {"key": doc[2], "context": doc[0:1]}
        #     ],
        #     "proper_noun_phrases": [
        #         {"key": doc[5], "context": None}
        #     ],
        # }

        # chunks:
        # NOUN - ...
        # PROPN - Most likely an attribute!


        # GOAL: Find Nodes, Edges, Attributes in text
        nodes, edges, attributes = [], [], []

        for noun_chunk in chunks["noun_phrases"]:
            noun = noun_chunk["key"]
            context = noun_chunk["context"]
            # found = self.find_noun_in_schema(noun)

            # TODO Add command to accompany noun. Eg. "HOW MANY Breweries". Node: Breweries, Command: "COUNT()"
            # command_phrase = self.is_command_phrase("placeholder")
            # if command_phrase:
            #     # command_phrase contains cypher command (eg. COUNT(...) for "How many")
            #     pass

            similarity = self.noun_similarity_in_schema(noun)
            threshold = 0.75
            if similarity[0][1] >= threshold:
                # Noun "found" in schema. Mark it as Node.
                print("Found node:", similarity[0][0])
                nodes.append(similarity[0][0])
            else:
                # use context...
                print("Could not find node, looking for instance/edge/attribute", "noun:", noun, "context:", context)

                # Search schema for context!
                # ...
                # Search in db for context!
                # eg. MATCH (unknown_node {name: <CONTEXT>}) RETURN unknown_node
                pass

        for proper_noun_chunk in chunks["proper_noun_phrases"]:
            noun = proper_noun_chunk["key"]
            # context = proper_noun_chunk["context"]
            # found = self.find_noun_in_schema(noun)





        # Try make sense of "possible_attributes" ...
        # 1. for each attr in schema: doc.similarity(each). Sort to highest.
        # 2. Find common phrases such as "highest" ... and their conversion to CYPHER
        # 3. Split phrase into smaller pieces and repeat from step 1.

        not_matched = [
            {"NOUN/PROPN": "Breweries"}, {"possible_attributes": "near me"},
        ]
        # ... use similarity score to match with highest similar node/edge/attr from schema,
        #     if above threshold, otherwise prompt user ...

        from_root = []

        # print("sentences")
        # sentences = list(doc.sents)
        # for sent in sentences:
        #     root_token = sent.root
        #     print("root_token", root_token, root_token.dep_)
        #     from_root.append(root_token.text)
        #     for child in root_token.children:
        #         print(child, child.dep_)
        #         from_root.append(child.text)

        # print("\n\n\n")
        # for tIndex, token in enumerate(doc):
        #     if token.text in from_root:
        #         print(tIndex, token.text, token.dep_, token.pos_)
        # print("\n\n\n")

        #spacy.displacy.serve(doc, style="dep")

        # print("doc[3]=", doc[3].text)
        # print("doc[3]=", list(doc[3].children))
        #
        # base = nlp("like")
        # comparisons = [
        #     nlp("id"),
        #     nlp("name"),
        #     nlp("wrote"),
        #     nlp("similar"),
        #     nlp("wrote tip"),
        #     nlp("review"),
        # ]
        # for each in comparisons:
        #     print(base, "<->", each, base.similarity(each))



        # new^

        for tIndex, token in enumerate(doc):
            print(tIndex, token, token.pos_)
            # if not token.is_stop and token.pos_ != "PUNCT":
            #     print(tIndex, token, token.pos_)
            # else:
            #     print(tIndex)

            # for each in nodes + relationships:
            #     if each.name.lower() == token.text.lower():
            #         print("MATCH", each.name, "==", token.text)


        return n, e, a


    def identify_key_concepts(self, natural_language_query):
        """Compare doc tokens with that of nodes/relationships/attributes from db"""
        key_concepts = []
        context = []

        doc = self.process_text(natural_language_query)

        # Find Key Concepts -
        for tIndex, token in enumerate(doc):
            print(tIndex, token)

        # Collect Context -

        return key_concepts, context

    @staticmethod
    def process_text(text):
        """Splits text into tokens"""
        doc = nlp(text)

        # Clean document - Split tokens that are formatted as camelCase
        with doc.retokenize() as retokeniser:
            # if len(doc) > 1:
                for index, token in enumerate(doc):
                    words = split_camel_case(token)
                    if words:
                        heads = []
                        for i, word in enumerate(words):
                            heads.append( (token, i,) )
                        retokeniser.split(token, words, heads=heads)

        return doc