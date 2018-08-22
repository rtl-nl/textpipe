# pylint: disable=too-many-instance-attributes
"""
Clean text, make it readable and obtain metadata from it.
"""

import functools
import re

import cld2
import spacy
import textacy
import textacy.text_utils
from bs4 import BeautifulSoup

from textpipe.utils import hash_dict


class TextpipeMissingModelException(Exception):
    """Raised when the requested model is missing"""
    pass


class Doc:  # pylint: disable=too-many-arguments
    """
    Create a doc instance of text, obtain cleaned, readable text and
    metadata from this doc.

    Properties:
    raw: incoming, unedited text
    language: 2-letter code for the language of the text
    hint_language: language you expect your text to be
    _spacy_nlps: dictionary containing loaded spacy language modules
    """

    def __init__(self, raw, language=None, hint_language='en', spacy_nlps=None):
        self.raw = raw
        self.is_detected_language = language is None
        self.hint_language = hint_language
        self._spacy_nlps = spacy_nlps or dict()
        self._spacy_docs = {}
        self._text_stats = {}

    @property
    def language(self):
        """
        Provided or detected language of a text

        >>> from textpipe.doc import Doc
        >>> Doc('Test sentence for testing text').language
        'en'
        >>> Doc('Test sentence for testing text', language='en').language
        'en'
        >>> Doc('Test', hint_language='nl').language
        'nl'
        """
        return self.detect_language(self.hint_language)

    @functools.lru_cache()
    def detect_language(self, hint_language=None):
        """
        Detected the language of a text if no language was provided along with the text

        Args:
        hint_language: language you expect your text to be

        Returns:
        language: 2-letter code for the language of the text

        >>> from textpipe.doc import Doc
        >>> doc = Doc('Test')
        >>> doc.language
        'en'
        >>> doc.detect_language('nl')
        'nl'
        """
        _, _, best_guesses = cld2.detect(self.clean, hintLanguage=hint_language,
                                         bestEffort=True)
        return best_guesses[0][1]

    def _spacy_doc(self, model_name=None):
        """
        Loads a spacy doc or creates one if necessary

        >>> doc = Doc('Test sentence for testing text')
        >>> type(doc._spacy_doc())
        <class 'spacy.tokens.doc.Doc'>
        """
        lang = self.hint_language if self.language == 'un' else self.language
        # Load default spacy model if necessary, if not loaded already
        if lang not in self._spacy_nlps or (model_name is None and
                                            model_name not in self._spacy_nlps[lang]):
            self._set_default_nlp(lang)
        if model_name in self._spacy_docs:
            doc = self._spacy_docs[model_name]
        else:
            if model_name not in self._spacy_nlps[lang] and model_name is not None:
                raise TextpipeMissingModelException(f'Custom model {model_name} '
                                                    f'is missing.')
            else:
                nlp = self._spacy_nlps[lang][model_name]
                doc = self._spacy_docs[model_name] = nlp(self.clean_text())
        return doc

    @property
    def clean(self):
        """
        Cleaned text with sensible defaults.

        >>> doc = Doc('“Please clean this piece… of text</b>„')
        >>> doc.clean
        '"Please clean this piece... of text"'
        """
        return self.clean_text()

    @functools.lru_cache()
    def clean_text(self, remove_html=True, clean_dots=True, clean_quotes=True,
                   clean_whitespace=True):
        """
        Clean HTML and normalise punctuation.

        >>> doc = Doc('“Please clean this piece… of text</b>„')
        >>> doc.clean_text(False, False, False, False) == doc.raw
        True
        """
        text = self.raw
        if remove_html:
            text = BeautifulSoup(text, 'html.parser').get_text()  # remove HTML

        # Three regexes below adapted from Blendle cleaner.py
        # https://github.com/blendle/research-summarization/blob/master/enrichers/cleaner.py#L29
        if clean_dots:
            text = re.sub(r'…', '...', text)
        if clean_quotes:
            text = re.sub(r'[`‘’‛⸂⸃⸌⸍⸜⸝]', "'", text)
            text = re.sub(r'[„“]|(\'\')|(,,)', '"', text)
        if clean_whitespace:
            text = re.sub(r'\s+', ' ', text).strip()

        return text

    @property
    def ents(self):
        """
        A list of the named entities with sensible defaults.

        >>> doc = Doc('Sentence for testing Google text')
        >>> doc.ents
        [('Google', 'ORG')]
        """
        return self.find_ents()

    @hash_dict
    @functools.lru_cache()
    def find_ents(self, model_mapping=None):
        """
        Extract a list of the named entities in text, with the possibility of using a custom model.
        >>> doc = Doc('Sentence for testing Google text')
        >>> doc.find_ents()
        [('Google', 'ORG')]
        """
        lang = self.hint_language if self.language == 'un' else self.language
        model_name = model_mapping.get(lang, None) if model_mapping else None
        return list({(ent.text, ent.label_) for ent in self._spacy_doc(model_name).ents})

    @property
    def nsents(self):
        """
        Extract the number of sentences from text

        >>> doc = Doc('Test sentence for testing text.')
        >>> doc.nsents
        1
        """
        return len(list(self._spacy_doc().sents))

    @property
    def nwords(self):
        """
        Extract the number of words from text

        >>> doc = Doc('Test sentence for testing text')
        >>> doc.nwords
        5
        """
        return len(self.clean.split())

    @property
    def complexity(self):
        """
        Determine the complexity of text using the Flesch
        reading ease test ranging from 0.0 - 100.0 with 0.0
        being the most difficult to read.

        >>> doc = Doc('Test sentence for testing text')
        >>> doc.complexity
        83.32000000000004
        """
        if not self._text_stats:
            self._text_stats = textacy.TextStats(self._spacy_doc())
        if self._text_stats.n_syllables == 0:
            return 100
        return self._text_stats.flesch_reading_ease

    def _set_default_nlp(self, lang):
        """
        Loads the spacy default language module for the Doc's language into the _spacy_nlps object
        """
        if lang not in self._spacy_nlps:
            self._spacy_nlps[lang] = {}
        model = spacy.load('{}_core_{}_sm'.format(lang, 'web' if lang == 'en' else 'news'))
        self._spacy_nlps[lang][None] = model
