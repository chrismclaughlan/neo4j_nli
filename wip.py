from db_management_system.db_neo4j import DBNeo4j
import config

nlp = config.nlp


class CypherNode:
    def __init__(self, _label, target_prop=None, _constraints=None):
        self.label = _label
        self.targetProp = target_prop
        if _constraints is None:
            self.constraints = {}  # {'name': 'NAME', 'city': 'CITY'}
        else:
            self.constraints = _constraints

    def __repr__(self):
        constraints = ""

        for key, value in self.constraints.items():
            constraints += "{" + key + ":" + " '" + value + "'}"

        # for constraint in self.constraints:
        #     constraints += "{" + "CONSTAINT_KEY" + ":" + " '" + "CONSTAINT_VALUE" + "'}"  # TODO get key/value pairs from dict!
        return self.label + " " + constraints


class CypherRelationship:
    def __init__(self, _label, _constraints=None):
        self.label = _label
        if _constraints is None:
            self.constraints = {}
        else:
            self.constraints = _constraints

    # def __repr__(self):
    #     return ""


class CypherQuery:
    def __init__(self, target_node=None, related_nodes=None, return_command=""):
        self.targetNode = target_node
        if related_nodes is None:
            self.relatedNodes = []
        else:
            self.relatedNodes = related_nodes
        self.returnCommand = return_command

    # def __str__(self):
    #     return f"MATCH (m:{self.targetNode.label}) RETURN {self.returnCommand}(m)"

    def get_query(self):
        # assert(...) ... Make sure syntax is okay.

        if self.targetNode is None:
            print("No target node found, cannot execute query!")
            return None

        related_nodes = ""
        alphabet = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "y", "z"]
        target_alias = alphabet.pop()
        for node in self.relatedNodes:
            #related_nodes += f"-[:REVIEWS]->(:Review)"  # example TODO incorporate relations
            related_nodes += f"--({alphabet.pop()}:{node})"
        return_prop = target_alias
        if self.targetNode.targetProp:
            return_prop = target_alias + "." + self.targetNode.targetProp
        return f"MATCH ({target_alias}:{self.targetNode}){related_nodes} RETURN {self.returnCommand}({return_prop}) AS result"

    def set_target_node(self, node, target_prop=None, node_constraints=None):
        # assert...
        self.targetNode = CypherNode(node.name, target_prop, node_constraints)

    def add_related_node(self, node, target_prop=None, node_constraints=None):
        # assert...
        self.relatedNodes.append(CypherNode(node.name, target_prop, node_constraints))

    def set_return_command(self, command):
        # assert... if in suitable_commands = ["...", "...", ...]
        self.returnCommand = command


class Neo4JNLI:
    def __init__(self):
        self.db = None

    def _db_connect(self):
        self.db = DBNeo4j("bolt://localhost:7687", "username", "password")

    def process_nlq(self, text):
        return nlp(text)

    def get_noun_phrases(self, doc):
        return list(doc.noun_chunks)

    def get_noun_context(self, noun_phrases):
        noun_context = []

        for phrase in noun_phrases:
            noun = phrase.root
            context = phrase.text.replace(noun.text, "%")
            #context = nlp(context)  # TODO spans?
            noun_context.append( (noun, context, ) )

        return noun_context

    def run(self):
        """Event loop that processes user input"""
        self._db_connect()

        while True:

            # Aim: Fill cypherQuery and execute it.
            cypher_query = CypherQuery()

            #natural_language_query = "How many Businesses are in Phoenix?"  # MATCH (m:Business) WHERE m.city = "Phoenix" RETURN COUNT(m)
            #natural_language_query = "How many stars does Mother Bunch Brewing have?"  # TODO if we also include "does the BUSINESS Mother ..." we get a duplicate in the query!
            #                                                                                 handle duplicate nodes in query!
            #natural_language_query = "How many Cities?"
            natural_language_query = input("Enter natural language query:")

            doc = self.process_nlq(natural_language_query)
            print(natural_language_query)
            print(list(doc.noun_chunks))

            noun_phrases = self.get_noun_phrases(doc)
            noun_context = self.get_noun_context(noun_phrases)

            # 1. Query phrase directly, expect to fail most of the time.
            for phrase in noun_phrases:
                q = f"MATCH (m) WHERE m.name = '{phrase.text}' RETURN DISTINCT labels(m) AS node_types, COUNT(*) AS count"
                result = self.db.query(q)
                print("result=", result)

                if len(result) == 1:
                    node_name = result[0]["node_types"][0]  # TODO if more than one label! eg. ["User", "Person"]
                    print("FOUND NOUN_PHRASE AS INSTANCE", phrase.text, "<->", node_name)
                    node = next((x for x in self.db.schema["nodes"] if x.name == node_name), None)
                    if node:
                        cypher_query.add_related_node(node, node_constraints={"name": phrase.text})

                elif len(result) > 1:  # TODO TODO TODO
                    print("found multiple results, find unique one")
                    for each in result:
                        node_types = each["node_types"]
                        count = each["count"]
                        if count == 1:  # TODO what if we get more than one in result that has count 1??
                            print("FOUND NOUN_PHRASE AS ATTRIBUTE", phrase.text, "<->", node_types)

            # TODO DIFFERENT TRANSLATIONS FOR NODES / ATTRIBUTES!
            # eg. How many Breweries? (b:Breweries) RETURN COUNT(b)
            #     How many stars does "..." have? (b:Breweries)--(r:Review) RETURN SUM(r.stars) (sum???)

            # FORMATTEDAS (natural text, (node_command, prop_command),) where it is later decided whether to use node-/prop_command according to target node/prop
            commands = [
                ("how many", ("COUNT", "SUM")),
                ("highest", ("ORDER BY % DESC", "TODO"),),  # TODO how to format
                ("lowest", ("ORDER BY", "TODO"),),
                ("average", ("AVG", "TODO"),)
            ]
            similarity_threshold = 0.75
            # 2. Find in schema
            for each in noun_context:
                noun, context = each[0], each[1]
                #print(f"noun: '{noun}' (pos={noun.pos_}) context: '{context}'")

                # Check if noun is a node in db
                similarity_matrix = []
                for node in self.db.schema["nodes"]:
                    node_similarity = noun.similarity(node.namesReadable)
                    if node_similarity >= similarity_threshold:
                        similarity_matrix.append(("NODE", noun, node_similarity, node))

                    # similarity_score = noun.similarity(node.namesReadable)
                    # if similarity_score >= similarity_threshold:
                    #     print("FOUND", noun.pos_, "AS NODE", noun, "<->", node)

                    # If no match, check attributes
                    for prop in node.props:
                        prop_similarity = noun.similarity(nlp(prop))
                        if prop_similarity >= similarity_threshold:
                            similarity_matrix.append(("PROP", noun, prop_similarity, prop, node))

                        # similarity_score = noun.similarity(nlp(prop))
                        # if similarity_score >= similarity_threshold:
                        #     print("FOUND", noun.pos_, "AS ATTRIBUTE:", noun, "<->", node.namesReadable, prop, similarity_score)

                similarity_matrix.sort(key=lambda tup: tup[2], reverse=True)
                print(similarity_matrix)

                if len(similarity_matrix) == 0:
                    print("Could not find any matches in schema for", noun)

                    q = f"MATCH (m) WHERE m.name = '{noun}' RETURN DISTINCT labels(m) AS node_types, COUNT(*) AS count"
                    result = self.db.query(q)
                    print("result=", result)

                    continue

                # Check for commands
                found_command = ""
                for command in commands:
                    command_text, command_cypher = command[0], command[1]
                    if command_text in context.lower():
                        found_command = command_cypher
                        print("FOUND COMMAND IN CONTEXT", context, "<->", command_cypher)

                best_match = similarity_matrix[0]
                # If top 2 choices equal, give priority to Node!  # TODO prompt user? Eg. "Is ... a property or a node?"
                if (len(similarity_matrix) > 1) and (similarity_matrix[0][2] == similarity_matrix[1][2]) and (similarity_matrix[1][0] == "NODE"):
                    best_match = similarity_matrix[1]

                _type = best_match[0]
                _noun = best_match[1]
                _score = best_match[2]
                _matched_with = best_match[3]
                print("FOUND", noun.pos_, "AS", _type, _noun, "<->", _matched_with, _score)

                # Create CypherNode!
                if _type == "NODE":
                    print(_type, _noun, _score, _matched_with)
                    if found_command:
                        cypher_query.set_target_node(_matched_with)
                        cypher_query.set_return_command(found_command[0])
                    else:
                        cypher_query.add_related_node(_matched_with)
                elif _type == "PROP":
                    _node = best_match[4]
                    print("PROP:", _matched_with)
                    if found_command:
                        cypher_query.set_target_node(_node, target_prop=_matched_with)
                        cypher_query.set_return_command(found_command[1])
                    else:
                        cypher_query.add_related_node(_node, target_prop=_matched_with)

            # 3. If still not found match, search for only noun!
            # TODO mark if noun found or not. If not enter this case:
            # if ...
            # ...



            print()
            query = cypher_query.get_query()
            if query:
                print(query)
                result = self.db.query(query)
                print(result)


            # Check for nodes in nouns

            # Check for attributes in (proper) nouns

            # Check for relationships between nodes / nouns


            # DO SOMETHING
            # interpreter = NLInterpreter(self.db.schema)
            # TODO psuedo algo...
            # text = interpreter.process_text(...)
            # noun_phrases = interpreter.get_noun_phrases(...)
            # noun_context = interpreter.get_noun_context(...)
            #
            # if noun_context[0] is_command(...): ... eg "How many" -> "COUNT()"
            #
            # nouns, edges, attrs = [], [], []
            # nouns = interpreter.find_noun_in_schema(...)
            # for noun not in nouns:
            # ... use context to find noun as instance / attribute
            #
            # How to find edges? Look for words such as "in"?

            #interpreter.recognise_graph_components(query_nl)
            #keyConcepts, context = interpreter.identify_key_concepts(query_nl)

    def close(self):
        if self.db: self.db.close()


if __name__ == "__main__":
    nli = Neo4JNLI()
    nli.run()
    nli.close()
