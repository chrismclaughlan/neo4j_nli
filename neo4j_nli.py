from spacy.tokens.doc import Doc as spacy_Doc
from spacy.tokens import Token as spacy_Token
from spacy.tokens.span import Span as spacy_Span
from typing import Union, Tuple

from db_management_system.db_neo4j import DBNeo4j
from db_management_system.types import Command, Node, Relationship, Property, Parameter
#from query_creator.cypher_query import CypherQuery
from query_creator.cypher_query_wip import CypherQuery
from components.sentence import Sentence, Span
from processing import process_text
import config

nlp = config.nlp


NOUN_SIMILARITY_THRESHOLD = 0.75


class Neo4JNLI:
    def __init__(self, database_uri: str, database_username: str, database_password: str):
        self.db = DBNeo4j(database_uri, database_username, database_password)
        #self.db = None  # to speed up init phase

    def find_match(self, target_span: Span, target_list: list[Union[Node, Relationship]]) -> Union[Command, Node, Relationship, Property, Parameter, None]:
        # 1. Check if matching a Command
        # for each in COMMANDS:
        #     print(each[0], "<-command?->", target_span.text.lower())
        #     if each[0] == target_span.text.lower():
        #         return Command(each[1])
        match = None

        # 2. Check if matching a Node / Property
        similarity_matrix = []
        for each in target_list:
            similarity = target_span.get_similarity(each.namesReadable)
            # TODO handle empty vectors! eg. similarity = 0
            if similarity >= NOUN_SIMILARITY_THRESHOLD:
                similarity_matrix.append(
                    {"similarity": similarity, "match": each, "match_prop": None}
                )

            for prop in each.properties:
                similarity = target_span.get_similarity(prop.namesReadable)
                if similarity >= NOUN_SIMILARITY_THRESHOLD:
                    similarity_matrix.append(
                        {"similarity": similarity, "match": each, "match_prop": prop}
                    )

        if len(similarity_matrix) > 0:
            best_match = similarity_matrix[0]
            if len(similarity_matrix) > 1:
                similarity_matrix.sort(key=lambda dic: dic["similarity"], reverse=True)
                best_match = similarity_matrix[0]

                # If top 2 choices equal, give priority to Node!  # TODO prompt user? Eg. "Is ... a property or a node?"
                if (similarity_matrix[0]["similarity"] == similarity_matrix[1]["similarity"]):
                    print("Equal similarity! Prioritising Node (last dict shown to the right)!", similarity_matrix[0], "<->", similarity_matrix[1])
                    if (similarity_matrix[1]["match_prop"] is None):
                        best_match = similarity_matrix[1]

            print(target_span, similarity_matrix)

            if best_match["match_prop"]: return best_match["match_prop"]
            elif best_match["match"]: return best_match["match"]

        # 3. Check if matching a Parameter
        parameter = self.find_parameter_in_db(target_span.span.text)
        if parameter:
            return parameter

        return None


# MATCH (n) WHERE ANY(x IN KEYS(n) WHERE n[x] =~ "(?i)#*#2018/01/01,01:40:00")
# RETURN n, [x IN KEYS(n) WHERE n[x]  =~"#2018/01/01,01:40:00" | x] AS myValues

# MATCH (n) WHERE ANY(x IN KEYS(n) WHERE n[x] =~ "(?i)#*#2018/01/01,01:40:00")
# RETURN [x IN KEYS(n) WHERE n[x]  =~"#2018/01/01,01:40:00" | x] AS property_names, labels(n) AS node_labels

    def find_parameter_in_db(self, parameter: str) -> Union[Parameter, None]:
        """Value is string"""
        # TODO handle special regex characters! Escape parameter!

        regex = f"(?i)#*{parameter}"
        query = f"""
MATCH (m) WHERE any(key IN keys(m) WHERE m[key] =~ $regex)
RETURN DISTINCT REDUCE 
(values = [], key IN keys(m) | 
CASE
WHEN m[key] =~ $regex THEN values + key
ELSE values
END
) AS property_names, labels(m) AS node_labels
        """
        result = self.db.query(query, {"regex": regex})
        if len(result) == 0:
            return None

        if len(result) > 1:
            # TODO Overall idea is to score each element with certain criteria:
            # 1. Priority to node with direct connection to prev/next node in sentence
            # 2. Priority to highest count (or lowest?)
            pass

        print("p!nl!pn!", parameter, result)

        # TODO return multiple parameters! Store multiple possibilities for each span!
        # TODO REGEX find data after first # occured

        node_labels: list[str] = result[0]["node_labels"]
        property_names: list[str] = result[0]["property_names"]

        for node in self.db.schema.nodes:
            print(node.label, node_labels)
            if node.label in node_labels:
                for prop in node.properties:
                    print("PROP", prop.name, property_names)
                    if prop.name in property_names:
                        return Parameter(parameter, prop)

        return None

    @staticmethod
    def find_command(target_span: spacy_Span) -> Union[Command, None]:
        for c in Command.translations:
            if c["text"] == target_span.text.lower():
                return Command(c)
        return None

    def run(self) -> None:
        queries = [
            # "How many Cities?",
            # "City",
            # "How many Businesses that are Breweries are in Phoenix?",
            #"How many stars does Mother Bunch Brewing have?",
            # "How many businesses are in the category Breweries?",

            # "How many Wind Mills are there in the US?",
            # "How is that even possible?",

            # "Named individuals that have wind direction",
            "How much wind speed on date #2018/01/01,01:40:00",
        ]

        while queries:
            natural_language_query = queries.pop()
            doc = process_text(natural_language_query)
            sentence = Sentence(doc)

            print(list(sentence.doc))

            iteration_no = 1
            while True:
                print(iteration_no)
                print(sentence)
                iteration_no+=1
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
                        match = self.find_match(each, self.db.schema.nodes)
                        if match:
                            each.match = match
                            continue

                    did_split = each.split()
                    if did_split:
                        did_change = True

                if not did_change:
                    break

            # Sentence split, and (most) components identified -> Construct query!
            cypher_query = CypherQuery(sentence)
            print(cypher_query)

            print(sentence)

    def close(self) -> None:
        if self.db: self.db.close()


if __name__ == "__main__":
    nli = Neo4JNLI("bolt://localhost:7687", "neo4j", "password")  # username = neo4j or username
    nli.run()
    nli.close()