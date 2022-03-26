from db_management_system.db_neo4j import DBNeo4j
from query_creator.cypher_query import CypherQuery
import config

nlp = config.nlp

# Translations from natural language phrase into CYPHER commands
COMMANDS = [
    (
        "how many", {"NODE": "COUNT", "PROP": "SUM"}
    ),
    (
        "highest", {"NODE": "ORDER BY % DESC", "PROP": "TODO"},  # TODO PROP: ... change!
    ),
    (
        "lowest", {"NODE": "ORDER BY", "PROP": "TODO"},  # TODO PROP: ... change!
    ),
    (
        "average", {"NODE": "AVG", "PROP": "TODO"},  # TODO PROP: ... change!
    )
]

NOUN_SIMILARITY_THRESHOLD = 0.75


class NounPhrase:
    def __init__(self, phrase):
        self.noun = phrase.root                                 # token
        self.nounType = self.noun.pos_                          # string
        self.context = phrase.text.replace(self.noun.text, "")  # string
        self.phrase = phrase                                    # span?

        self.command = ""
        for command in COMMANDS:
            if command[0] in self.context.lower():
                self.command = command[1]
                break

        # WIP
        self.phraseIsInstance = False
        self.nounIsInSchema = False

    def __str__(self): return self.phrase.text

    def __repr__(self):
        """Highlights noun in phrase as UPPERCASE"""
        return self.phrase.text.lower().replace(self.noun.text.lower(), self.noun.text.upper())


class Neo4JNLI:
    def __init__(self):
        self.db = DBNeo4j("bolt://localhost:7687", "neo4j", "password")

    def check_is_instance_name(self, text):
        query = f"MATCH (m) WHERE m.name =~ '(?i){text}' RETURN DISTINCT labels(m) AS node_types, COUNT(*) AS count"
        result = self.db.query(query)

        if len(result) == 0:
            return None

        node_types = result[0]["node_types"]
        if len(result) > 1:  # Priority to results with only one instance! More likely to be "Category name"...
            for each in result:
                if each["count"] == 1:  # TODO what if we get more than one in result that has count 1??
                    node_types = each["node_types"]

        # Check if node exists in database schema
        return next((n for n in self.db.schema["nodes"] if n.name in node_types), None)

    def run(self):
        while True:
            cypher_query = CypherQuery()

            # Get natural language input
            natural_language_query = "How many stars does Mother Bunch Brewing have?"
            natural_language_query = "Mother Bunch Brewing"
            natural_language_query = input("Enter natural language query: ")

            # Tokenise and process natural language text
            doc = nlp(natural_language_query)

            # Identify and collect noun phrases
            noun_phrases = []
            noun_chunks = list(doc.noun_chunks)
            for noun_chunk in noun_chunks:
                np = NounPhrase(noun_chunk)
                noun_phrases.append(np)

            print(noun_phrases)

            # Identify Nodes / Relationships / Attributes / Instances in noun phrases
            # 1. Check if whole phrase is itself an instance
            for index, phrase in enumerate(noun_phrases):
                node = self.check_is_instance_name(str(phrase))
                if node:
                    if index == 0:  # First phrase will include target noun ...
                        cypher_query.set_target_node(node, node_constraints={"name": str(phrase)})
                    else:
                        cypher_query.add_related_node(node, node_constraints={"name": str(phrase)})
                    phrase.phraseIsInstance = True

            # 2 Find nouns in database schema as nodes/relationships/attributes
            for index, phrase in enumerate(noun_phrases):  # TODO merge with prev. for...?

                if phrase.phraseIsInstance:
                    continue

                similarity_matrix = []
                for node in self.db.schema["nodes"]:
                    similarity = phrase.noun.similarity(node.namesReadable)
                    if similarity >= NOUN_SIMILARITY_THRESHOLD:
                        similarity_matrix.append(
                            {"type": "NODE", "phrase": phrase, "similarity": similarity, "node": node}
                        )

                    for prop in node.props:
                        similarity = phrase.noun.similarity(nlp(prop))
                        if similarity >= NOUN_SIMILARITY_THRESHOLD:
                            similarity_matrix.append(
                                {"type": "PROP", "phrase": phrase, "similarity": similarity, "node": node, "prop": prop}
                            )

                if len(similarity_matrix) == 0:
                    continue

                best_match = similarity_matrix[0]
                if len(similarity_matrix) > 1:
                    similarity_matrix.sort(key=lambda dic: dic["similarity"], reverse=True)

                    # If top 2 choices equal, give priority to Node!  # TODO prompt user? Eg. "Is ... a property or a node?"
                    if (similarity_matrix[0]["similarity"] == similarity_matrix[1]["similarity"]) \
                        and (similarity_matrix[1]["type"] == "NODE"):
                        best_match = similarity_matrix[1]

                target_prop = None
                if best_match["type"] == "PROP":
                    target_prop = best_match["prop"]

                if index == 0:  # First phrase will include target noun ...
                    cypher_query.set_target_node(best_match["node"], target_prop=target_prop)
                    if phrase.command:
                        cypher_query.set_return_command(phrase.command[best_match["type"]])
                else:
                    cypher_query.add_related_node(best_match["node"], target_prop=target_prop)
                phrase.nounIsInSchema = True

            # 3. Check if noun is itself an instance
            for index, phrase in enumerate(noun_phrases):  # TODO merge with prev. for...?

                # TODO command??

                # Only check phrases which have yet to be matched to an instance/node/edge/attribute
                if phrase.phraseIsInstance or phrase.nounIsInSchema:
                    continue

                name = phrase.noun.text
                node = self.check_is_instance_name(name)
                print("[3.] node", node)
                if node:
                    if index == 0:  # First phrase will include target noun ...
                        cypher_query.set_target_node(node, node_constraints={"name": name})
                        if phrase.command:
                            cypher_query.set_return_command(phrase.command["NODE"])
                    else:
                        cypher_query.add_related_node(node, node_constraints={"name": name})
                    phrase.phraseIsInstance = True

            # Automatic query construction done, do something with it.
            query = cypher_query.get_query()
            if query:
                print("query:", query)
                result = self.db.query(query)
                print("result:", result)

    def close(self):
        if self.db: self.db.close()


if __name__ == "__main__":
    nli = Neo4JNLI()
    nli.run()
    nli.close()