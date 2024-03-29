from typing import Union, Type
from components.sentence import Sentence
from components.span import Span
from db_management_system.types import Match, Command, Node, Property, Parameter, Relationship
from db_management_system.db_neo4j import DBNeo4j


class CypherComponent:
    def __init__(self, match: Match, command: Union[Command, None] = None):
        self.match: Match = match
        self.command: Union[Command, None] = command
        self.node = None
        self.match_type: Union[Type[Node], Type[Property], Type[Parameter], None] = None  # TODO @getter ?
        # TODO what if relationship?
        if isinstance(match.match, Node):
            self.node = match.match
            self.match_type = Node
        elif isinstance(match.match, Property):
            self.node = match.match.parent
            self.match_type = Property
        elif isinstance(match.match, Parameter):
            self.node = match.match.parent.parent
            self.match_type = Parameter
        else:
            raise Exception("Error creating CypherComponent: Could not find match for", match)

    def __str__(self):
        #return str(self.match.match)
        instance = self.match.match
        if self.match_type == Node or self.match_type == Property:
            return str(self.node)
        elif self.match_type == Parameter:
            #return str(instance)
            regex = DBNeo4j.create_regex_param(instance.value).replace("\\", "\\\\")    # TODO: Why do we need this? Why does it sometimes have single "\" and then "\\"?
            #return f" WHERE {self.node.variableName}.{instance.parent.name} =~ '{regex}'"
            return f"{self.node} WHERE {self.node.variableName}.{instance.parent.name} =~ '{regex}'"
        return ""
        #raise Exception("Error creating CypherComponent: Could not find match for", type(instance))


# def get_node(match: Match) -> Union[Node, None]:
#     instance = match.match
#     if isinstance(instance, Node):
#         return instance
#     elif isinstance(instance, Property):
#         return instance.parent
#     elif isinstance(instance, Parameter):
#         return instance.parent.parent
#     return None


class CypherQuery:
    def __init__(self, db: DBNeo4j, sentence: Sentence):
        self.db = db
        self.sentence: Sentence = sentence
        #
        # self.construct_query()

    def get_target(self, matches: list[Match]) -> Union[CypherComponent, None]:
        # Target can only be: Node / Property. (Q: What about Relationship?)
        # Target either follows first command, or if no command, the first Node / Property.

        # Find the first command and return the next Node / Property as the target (with the command attached)
        first_command: Union[Command, None] = None
        first_match: Union[Match, None] = None
        for match in matches:
            if match is None: continue

            instance = match.match
            if isinstance(instance, Command):
                first_command = instance
            #elif isinstance(instance, Node) or isinstance(instance, Property):
            else:
                if first_match is None:
                    first_match = match

                if first_command is not None:
                    return CypherComponent(match, first_command)

        # If no command found, return the first Node / Property that was found
        if first_match:
            return CypherComponent(first_match)

        # If no Node / Property found, no target found!
        return None

    def construct_query(self, sort=True) -> str:
        """sort=True -> Sort confidence within span matches, False->don't"""
        spans: list[Span] = self.sentence.get_all_span_leaves()
        matches: list[Union[Match, None]] = []
        for s in spans:
            if not s.matches or s.ignoreMatches: continue
            if sort:
                s.sort_by_most_confident_match()
            matches.append(s.matches[0])

        # 1. Find target we are searching for! eg. Match ( ? ) ... RETURN ?
        target: Union[CypherComponent, None] = self.get_target(matches)
        if target is None:
            raise Exception("Cannot create CypherQuery: No target found in sentence!")


        components: list[CypherComponent] = []  # Excluding target!
        for match in matches:
            if match is None or match == target.match or isinstance(match.match, Command):
                continue

            components.append(CypherComponent(match))  # TODO commands for other components!

        # TODO Find longest match in components, reduce duplicate lines!

        components_s: str = ""
        for comp in components:
            if comp.node == target.node:
                components_s += "\nMATCH " + str(comp)
            else:
                print("SHORTEST PATH", target.node, comp.node)

                b = ""
                if comp.match_type == Parameter:
                    b = f"{comp.node.label} {{{comp.match.match.parent.name}: '{comp.match.match.value}'}}"
                else:
                    b = str(comp.node)

                shortest_path: str = self.db.get_shortest_path(target.node.label, comp.node.label)#b, comp.node.variableName)

                print(shortest_path)

                if shortest_path:
                    components_s += "\nMATCH " + shortest_path
                    if comp.match_type == Parameter:
                        parameter: Parameter = comp.match.match
                        regex = DBNeo4j.create_regex_param(parameter.value).replace("\\", "\\\\")  # TODO: Why do we need this? Why does it sometimes have single "\" and then "\\"?
                        components_s += f" WHERE {comp.node.variableName}.{parameter.parent.name} =~ '{regex}'"
                else:
                    components_s += "\nMATCH " + str(target.node) + "-[*1..3]-" + str(comp)

                # relationship = None
                # for rela in self.db.schema.relationships:
                #     if rela.is_relationship_between(target.node, comp.node):
                #         relationship = rela
                #         break
                # print(relationship)
                #
                # if relationship is not None:
                #     components_s += "\nMATCH " + str(target.node) + "-" + str(relationship) + "-" + str(comp)
                # else:
                #     # TODO improve reliability and performance in relationships ... eg. [*1...3] ...
                #     components_s += "\nMATCH " + str(target.node) + "-[*1..3]-" + str(comp)

        if target.command:
            if target.match_type == Property:
                command_name = str(target.command.cypher_dict["as_prop"])
                prop_name: str = target.match.match.parent.name
                command_target = f"{target.node.variableName}.{prop_name}"
            else:
                command_name = str(target.command.cypher_dict["as_node"])
                command_target = target.node.variableName

            return_s = f"{command_name}({command_target})"
        else:
            return_s = target.node.variableName

        return f"MATCH {str(target)} {components_s} \nRETURN {return_s} AS results"


# For debugging and testing purposes
if __name__ == "__main__":

    from components.sentence import Sentence
    from config import nlp

    doc = nlp("How many businesses are in the category Breweries?")
    spans: list[Span] = []
    spans.append(Span(doc[0:2], [Match(Command({'text': 'how many', 'as_node': 'COUNT', 'as_prop': 'SUM'}), 1.0)]))
    businesses = Node("Business", "a")
    businesses.add_property("id")
    businesses.add_property("name")
    businesses.add_property("address")
    businesses.add_property("city")
    businesses.add_property("state")
    businesses.add_property("location")
    spans.append(Span(doc[2:3], [Match(businesses, 0.7698343847104357)]))
    spans.append(Span(doc[3:4]))
    spans.append(Span(doc[4:5]))
    spans.append(Span(doc[5:6]))
    category = Node("Category", "b")
    category.add_property("name")
    spans.append(Span(doc[6:7], [Match(category, 1.0000001026793226)]))
    name = Property("name", category)
    breweries = Parameter("breweries", name)
    spans.append(Span(doc[7:8], [Match(breweries, 1.0)]))
    sentence = Sentence(doc, spans)
    print(sentence)

    db = DBNeo4j("bolt://localhost:7687", "neo4j", "password")
    #cypher_query = CypherQuery(db, sentence)
    query = CypherQuery(db, sentence)
    #b = cypher_query.has_valid_relationships()

    cypher = query.construct_query()
    print(cypher)

    db.close()
