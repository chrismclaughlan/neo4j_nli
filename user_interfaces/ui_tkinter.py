import tkinter
import tkinter as tk
from typing import Callable
from functools import partial
from timeit import default_timer as timer


class UITkinter:
    def __init__(self,
                 fn_translate: Callable,
                 fn_execute: Callable,
                 fn_save: Callable,
                 size="1300x260",
                 title="Neo4j NLI"):
        self.fn_translate = fn_translate
        self.fn_execute = fn_execute
        self.fn_save = fn_save
        self.cypherQuery = None  # type == NewCypherQuery

        self.tk_root = tk.Tk()
        self.tk_root.tk.call('tk', 'scaling', 2.0)  # tmp
        self.tk_root.geometry(size)
        self.tk_root.title(title)

        self.tk_root_2 = None

        # configure the grid
        # self.tk_root.columnconfigure(0, weight=0)
        # self.tk_root.columnconfigure(1, weight=3)

        # Text Query
        row = 0
        text_query_label = tk.Label(self.tk_root, text="Text Query:")
        text_query_label.grid(
            column=0, row=row, sticky=tk.W, padx=5, pady=5)
        self.text_query_entry = tk.Entry(self.tk_root, width=100)
        self.text_query_entry.grid(
            column=1, columnspan=2, row=row, padx=5, pady=5)
        text_query_button = tk.Button(self.tk_root, text="Translate", width=10, command=self.btn_translate)
        text_query_button.grid(
            column=4, row=row, sticky=tk.E, padx=5, pady=5)
        self.text_query_entry.bind("<Return>", self.btn_translate)
        #
        # # Text Interpretation
        # OPTIONS = ["Node", "Property", "Parameter"]
        # variable = tk.StringVar(self.tk_root)
        # variable.set(OPTIONS[0])  # default value
        # row += 1
        # one = tk.Label(self.tk_root, text="Wind Speed")
        # one.grid(column=1, row=row, stick=tk.E)
        # two = tk.OptionMenu(self.tk_root, variable, *OPTIONS)
        # two.grid(column=2, row=row, stick=tk.W)
        # row += 1
        # one = tk.Label(self.tk_root, text="Date")
        # one.grid(column=1, row=row, stick=tk.E)
        # two = tk.OptionMenu(self.tk_root, variable, *OPTIONS)
        # two.grid(column=2, row=row, stick=tk.W)
        # row += 1
        # one = tk.Label(self.tk_root, text="#2018/01/01,04:00:00")
        # one.grid(column=1, row=row, stick=tk.E)
        # two = tk.OptionMenu(self.tk_root, variable, *OPTIONS)
        # two.grid(column=2, row=row, stick=tk.W)

        # Cypher Query
        row += 1
        cypher_query_label = tk.Label(self.tk_root, text="Cypher Query:")
        cypher_query_label.grid(
            column=0, row=row, sticky=tk.W, padx=5, pady=5)
        self.cypher_query_entry = tk.Text(self.tk_root, width=75, height=3)
        self.cypher_query_entry.grid(
            column=1, columnspan=2, row=row, padx=5, pady=5)
        cypher_query_button = tk.Button(self.tk_root, text="Execute", width=10, command=self.btn_execute)
        cypher_query_button.grid(
            column=4, row=row, sticky=tk.E, padx=5, pady=5)
        # self.cypher_query_entry.bind("<Return>", self.btn_execute)

        # Cypher Results
        row += 1
        cypher_results_label = tk.Label(self.tk_root, text="Cypher Results:")
        cypher_results_label.grid(
            column=0, row=row, sticky=tk.W, padx=5, pady=5)
        self.cypher_results_entry = tk.Text(self.tk_root, width=75, height=5)
        self.cypher_results_entry.grid(
            column=1, columnspan=2, row=row, padx=5, pady=5)
        cypher_results_button = tk.Button(self.tk_root, text="Save", width=10, command=self.btn_save)
        cypher_results_button.grid(
            column=4, row=row, sticky=tk.E, padx=5, pady=5)
        # self.cypher_results_entry.bind("<Return>", self.btn_save)

    def opt_toggle_match(self, *args):
        for s in self.cypherQuery.sentence.get_all_span_leaves():
            if s == args[0]:
                s.ignoreMatches = not s.ignoreMatches
                break
        cypher_query_text = self.cypherQuery.construct_query(sort=False)
        self.cypher_query_entry.delete(1.0, tk.END)
        self.cypher_query_entry.insert(1.0, cypher_query_text)

    def opt_adjust_match(self, *args):
        for s in self.cypherQuery.sentence.get_all_span_leaves():
            if s == args[0]:
                # Place arg[1] to front of s.matches
                if s.matches[0] == args[1]: break
                new_matches = s.matches[::]
                new_matches.remove(args[1])
                new_matches = [args[1]] + new_matches
                s.matches = new_matches
                break
        cypher_query_text = self.cypherQuery.construct_query(sort=False)
        self.cypher_query_entry.delete(1.0, tk.END)
        self.cypher_query_entry.insert(1.0, cypher_query_text)

    def btn_translate(self, *args):
        print("UITKinter - Translating Query")
        self.cypher_results_entry.delete(1.0, tk.END)

        text = self.text_query_entry.get()

        start = timer()
        self.cypherQuery = self.fn_translate(text)
        cypher_query_text = self.cypherQuery.construct_query()
        end = timer()
        print("UITKinter - Translating Query took", end - start, "seconds")


        self.cypher_query_entry.delete(1.0, tk.END)
        self.cypher_query_entry.insert(1.0, cypher_query_text)

        # Create second window
        if self.tk_root_2:
            self.tk_root_2.destroy()
        self.tk_root_2 = tkinter.Toplevel(self.tk_root)
        row = 0
        one = tk.Label(self.tk_root_2, text="Key Concepts identified in sentence. "
                                            "Use dropdowns to adjust matching db components.")
        one.grid(row=row, column=0, columnspan=3)

        spans = self.cypherQuery.sentence.get_all_span_leaves()
        print(spans)
        for s in spans:
            options = [m for m in s.matches]
            if not options: continue
            variable = tk.StringVar(self.tk_root_2)
            variable.set(options[0])  # default value
            row += 1
            one = tk.Label(self.tk_root_2, text=str(s))
            one.grid(column=1, row=row, stick=tk.E)
            #if len(options) > 1:
                #options = options[1:]
            two = tk.OptionMenu(self.tk_root_2, variable, *options, command=partial(self.opt_adjust_match, s))
            two.grid(column=2, row=row, stick=tk.W)
            three = tk.Button(self.tk_root_2, text="Toggle", width=10, command=partial(self.opt_toggle_match, s))
            three.grid(column=3, row=row, stick=tk.W)

        #
        # # Text Interpretation
        # OPTIONS = ["Node", "Property", "Parameter"]
        # variable = tk.StringVar(self.tk_root_2)
        # variable.set(OPTIONS[0])  # default value
        # row += 1
        # one = tk.Label(self.tk_root_2, text="Wind Speed")
        # one.grid(column=1, row=row, stick=tk.E)
        # two = tk.OptionMenu(self.tk_root_2, variable, *OPTIONS)
        # two.grid(column=2, row=row, stick=tk.W)
        # row += 1
        # one = tk.Label(self.tk_root_2, text="Date")
        # one.grid(column=1, row=row, stick=tk.E)
        # two = tk.OptionMenu(self.tk_root_2, variable, *OPTIONS)
        # two.grid(column=2, row=row, stick=tk.W)
        # row += 1
        # one = tk.Label(self.tk_root_2, text="#2018/01/01,04:00:00")
        # one.grid(column=1, row=row, stick=tk.E)
        # two = tk.OptionMenu(self.tk_root_2, variable, *OPTIONS)
        # two.grid(column=2, row=row, stick=tk.W)

    def btn_execute(self, *args):
        print("UITKinter - Executing Query")
        #self.tk_root_2.destroy()

        self.cypher_results_entry.delete(1.0, tk.END)

        text = self.cypher_query_entry.get(1.0, tk.END)
        cypher_results = self.fn_execute(text)
        if not cypher_results:
            cypher_results = "Could not find any results!"
        self.cypher_results_entry.insert(1.0, cypher_results)

    def btn_save(self, *args):
        print("UITKinter - Saving Results")
        text = self.cypher_results_entry.get(1.0, tk.END)

        self.fn_save(text)

    def run(self):
        print("UITKinter - Run")
        self.tk_root.mainloop()

    def close(self):
        self.tk_root.destroy()


# def translate(text):
#     return
#
# def execute(text):
#     return "[{'node': 'Business', ...}]"
#
# def save():
#     pass
#
#
# if __name__ == "__main__":
#     ui = UITkinter(translate, execute, save)
#     ui.run()