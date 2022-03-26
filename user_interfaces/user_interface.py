# TODO add more functionality... maybe with external library

closeMessages = ["close", "quit", "exit"]

class UserInterface:
    def __init__(self):
        # self.keepAlive = True  # False to close application
        pass

    def wait_for_event(self):
        text = input("Enter Natural Language Query: ")

        if text.lower() in closeMessages:
            return "QUIT", "User input 'quit'"

        return "QUERY", text

    def display_results(self, results):
        print(results)
