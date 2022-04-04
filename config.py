import spacy
import subprocess, sys

SPACY_MODEL_PIPELINE = "en_core_web_lg"

try:
    nlp = spacy.load(SPACY_MODEL_PIPELINE)
except OSError as e:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "spacy",
            "download",
            SPACY_MODEL_PIPELINE
        ]
    )
    nlp = spacy.load(SPACY_MODEL_PIPELINE)

# Split words with '_' seperating them. Eg: ['find_all', ...] -> ['find', 'all', ...]
infixes = nlp.Defaults.infixes + [r'''_''', ]
infix_regex = spacy.util.compile_infix_regex(infixes)
nlp.tokenizer.infix_finditer = infix_regex.finditer

prefixes = list(nlp.Defaults.prefixes)
prefixes.remove('#')
prefix_regex = spacy.util.compile_prefix_regex(prefixes)
nlp.tokenizer.prefix_search = prefix_regex.search

SPACY_NOUN_POS_TAGS = ["NOUN", "PROPN"]
