from exception import Neo4jNLIException
from db_management_system.db_neo4j import DBNeo4j
from user_interfaces.user_interface import UserInterface
from interpreter.nl_interpreter import NLInterpreter


# test. TODO place in db_neo4j.py and import it
class CypherNode:
    def __init__(self, _label, _constraints=None):
        self.label = _label
        if _constraints is None:
            self.constraints = {}  # {'name': 'NAME', 'city': 'CITY'}
        else:
            self.constraints = _constraints

    def __repr__(self):
        constraints = ""
        for constraint in self.constraints:
            constraints += "{" + "CONSTAINT_KEY" + ":" + " '" + "CONSTAINT_VALUE" + "'}"  # TODO get key/value pairs from dict!
        return self.label + " " + constraints


class CypherRelationship:
    def __init__(self, _label, _constraints):
        self.label = _label
        if _constraints is None:
            self.constraints = {}
        else:
            self.constraints = _constraints

    def __repr__(self):
        return ""


class CypherQuery:
    def __init__(self, target_node=None, related_nodes=None, return_command=""):
        self.targetNode = target_node
        if related_nodes is None:
            self.relatedNodes = []
        else:
            self.relatedNodes = related_nodes
        self.returnCommand = return_command

    def get_query(self):
        # assert(...) ... Make sure syntax is okay.
        related_nodes = ""
        for node in self.relatedNodes:
            related_nodes = f"-[:REVIEWS]->(:Review)"  # example TODO
        return f"MATCH (m:{self.targetNode}){related_nodes} RETURN {self.returnCommand} m"

    def set_target_node(self, node_name, node_constraints):
        # assert...
        pass

    def add_other_node(self, node_name, node_constraints):
        # assert...
        pass

    def set_return_command(self, command):
        # assert... if in suitable_commands = ["...", "...", ...]
        self.returnCommand = command


class Neo4JNLI:
    def __init__(self):
        self.db = None
        self.nodes = []  # type class Node
        self.relationships = []  # type class Relationship

        self.userInterface = UserInterface()

    def _db_connect(self):
        if self.db is not None:
            print("WARNING Cannot connect to db, db connection already established!")
            return

        self.db = DBNeo4j("bolt://localhost:7687", "username", "password")

    def run(self):
        """Event loop that processes user input"""

        # MAIN GOAL: FILL cypher_query AND THEN EXECUTE QUERY

        # Idea: node class with constraints?
        #
        # target_node = Node("Business", {"name": "NAME", "city": "CITY"})
        # other_nodes = [Node(...), Node(...)]
        # return_command = ""
        #
        # query = create_query(target_node, other_nodes, return_command)
        # print(query) -> "MATCH (n:Business) WHERE n.name = 'NAME' AND n.city = 'CITY' RETURN COUNT(n)"
        # db.query(query)
        #
        #
        # cypher class?
        cypher = {
            "target_node": "",         # eg. "Business"
            "target_constraints": [],  # eg. {"name": "NAME", "city": "CITY"} -> "WHERE m.name = 'NAME' AND m.city = 'CITY'"
            "other_nodes": [],         # eg. [{"direction": "to", "relationship": "WRITES", "node": "Review"}]
            "return_command": "",      # eg. "COUNT", "ORDER DESC", ...
        }

        try:
            self._db_connect()
        except Neo4jNLIException as e:
            print(e)
            # if e.isFatal:
            #     return
            return

        query_nl = "What Breweries near me that my friends also like have the highest rating?"
        query_nl = "How many Breweries are in Phoenix?"
        query_nl = "How many Businesses are in Phoenix?"  # MATCH (m:Business) WHERE m.city = "Phoenix" RETURN COUNT(m)
        query_cl = "Which city is Mother Bunch Brewing in?"

        # TODO steps: Find target node/edge/attr we are trying to receive. Eg. "How many businesses are in Phoenix?"
        #                                                                    = Node(Business) What? COUNT(...)
        #                                                                    = MATCH (m:Business) ... RETURN COUNT(m)
        #             Next, what are our constraints?

        # query_nl = "How many reviews does Mother Bunch Brewing have?"
        # query_nl = "How many stars does Mother Bunch Brewing have?"

        print("INPUT:", query_nl)





        # DO SOMETHING
        interpreter = NLInterpreter(self.db.schema)
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

        interpreter.recognise_graph_components(query_nl)
        #keyConcepts, context = interpreter.identify_key_concepts(query_nl)

        query_cypher = ""

        print("OUTPUT:", query_cypher)

        # while True:
        while False:
            event = self.userInterface.wait_for_event()
            #event = ("QUERY", "match(m) return m limit 1",)  # tmp

            command = event[0]
            if command == "QUIT":
                break
            elif command != "QUERY":
                raise Neo4jNLIException("Received Unknown Event in Neo4jNLI.run()")

            # if command == "QUERY": ...

            query_nl = event[1]

            #newv

            something = self.nLInterpreter.process(query_nl)

            #new^

            # TODO userInterface.user_input() returns tuples, first element is event, seoncd is data
            #      eg. ("MSG_QUERY", "MATCH (m) RETURN m LIMIT 1")
            #          ("MSG_QUIT", )

            # TODO MEAT AND GRAVY OF APPLICATION
            # eg.
            # NaturalLanguageQueryInterpreter()
            # NaturalLanguageQueryAnalyser()
            # CypherQueryCreator()
            query_cypher = query_nl  # tmp

            try:
                results = self.db.query(query_cypher)
                self.userInterface.display_results(results)
            except Neo4jNLIException as e:
                print(e)
                if e.isFatal:
                    break
                #break  # tmp TODO handle error message

    def close(self):
        if self.db is None:
            print("WARNING Cannot close db if db is None!")
            return

        self.db.close()


if __name__ == "__main__":
    nli = Neo4JNLI()
    nli.run()
    nli.close()
