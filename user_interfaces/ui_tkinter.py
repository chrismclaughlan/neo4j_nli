import tkinter as tk
from typing import Callable


class UITkinter:
    def __init__(self,
                 fn_translate: Callable,
                 fn_execute: Callable,
                 fn_save: Callable,
                 size="800x260",
                 title="Neo4j NLI"):
        self.fn_translate = fn_translate
        self.fn_execute = fn_execute
        self.fn_save = fn_save

        self.tk_root = tk.Tk()
        self.tk_root.tk.call('tk', 'scaling', 2.0)  # tmp
        self.tk_root.geometry(size)
        self.tk_root.title(title)

        # configure the grid
        self.tk_root.columnconfigure(0, weight=0)
        self.tk_root.columnconfigure(1, weight=3)

        # Text Query
        text_query_label = tk.Label(self.tk_root, text="Text Query:")
        text_query_label.grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.text_query_entry = tk.Entry(self.tk_root, width=200)
        self.text_query_entry.grid(column=1, row=0, padx=5, pady=5)
        text_query_button = tk.Button(self.tk_root, text="Translate", width=10, command=self.btn_translate)
        text_query_button.grid(column=2, row=0, sticky=tk.E, padx=5, pady=5)
        self.text_query_entry.bind("<Return>", self.btn_translate)

        # Cypher Query
        cypher_query_label = tk.Label(self.tk_root, text="Cypher Query:")
        cypher_query_label.grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)
        self.cypher_query_entry = tk.Text(self.tk_root, width=150, height=3)
        self.cypher_query_entry.grid(column=1, row=1, padx=5, pady=5)
        cypher_query_button = tk.Button(self.tk_root, text="Execute", width=10, command=self.btn_execute)
        cypher_query_button.grid(column=2, row=1, sticky=tk.E, padx=5, pady=5)
        # self.cypher_query_entry.bind("<Return>", self.btn_execute)

        # Cypher Results
        cypher_results_label = tk.Label(self.tk_root, text="Cypher Results:")
        cypher_results_label.grid(column=0, row=2, sticky=tk.W, padx=5, pady=5)
        self.cypher_results_entry = tk.Text(self.tk_root, width=150, height=5)
        self.cypher_results_entry.grid(column=1, row=2, padx=5, pady=5)
        cypher_results_button = tk.Button(self.tk_root, text="Save", width=10, command=self.btn_save)
        cypher_results_button.grid(column=2, row=2, sticky=tk.E, padx=5, pady=5)
        # self.cypher_results_entry.bind("<Return>", self.btn_save)

    def btn_translate(self, *args):
        self.cypher_results_entry.delete(1.0, tk.END)
        self.cypher_query_entry.delete(1.0, tk.END)

        text = self.text_query_entry.get()
        cypher_query = self.fn_translate(text)

        self.cypher_query_entry.insert(1.0, cypher_query)

    def btn_execute(self, *args):
        self.cypher_results_entry.delete(1.0, tk.END)

        text = self.cypher_query_entry.get(1.0, tk.END)
        cypher_results = self.fn_execute(text)

        self.cypher_results_entry.insert(1.0, cypher_results)

    def btn_save(self, *args):
        text = self.cypher_results_entry.get(1.0, tk.END)

        self.fn_save(text)

    def run(self):
        self.tk_root.mainloop()

    def close(self):
        self.tk_root.destroy()


def translate(text):
    return "MATCH (m) RETURN m"

def execute(text):
    return "[{'node': 'Business', ...}]"

def save():
    pass


if __name__ == "__main__":
    ui = UITkinter(translate, execute, save)
    ui.run()