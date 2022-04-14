from spacy.tokens.doc import Doc as spacy_Doc
from spacy.tokens import Token as spacy_Token
from spacy.tokens.span import Span as spacy_Span
from typing import Union, Tuple
from components.span import Span
from config import SPACY_NOUN_POS_TAGS


class Sentence:
    def __init__(self, doc: spacy_Doc, spans: list[Span] = None):
        self.doc: spacy_Doc = doc

        if spans:
            self.spans = spans  # used for debugging / testing
        else:
            self.spans: list[Span] = []

            # Include non-noun chunks in chunks
            chunks = list(self.doc.noun_chunks)
            # Filter out unwanted noun phrases
            for each in chunks:
                if each.root.pos_ not in SPACY_NOUN_POS_TAGS: chunks.remove(each)

            if len(chunks) > 0:
                sentence_in_chunks = [chunks[0]]
                for index, chunk in enumerate(chunks[1:]):
                    idx_this_start = chunk[0].i
                    idx_prev_end = chunks[index][-1].i
                    between_chunk = self.doc[idx_prev_end+1:idx_this_start]
                    if between_chunk:
                        sentence_in_chunks.append(between_chunk)
                    sentence_in_chunks.append(chunk)
                for chunk in sentence_in_chunks:
                    self.spans.append(Span(chunk))

                trailing_span = self.doc[self.spans[-1].span[-1].i+1:]
                if trailing_span:
                    last_span = self.doc[self.spans[-1].span[0].i:]
                    if last_span[-1].is_punct:
                        last_span = last_span[:-1]
                    self.spans[-1] = Span(last_span)

                starting_span = self.doc[:self.spans[0].span[0].i]
                if starting_span:
                    new_span = self.doc[0:self.spans[0].span[-1].i+1]
                    self.spans = [Span(new_span)] + self.spans[1:]

                # trailing_span = self.doc[self.spans[-1].span[-1].i+1:]
                # if trailing_span:
                #     print("Appending trailing span:", trailing_span)
                #     self.spans.append(Span(trailing_span))
                #
                # starting_span = self.doc[:self.spans[0].span[0].i]
                # print("starting_span", starting_span)
                # if starting_span:
                #     self.spans = [Span(starting_span)] + self.spans

            else:
                # No noun chunks, make just one big span!
                self.spans = [Span(doc[::])]

    def get_all_span_leaves(self) -> list[Span]:
        all_spans = []

        assert(len(self.spans) > 0)

        # if len(self.spans) == 1:
        #     return self.spans[0].get_all_spans()

        for span in self.spans:
            all_spans.extend(span.get_all_spans())
        return all_spans

    def __str__(self):
        """Visualise sentence and it's components"""
        string = self.doc.text + "\n"

        all_spans = self.get_all_span_leaves()

        for i, s in enumerate(all_spans):
            string += str(i) + ("_" * (len(s.span.text) - 1)) + " "
        string += "\n"

        for s in all_spans:
            string += s.get_match_char() + ("_" * (len(s.span.text) - 1)) + " "
        string += "\n"

        return string
