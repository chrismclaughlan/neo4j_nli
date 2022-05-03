from typing import Union

import neo4j
from exception import Neo4jNLIException
# from db_management_system.nodes import Node
# from db_management_system.relationships import Relationship
from db_management_system.types import Node, Relationship

from neo4j.exceptions import ServiceUnavailable, CypherSyntaxError, DatabaseError
from timeit import default_timer as timer
import re  # Regular Expression Operations

ALPHABET = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]

class Schema:
    def __init__(self, nodes: Node = None, relationships: Relationship = None):
        self.nodes = nodes if nodes is not None else []
        self.relationships = relationships if relationships is not None else []

    @staticmethod
    def get_variable_name(number_of_existing_variable_names):
        n = number_of_existing_variable_names
        iterations_alphabet = n // 26
        alphabet_index = n % 26
        return ALPHABET[alphabet_index] * (iterations_alphabet + 1)

    def add_node(self, label: str) -> None:
        var_name = "n_" + self.get_variable_name(len(self.nodes))
        node = Node(label, var_name)
        if node not in self.nodes:
            self.nodes.append(node)

    def add_relationship(self, type: str, source: str, target: str, props: list[str] = None) -> None:
        var_name = "r_" + self.get_variable_name(len(self.relationships))
        relationship = Relationship(type, var_name, source, target, props)
        if relationship not in self.relationships:
            self.relationships.append(relationship)

    def get_node_by_label(self, label: str) -> Union[Node, None]:
        for node in self.nodes:
            if node.label == label: return node
        return None

    def get_rela_by_type(self, type: str) -> Union[Relationship, None]:
        for relationship in self.relationships:
            if relationship.type == type: return relationship
        return None


class DBNeo4j:

    def __init__(self, uri: str, username: str, password: str):
        self.uri = uri
        self.username = username
        # self.password = password

        self.schema = Schema()

        self.__driver = None
        try:
            print(f"Starting driver for", self)
            self.__driver = neo4j.GraphDatabase.driver(uri, auth=(username, password))
            self.refresh_schema()
        except neo4j.exceptions.DriverError as e:
            raise Neo4jNLIException("Initialising Neo4j Graph Database Driver", is_fatal=False, exception=e)
        except Neo4jNLIException as e:
            raise e

    def get_shortest_path(self, a: str, b: str) -> str:
        # TODO clean function up!
        print("DBNeo4j - Finding the shortest path for", a, "and", b)
        query_text = f"MATCH (a:{a}) " \
                f"MATCH (b:{b}), " \
                f"p = shortestPath((a)-[*1..10]-(b)) " \
                "WITH p LIMIT 200 " \
                "RETURN p ORDER BY length(p) LIMIT 1"
        # query_text = f"MATCH (a:City) " \
        #         f"OPTIONAL MATCH (b:User), " \
        #         "p = shortestPath((a)-[*1..10]-(b)) " \
        #         "WITH p LIMIT 50 " \
        #         "RETURN p ORDER BY length(p) LIMIT 1"

        print(query_text)

        session = None
        try:
            session = self.__driver.session()
            result = session.run(query_text).single().items()
        except DatabaseError as e:
            return ""
        finally:
            if session:
                session.close()
        path = result[0][1]

        if not path:
            return ""

        start = path.start_node
        end = path.end_node
        print("start", start)
        for i, each in enumerate(path):
            print(i, each)
        print("end", end)
        #print(result, start, end, path)

        r = f"({list(start.labels)[0]})"
        for rela in path:
            node_label = list(rela.nodes[0].labels)[0]
            r += f"-[:{rela.type}]-({node_label})"
        print(r)


        # Translate to our instances
        #start_node = self.find_node_by_labels(list(start.labels))
        start_node: Node = self.schema.get_node_by_label(a)
        t: str = str(start_node)
        for i, relationship in enumerate(path):
            r = self.schema.get_rela_by_type(relationship.type)
            if i < len(path) - 1:
                n = self.schema.get_node_by_label(list(relationship.nodes[0].labels)[0])
            else:
                n = self.schema.get_node_by_label(b)
            t+= "-" + str(r) + "-" + str(n)
        return t

    @staticmethod
    def create_regex_param(text: str) -> str:
        return f"(?i)#?({re.escape(text)})"

    def __str__(self):
        return f"neo4j database uri: {self.uri} username: '{self.username}'"

    def refresh_schema(self) -> None:
        """Queries database for current schema. Returns two lists: First containing strings of nodes' names. Second
        containing relationship tuples formatted as (node_from, relationship_between, node_to)."""
        if not self.__driver:
            raise Neo4jNLIException("No driver initialised!")
        print("DBNeo4j - Refreshing Schema")

        self.schema = Schema()
        session = self.__driver.session()

        # Extracts schema data from database
        schema_data = self.query("CALL db.schema.visualization()")[0]
        #print(schema_data)
        # set(...) used to avoid duplicates!
        schema_nodes = set([each["name"] for each in schema_data["nodes"]])
        schema_relationships = set([(each[0]["name"], each[1], each[2]["name"],) for each in schema_data["relationships"]])

        # Parse schema data for node data
        for node_name in set(schema_nodes):
            self.schema.add_node(node_name)

        # Parse schema data for relationship data
        for each in set(schema_relationships):
            self.schema.add_relationship(each[1], source=each[0], target=each[2])

        if True:  # save query time
            node_type_properties = self.query("CALL db.schema.nodeTypeProperties()")
            #print(node_type_properties)

            for node in self.schema.nodes:
                for each in node_type_properties:
                    prop_name = each["propertyName"]
                    if prop_name and node.label in each["nodeLabels"]:
                        node.add_property(prop_name)

            rel_type_properties = self.query("CALL db.schema.relTypeProperties()")
            #print(rel_type_properties)

            for relationship in self.schema.relationships:
                for each in rel_type_properties:
                    prop_name = each["propertyName"]
                    if prop_name and relationship.type == each["relType"][2:-1]:
                        relationship.add_property(prop_name)

        if session: session.close()

    # TODO issue found: Different results
    def query(self, query_text: str, parameters: dict = None) -> list[dict]:
        if not self.__driver:
            raise Exception("No driver initialised!")

        session, data = None, None
        try:
            session = self.__driver.session()

            print("DBNeo4j - Executing query", "\"" + query_text[:50] + "...\" with params", parameters)
            start = timer()
            result = session.run(query_text, parameters=parameters)
            data = result.data()
            end = timer()
            print("          Took", end - start, "seconds")  # Time in seconds, e.g. 5.38091952400282

        except ServiceUnavailable as e:
            raise Neo4jNLIException("Service Unavailable", is_fatal=False, exception=e)
        except CypherSyntaxError as e:
            raise Neo4jNLIException("Invalid CYPHER Syntax!", is_fatal=False, exception=e)
        finally:
            if session:
                session.close()

        return data

    def close(self) -> None:
        if not self.__driver:
            print("WARNING Could not close driver if driver is None!")

        self.__driver.close()
