from interpreter.nl_interpreter import NLInterpreter
import config
nlp = config.nlp


# TODO base class for relationships and nodes
class Relationship:
    def __init__(self, name, source, target, props=None):
        if props is None:
            props = []

        self.name = name
        self.sourceNode = source
        self.targetNode = target
        self.props = props

        self.namesReadable = ""
        for i, token in enumerate(NLInterpreter.process_text(name)):
            if not token.is_punct:
                if i == 0:
                    self.namesReadable += token.text.lower()
                else:
                    self.namesReadable += " " + token.text.lower()
        self.namesReadable = nlp(self.namesReadable)

    def add_property(self, property_name):
        if property_name not in self.props:
            self.props.append(property_name)

    def __repr__(self):
        # Format similar to CYPHER
        if self.props:
            props = ""
            for each in self.props:
                props += f"'{each}',"
            return f"({self.sourceNode})-[:{self.name} {{{props[:-1]}}}]->({self.targetNode})"
        else:
            return f"({self.sourceNode})-[:{self.name}]->({self.targetNode})"