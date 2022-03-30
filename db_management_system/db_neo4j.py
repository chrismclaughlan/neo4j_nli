import neo4j
from exception import Neo4jNLIException
from db_management_system.nodes import Node
from db_management_system.relationships import Relationship

from neo4j.exceptions import ServiceUnavailable, CypherSyntaxError


class DBNeo4j:

    def __init__(self, uri, username, password):
        self.uri = uri
        self.username = username
        # self.password = password

        self.__driver, self.schema = None, None
        try:
            print(f"Starting driver for", self)
            self.__driver = neo4j.GraphDatabase.driver(uri, auth=(username, password))
            self.refresh_schema()
        except neo4j.exceptions.DriverError as e:
            raise Neo4jNLIException("Initialising Neo4j Graph Database Driver", is_fatal=False, exception=e)
        except Neo4jNLIException as e:
            raise e

    def __str__(self):
        return f"neo4j database uri: {self.uri} username: '{self.username}'"

    def refresh_schema(self):
        """Queries database for current schema. Returns two lists: First containing strings of nodes' names. Second
        containing relationship tuples formatted as (node_from, relationship_between, node_to)."""
        if not self.__driver:
            raise Neo4jNLIException("No driver initialised!")

        self.schema = {
            "nodes": [],
            "relationships": [],
        }

        session = self.__driver.session()

        # Extracts schema data from database
        schema_data = self.query("CALL db.schema.visualization()")[0]
        #print(schema_data)
        # set(...) used to avoid duplicates!
        schema_nodes = set([each["name"] for each in schema_data["nodes"]])
        schema_relationships = set([(each[0]["name"], each[1], each[2]["name"],) for each in schema_data["relationships"]])

        # Parse schema data for node data
        for node_name in set(schema_nodes):
            self.schema["nodes"].append(Node(node_name))
            # result = session.run(f"MATCH(n:{node_name}) UNWIND keys(n) AS keys RETURN DISTINCT keys")
            # node_props = [prop["keys"] for prop in result.data()]
            # node = Node(node_name, node_props)
            # nodes.append(node)

        # Parse schema data for relationship data
        for each in set(schema_relationships):
            relationship_name = each[1]
            node_source = each[0]
            node_target = each[2]
            self.schema["relationships"].append(Relationship(relationship_name, node_source, node_target))
            # result = session.run(f"MATCH({node_target})<-[r:{relationship_name}]-({node_source}) UNWIND keys(r) AS keys RETURN DISTINCT keys")
            # relationship_props = [prop["keys"] for prop in result.data()]
            # relationship = Relationship(relationship_name, node_source, node_target, relationship_props)
            # relationships.append(relationship)

        if True:  # save query time
            node_type_properties = self.query("CALL db.schema.nodeTypeProperties()")
            #print(node_type_properties)

            for node in self.schema["nodes"]:
                # Find node label in node_type_properties
                # Get list of all instances in node_type_properties and remove them from node_type_properties
                # Iterate list and add them to node
                for each in node_type_properties:
                    prop_name = each["propertyName"]
                    if prop_name and node.name in each["nodeLabels"]:
                        node.add_property(prop_name)

            rel_type_properties = self.query("CALL db.schema.relTypeProperties()")
            #print(rel_type_properties)

            for rel in self.schema["relationships"]:
                for each in rel_type_properties:
                    prop_name = each["propertyName"]
                    if prop_name and rel.name == each["relType"][2:-1]:
                        rel.add_property(prop_name)

        # except Exception as e:
        #     raise Neo4jNLIException("Could not complete queries", exception=e)
        # finally:
        #     if session:
        #         session.close()

        if session: session.close()

    # TODO issue found: Different results
    def query(self, cypher_query):
        if not self.__driver:
            raise Exception("No driver initialised!")

        session, result = None, None
        try:
            session = self.__driver.session()
            result = session.run(cypher_query).data()
        except ServiceUnavailable as e:
            raise Neo4jNLIException("Service Unavailable", is_fatal=False, exception=e)
        except CypherSyntaxError as e:
            raise Neo4jNLIException("Invalid CYPHER Syntax!", is_fatal=False, exception=e)
        finally:
            if session:
                session.close()

        return result

    def close(self):
        if not self.__driver:
            print("WARNING Could not close driver if driver is None!")

        self.__driver.close()
