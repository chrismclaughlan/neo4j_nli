from typing import Union, Type
from components.sentence import Sentence
from components.span import Span
from db_management_system.types import Match, Command, Node, Property, Parameter, Relationship
from db_management_system.db_neo4j import DBNeo4j


def get_linked_list_as_str(component: 'CypherComponent') -> str:
    if component is None: return ""
    return str(component) + " -> " + get_linked_list_as_str(component.next)


class CypherComponent:
    def __init__(self, match: Match, command: Command = None):
        self.match: Match = match
        self.next: Union['CypherComponent', None]= None
        self.prev: Union['CypherComponent', None] = None
        self.command: Union[Command, None] = command  # TODO can be multiple!
        self.constraint: Union[Parameter, None] = None  # TODO can be multiple!

    def add_next(self, component: 'CypherComponent') -> None:
        """Recursively add next to linked list"""
        if self.next is None:
            component.prev = self
            self.next = component
        else:
            self.next.add_next(component)

    def __str__(self):
        string = ""
        if self.command:
            if isinstance(self.match.match, Node):
                string += str(self.command.cypher_dict["as_node"])
            elif isinstance(self.match.match, Property):
                string += str(self.command.cypher_dict["as_prop"])
        string += str(self.match.match)
        if self.constraint:
            string += "." + str(self.constraint.parent.name) + " = " + str(self.constraint.value)
        return string


class CypherQuery:
    def __init__(self, db: DBNeo4j, sentence: Sentence):
        self.db = db
        self.sentence = sentence

        spans: list[Span] = self.sentence.get_all_span_leaves()
        matches: list[Union[Match, None]] = [s.get_most_confident_match() for s in spans]
        print(matches)

        # 1. Find target
        self.target: Union[CypherComponent, None] = None  # Head of linked list
        self.target = self.get_target(matches)
        if not self.target:
            print("Could not find valid target in cypher query!")

        print("target", self.target)

        # 2. Create linked list of Nodes (Nodes + properties etc.)
        # 2.1 Check neighbouring nodes (from relationships)
        # 2.2

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
            elif isinstance(instance, Node) or isinstance(instance, Property):
                if first_match is None:
                    first_match = match

                if first_command is not None:
                    return CypherComponent(match, first_command)

        # If no command found, return the first Node / Property that was found
        if first_match:
            return CypherComponent(first_match)

        # If no Node / Property found, no target found!
        return None

    # def add_target_relation(self, match: Match) -> None:
    #     # Determine if valid relation from target to match exists!
    #     for rela in self.db.schema.relationships:
    #         source =  rela.is_relationship_between(a=self.target.match.match, b=match.match)
    #         if source == "a":
    #             self.target.add_next()  # TODO add direction between components (eg. (prev)->(target)<-(next)
    #                                     # add_next() ... iterate over each (a)--(b)--(c) to see where connection makes sense
    #         elif source == "b":
    #             self.target



    # def create_components(self):
    #     # IDEA:
    #     # 1st iteration - Identify CypherComponents
    #     # 2nd iteration - Identify CypherConstraints
    #     handing_command: Union[Command, None] = None
    #     for i, match in enumerate(matches):
    #         # TODO rename types/.match to graph components?
    #         if match is None: continue
    #
    #         # Save command for next component
    #         if isinstance(match.match, Command):
    #             handing_command = match.match
    #             continue
    #
    #         # Ignore parameters on first pass
    #         if isinstance(match.match, Parameter):
    #             continue
    #
    #         cypher_component: CypherComponent = CypherComponent(match)
    #         if handing_command:
    #             cypher_component.command = handing_command
    #             handing_command = None
    #
    #         if self.target is None:
    #             self.target = cypher_component
    #         else:
    #             self.target.add_next(cypher_component)
    #
    #     for i, match in enumerate(matches):
    #         # TODO rename types/.match to graph components?
    #         if match is None: continue
    #         if isinstance(match.match, Parameter):
    #             print("Found parameter", match.match)
    #             self.attach_parameter(match.match)
    #
    #     print(get_linked_list_as_str(self.target))

    # def attach_parameter(self, parameter: Parameter):
    #     component: Union[CypherComponent, None] = self.target
    #
    #     # Find parameter parent (property)!
    #     while component:
    #         if isinstance(component.match.match, Property):
    #             if component.match.match.name == parameter.parent.name:
    #                 component.constraint = parameter
    #
    #         component = component.next
    #
    #     component = self.target
    #     # Find parameter parent's (property's) parent (Node/Relationship)!
    #     while component:
    #         print(component)
    #         if isinstance(parameter.parent.parent, Node):
    #             if component.match.match.label == parameter.parent.parent.label:
    #                 component.constraint = parameter
    #         elif isinstance(parameter.parent.parent, Relationship):
    #             if component.match.match.label == parameter.parent.parent.type:
    #                 component.constraint = parameter
    #
    #         component = component.next

    # def has_valid_relationships(self) -> bool:
    #     # TODO obviously
    #     relationships: list[Relationship] = self.db.schema.relationships
    #     print(relationships)
    #
    #     if self.target is None: return False
    #     component: CypherComponent = self.target
    #     while component and component.next:
    #         for rela in relationships:
    #             source = rela.nodeSource
    #             target = rela.nodeTarget
    #
    #             # TODO relationships etc.
    #             nodeCurrent = component.match.match
    #             nodeNext = component.next.match.match
    #             if isinstance(nodeCurrent, Node):
    #                 #print("FOUND NODE s t n", source, target, nodeCurrent)
    #                 if source == nodeCurrent.label:
    #                     if target == nodeNext.label:
    #                         print("FOUND MATCH", nodeCurrent, rela, nodeNext)
    #                 elif target == nodeCurrent.label:
    #                     if source == nodeNext.label:
    #                         print("found match", nodeNext, rela, nodeCurrent)
    #
    #
    #
    #         component = component.next
    #
    #     return True


class NewCypherComponent:
    def __init__(self, match: Match, variable_name: str, command: Union[Command, None] = None):
        self.variableName: str = variable_name
        self.match: Match = match
        self.command: Union[Command, None] = command
        self.node = None
        self.match_type: Union[Type[Node], Type[Property], Type[Parameter], None] = None
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

    def __repr__(self):
        instance = self.match.match
        if self.match_type == Node:
            return f"({self.variableName}:{self.node.label})"
        elif self.match_type == Property:
            return f"({self.variableName}:{self.node.label})"
        elif self.match_type == Parameter:
            props = f"{instance.parent.name}: '{instance.value}'"
            return f"({self.variableName}:{self.node.label} {{{props}}})"
        return ""
        #raise Exception("Error creating CypherComponent: Could not find match for", type(instance))


def get_node(match: Match) -> Union[Node, None]:
    instance = match.match
    if isinstance(match.match, Node):
        return match.match
    elif isinstance(match.match, Property):
        return match.match.parent
    elif isinstance(match.match, Parameter):
        return match.match.parent.parent
    return None


class NewCypherQuery:
    def __init__(self, db: DBNeo4j, sentence: Sentence):
        self.db = db
        self.sentence: Sentence = sentence
        #
        # self.construct_query()

    def get_target(self, matches: list[Match]) -> Union[NewCypherComponent, None]:
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
            elif isinstance(instance, Node) or isinstance(instance, Property):
                if first_match is None:
                    first_match = match

                if first_command is not None:
                    return NewCypherComponent(match, "a", first_command)

        # If no command found, return the first Node / Property that was found
        if first_match:
            return NewCypherComponent(first_match, "a")

        # If no Node / Property found, no target found!
        return None

    def construct_query(self) -> str:
        # alphabet excluding a (a is target variable name)
        alphabet = ["b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t",
                    "u", "v", "w", "x", "y", "z"]

        spans: list[Span] = self.sentence.get_all_span_leaves()
        matches: list[Union[Match, None]] = [s.get_most_confident_match() for s in spans]

        target: Union[NewCypherComponent, None] = self.get_target(matches)
        if target is None:
            raise Exception("Cannot create CypherQuery: No target found in sentence!")


        # TODO add unique id to each node/relationship for naming in query? (eg: Category -> aab) ?

        components: list[NewCypherComponent] = []  # Excluding target!
        for match in matches:
            if match is None or match == target.match or isinstance(match.match, Command):
                continue

            # TODO tmp fix for node
            node = get_node(match)
            if node and node == target.node:
                components.append(NewCypherComponent(match, "a"))
            else:
                components.append(NewCypherComponent(match, alphabet.pop()))  # TODO commands for other components!

        # TODO Find longest match in components, reduce duplicate lines!
        # TODO .is_relationship_between(..., ...) !!!!

        target_s: str = str(target)
        components_s: str = ""
        for comp in components:
            if comp.node == target.node:
                components_s += "\nMATCH " + str(comp)
            else:
                components_s += "\nMATCH " + target_s + "--" + str(comp)

        if target.command:
            if target.match_type == Property:
                command_name = str(target.command.cypher_dict["as_prop"])
                prop_name: str = target.match.match.parent.name
                command_target = f"a.{prop_name}"
            else:
                command_name = str(target.command.cypher_dict["as_node"])
                command_target = "a"

            return_s = f"{command_name}({command_target})"
        else:
            return_s = "a"

        return f"MATCH {target_s} {components_s} \nRETURN {return_s}"


# For debugging and testing purposes
if __name__ == "__main__":

    from components.sentence import Sentence
    from config import nlp

    doc = nlp("How many businesses are in the category Breweries?")
    spans: list[Span] = []
    spans.append(Span(doc[0:2], [Match(Command({'text': 'how many', 'as_node': 'COUNT', 'as_prop': 'SUM'}), 1.0)]))
    businesses = Node("Business")
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
    category = Node("Category")
    category.add_property("name")
    spans.append(Span(doc[6:7], [Match(category, 1.0000001026793226)]))
    name = Property("name", category)
    breweries = Parameter("breweries", name)
    spans.append(Span(doc[7:8], [Match(breweries, 1.0)]))
    sentence = Sentence(doc, spans)
    print(sentence)

    db = DBNeo4j("bolt://localhost:7687", "neo4j", "password")
    #cypher_query = CypherQuery(db, sentence)
    query = NewCypherQuery(db, sentence)
    #b = cypher_query.has_valid_relationships()

    cypher = query.construct_query()
    print(cypher)

    db.close()
