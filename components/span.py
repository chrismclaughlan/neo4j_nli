from spacy.tokens.doc import Doc as spacy_Doc
from spacy.tokens import Token as spacy_Token
from spacy.tokens.span import Span as spacy_Span
from typing import Union, Tuple
from db_management_system.types import Match, Command, Node, Relationship, Property, Parameter
from config import SPACY_NOUN_POS_TAGS


class Span:
    def __init__(self, span: spacy_Span, matches: list[Match] = None):
        self.span: spacy_Span = span

        self.children: list[Span] = []  # new

        self.spanL: Union[Span, None] = None
        self.spanR: Union[Span, None] = None

        self.matches: list[Match] = matches if matches else []
        self.matchTried: bool = False

        self.numNouns: int = 0
        for token in span:
            if token.pos_ in SPACY_NOUN_POS_TAGS:
                self.numNouns += 1

        self.ignoreMatches = False

    def __len__(self):
        return len(self.span)

    def __str__(self):
        return self.span.text

    def __repr__(self):
        return self.span.text

    def get_similarity(self, doc: spacy_Doc) -> float:
        similarity = 0.0

        if self.span and self.span.vector_norm and doc and doc.vector_norm:
            if len(self.span) == 1 and self.span[0].is_stop:
                similarity = 0
            else:
                similarity = self.span.similarity(doc)

                if len(self.span) == 1 and self.span.text.lower() in doc.text.lower():
                    similarity += 0.5
                #print(self.span, doc, similarity)
        else:
            #print("Cannot find similarity, either does not have a vector norm!", self, doc)
            # TODO also check if exactly sub-string?
            pass

        return similarity

    def get_match_char(self) -> str:
        if self.matches: return self.matches[0].match.visualisationChar  # TODO which match
        else: return "?"

    def sort_by_most_confident_match(self):
        if not self.matches:
            return None
        self.matches.sort(key=lambda match: match.confidence)

    def get_all_spans(self) -> list['Span']:
        """Returns itself if no children, otherwise return children"""
        if not self.children: return [self]

        all_spans: list[Span] = []
        for child in self.children:
            all_spans.extend(child.get_all_spans())
        return all_spans

    def split(self) -> bool:  # TODO Split context from nouns first! Then start splitting nouns. Eg. "How many Wind Mills..." to ["How many", "Wind Mills"]
        """Returns True if span was split, otherwise False."""

        if len(self.span) < 2:
            return False
        elif len(self.span) == 2:
            self.children.append(Span(self.span[:1]))
            self.children.append(Span(self.span[1:]))
            return True

        new_spans_t: list[list[spacy_Token]] = [[self.span[0]]]  # list of new spans wher they are lists of tokens (not spacy_Span yet!)
        if self.numNouns > 0:

            for token in self.span[1:]:

                if token.pos_ in SPACY_NOUN_POS_TAGS:
                    if new_spans_t[-1][-1].pos_ in SPACY_NOUN_POS_TAGS:
                        new_spans_t[-1].append(token)
                    else:
                        new_spans_t.append([token])
                else:
                    if new_spans_t[-1][-1].pos_ not in SPACY_NOUN_POS_TAGS:
                        new_spans_t[-1].append(token)
                    else:
                        new_spans_t.append([token])
        else:
            # Split span at span root
            if self.span[0] == self.span.root:
                new_spans_t.append([token for token in self.span[1:]])
            else:
                for index, token in enumerate(self.span[1:]):
                    index += 1  # compentate for shifting list by 1

                    if token == self.span.root:
                        new_spans_t.append([token for token in self.span[index:]])
                        break
                    else:
                        new_spans_t[-1].append(token)

        for each in new_spans_t:
            start_i: int = each[0].i
            end_i: int = each[-1].i
            new_span: spacy_Span = self.span.doc[start_i:end_i+1]
            self.children.append(Span( new_span ))

        if len(new_spans_t) == 1:
            return False  # Didn't split, it's the same!

        return True
