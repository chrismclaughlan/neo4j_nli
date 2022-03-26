import spacy

#nlp = spacy.load("en_core_web_sm")
nlp = spacy.load("en_core_web_md")
# Split words with '_' seperating them. Eg: ['find_all', ...] -> ['find', 'all', ...]
infixes = nlp.Defaults.infixes + [r'''_''', ]
indix_regex = spacy.util.compile_infix_regex(infixes)
nlp.tokenizer.infix_finditer = indix_regex.finditer