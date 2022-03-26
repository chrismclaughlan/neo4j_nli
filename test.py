import unittest
from db_management_system.db_neo4j import DBNeo4j


class TestNeo4JNLI(unittest.TestCase):
    def test_database(self):
        db = DBNeo4j("bolt://localhost:7687", "username", "password")
        nodes, relationships = db.get_nodes_and_relationships()
        print("node", nodes)
        print("relationships", relationships)
        db.query("MATCH(m) RETURN m LIMIT 5")
        db.close()


if __name__ == '__main__':
    unittest.main()