from spacy.tokens.doc import Doc as spacy_Doc
from spacy.tokens import Token as spacy_Token
from spacy.tokens.span import Span as spacy_Span
from typing import Union, Tuple

from db_management_system.db_neo4j import DBNeo4j
from db_management_system.types import Match, Command, Node, Relationship, Property, Parameter
#from query_creator.cypher_query import CypherQuery
from query_creator.cypher_query_wip import CypherQuery
from components.sentence import Sentence, Span
from processing import process_text
import config

nlp = config.nlp


NOUN_SIMILARITY_THRESHOLD = 0.7


class Neo4JNLI:
    def __init__(self, database_uri: str, database_username: str, database_password: str):
        self.db = DBNeo4j(database_uri, database_username, database_password)
        #self.db = None  # to speed up init phase

    def find_matches(self, target_span: Span, target_list: list[Union[Node, Relationship]]) \
            -> list[Match]:
        """Returns list of most likely matches. Ordered from most likely to least."""

        matches: list[Match] = []

        # 1. Check if matching a Command
        # for each in COMMANDS:
        #     print(each[0], "<-command?->", target_span.text.lower())
        #     if each[0] == target_span.text.lower():
        #         return Command(each[1])

        # 2. Check if matching a Node / Property
        similarity_matrix = []
        for each in target_list:
            similarity = target_span.get_similarity(each.namesReadable)
            # TODO handle empty vectors! eg. similarity = 0
            #print(similarity, target_span, each.namesReadable)
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
            similarity_matrix.sort(key=lambda dic: dic["similarity"], reverse=True)

            match = similarity_matrix[0]
            if match["match_prop"]:
                matches.append(
                    Match(match["match_prop"], match["similarity"])
                )
            elif match["match"]:
                matches.append(
                    Match(match["match"], match["similarity"])
                )
            # for each in similarity_matrix:
            #     if each["match_prop"]:
            #         matches.append(
            #             Match(each["match_prop"], each["similarity"])
            #         )
            #     elif each["match"]:
            #         matches.append(
            #             Match(each["match"], each["similarity"])
            #         )

        # 3. Check if matching a Parameter
        parameters = self.find_parameter_in_db(target_span.span.text)
        for each in parameters:
            matches.append(
                Match(each, confidence=1.0)
            )

        return matches

# MATCH (n) WHERE ANY(x IN KEYS(n) WHERE n[x] =~ "(?i)#*#2018/01/01,01:40:00")
# RETURN n, [x IN KEYS(n) WHERE n[x]  =~"#2018/01/01,01:40:00" | x] AS myValues

# MATCH (n) WHERE ANY(x IN KEYS(n) WHERE n[x] =~ "(?i)#*#2018/01/01,01:40:00")
# RETURN [x IN KEYS(n) WHERE n[x]  =~"#2018/01/01,01:40:00" | x] AS property_names, labels(n) AS node_labels

    def find_parameter_in_db(self, parameter: str) -> list[Parameter]:
        """Value is string"""
        # TODO handle special regex characters! Escape parameter!
        # TODO REGEX find data after first # occured. Maybe add option to interface for users to provide regex?
        matches: list[Parameter] = []

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
            return matches

        for each in result:
            node_labels: list[str] = each["node_labels"]
            property_names: list[str] = each["property_names"]

            for node in self.db.schema.nodes:
                #print(node.label, node_labels)
                if node.label in node_labels:
                    for prop in node.properties:
                        #print("PROP", prop.name, property_names)
                        if prop.name in property_names:
                            matches.append(Parameter(parameter, prop))

        return matches

    @staticmethod
    def find_command(target_span: spacy_Span) -> Union[Command, None]:
        for c in Command.translations:
            if c["text"] == target_span.text.lower():
                return Command(c)
        return None

    def step_find_node_components(self, sentence: Sentence) -> None:
        iteration_no = 1
        while True:
            # print("step_find_node_components", iteration_no)
            # print(sentence)
            iteration_no += 1
            # Get all sub-spans
            all_spans = sentence.get_all_span_leaves()

            did_change = False
            for each in all_spans:
                # If match or failed to find a match, skip and leave for later evaluation (relationships...)
                # ALso, if no nouns present in span, leave for later evaluation (relationships...)
                if each.matches:# or each.matchTried:
                    continue
                each.matchTried = True

                if each.numNouns < 1:
                    command = self.find_command(each.span)
                    if command:
                        each.matches = [Match(command, confidence=1.0)]
                        continue
                else:
                    matches = self.find_matches(each, self.db.schema.nodes)
                    if matches:
                        each.matches = matches
                        continue

                did_split = each.split()
                if did_split:
                    did_change = True

            if not did_change:
                break

    def step_reduce_matching_spans(self, sentence):
        """Reduce spans that contain matches to accurately locate matches within them. Frees
        other words/(spans) in span for context in later steps."""

        iteration_no = 1
        # print("step_reduce_matching_spans", iteration_no)
        # print(sentence)
        # Get all sub-spans
        all_spans = sentence.get_all_span_leaves()

        for each_span in all_spans:
            if len(each_span.span) > 1 and each_span.matches:
                for each_match in each_span.matches:  # TODO !!! will create duplicates !!!
                    if isinstance(each_match.match, Parameter) or isinstance(each_match.match, Command):
                        continue

                    match_name: spacy_Doc = each_match.match.namesReadable
                    span: spacy_Span = each_span.span

                    confidence: float = 0.0
                    while True:
                        confidence = span.similarity(match_name)
                        if confidence >= 1.0:
                            break
                        spanL: spacy_Span = span[:-1]
                        spanR: spacy_Span = span[1:]

                        confidenceL: float = spanL.similarity(match_name)
                        confidenceR: float = spanR.similarity(match_name)

                        # >= because possibility that other confidence is 0. Therefore, this confidence
                        # must be the sole contribution to confidence (a match). Eg. when span = "date #2018/01/01,01:40:00"
                        if confidenceL >= confidence and confidenceL > confidenceR:
                            span = spanL
                        elif confidenceR >= confidence and confidenceR > confidenceL:
                            span = spanR
                        else:
                            break

                    if span != each_span.span:

                        # Split span!
                        children: list[Span] = []

                        old_span_i_beg = each_span.span[0].i
                        old_span_i_end = each_span.span[-1].i

                        new_span_i_beg = span[0].i
                        new_span_i_end = span[-1].i

                        new_span_l_i_beg = old_span_i_beg
                        new_span_l_i_end = new_span_i_beg

                        new_span_r_i_beg = new_span_i_end
                        new_span_r_i_end = old_span_i_end

                        old_span   = each_span.span.doc[old_span_i_beg:old_span_i_end+1]
                        new_span_l = each_span.span.doc[new_span_l_i_beg:new_span_l_i_end]
                        new_span_m   = each_span.span.doc[new_span_i_beg:new_span_i_end+1]
                        new_span_r = each_span.span.doc[new_span_r_i_beg+1:new_span_r_i_end+1]

                        if new_span_l:
                            children.append(
                                Span(new_span_l)
                            )
                        if new_span_m:
                            children.append(
                                Span(new_span_m, [Match(each_match.match, confidence)])
                            )
                        if new_span_r:
                            children.append(
                                Span(new_span_r)
                            )
                        each_span.children = children
                        each_span.matches = []
                        break  # TODO !!! TMP FIX FOR DUPLICATES !!!


    def run(self) -> None:
        queries = [
            "How many Cities?",
            "City",
            "How many Businesses that are Breweries are in Phoenix?",
            "How many stars does Mother Bunch Brewing have?",
            "How many businesses are in the category Breweries?",

            # "On #2018/01/01,01:40:00 how much wind power did we produce?",
            # "How much wind speed on #2018/01/01,01:40:00?",
            # "Named individuals that have wind direction",
            # "How much wind speed on date #2018/01/01,01:40:00?",
        ]

        while queries:
            natural_language_query = queries.pop()
            doc = process_text(natural_language_query)
            sentence = Sentence(doc)
            self.step_find_node_components(sentence)
            self.step_reduce_matching_spans(sentence)
            self.step_find_node_components(sentence)

            # Sentence split, and (most) components identified -> Construct query!
            cypher_query = CypherQuery(sentence)
            print(sentence)

    def close(self) -> None:
        if self.db: self.db.close()


if __name__ == "__main__":
    nli = Neo4JNLI("bolt://localhost:7687", "neo4j", "password")  # username = neo4j or username
    nli.run()
    nli.close()