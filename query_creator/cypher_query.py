ALPHABET = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]


class CypherElementBase:
    def __init__(self, _label, _target_prop=None, _constraints=None):
        self.label = _label
        self.targetProp = _target_prop
        self.constraints = _constraints


class CypherNode(CypherElementBase):
    def __repr__(self):
        if self.constraints:
            constraints = ""
            for key, value in self.constraints.items():
                constraints += key + ": " + "'" + value + "'"

            return self.label + "{" + constraints + "}"
        else:
            return self.label


class CypherRelationship(CypherElementBase):
    def __repr__(self):
        # TODO
        return "TODO"


class CypherQuery:
    def __init__(self, target_node=None, related_nodes=None, return_command=""):
        self.targetNode = target_node  # Goes inside MATCH( ) statement
        if related_nodes is None: self.relatedNodes = []
        else: self.relatedNodes = related_nodes
        self.returnCommand = return_command  # Appears at end of query after RETURN statement. Eg RETURN COUNT( )

    def get_query(self):
        # assert(...) ... Make sure syntax is okay.

        if self.targetNode is None:
            print("No target node found, cannot execute query!")
            print("Related nodes:", self.relatedNodes)
            print("Return command:", self.returnCommand)
            return None

        possible_variable_names = ALPHABET[:]  # Used to get names for query variables

        # Configure variable names for target node
        target_alias = possible_variable_names.pop()
        return_prop = target_alias

        # Build query string
        related_nodes = ""
        for node in self.relatedNodes:
            # TODO 1. Ordering of related nodes!
            #      2. Incorporate relations between related nodes!
            related_nodes += f"--({possible_variable_names.pop()}:{node})"

        if self.targetNode.targetProp:
            return_prop = target_alias + "." + self.targetNode.targetProp  # Add target prop to RETURN statement

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
