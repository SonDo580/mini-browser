from browser.css.selectors import TagSelector, DescendantSelector

# (selector, property-value pairs)
CSSRule = tuple[TagSelector | DescendantSelector, dict[str, str]]


class ParsingError(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class CSSParser:
    def __init__(self, source: str):
        self.source = source  # inline style value or CSS file content
        self.i: int = 0  # current position while parsing

    # ---------- Utilities ----------
    # -------------------------------
    def __skip_whitespace(self) -> None:
        while self.i < len(self.source) and self.source[self.i].isspace():
            self.i += 1

    def __read_word(self) -> str:
        """Read a "word" token (tag names, properties, values)."""
        start = self.i
        while self.i < len(self.source):
            if self.source[self.i].isalnum() or self.source[self.i] in "#-.%":
                self.i += 1
            else:
                break

        if self.i == start:
            raise Exception("Parsing error")
        return self.source[start : self.i]

    def __consume(self, char: str) -> None:
        """
        Consume a required character.
        Raise error if current character doesn't match.
        """
        if not (self.i < len(self.source) and self.source[self.i] == char):
            raise Exception("Parsing error")
        self.i += 1

    def __ignore_util(self, stop_chars: list[str]) -> str | None:
        """
        For parsing error recovery.
        Advance until one of the stop characters is found and return it.
        Returns None if reach end of string.
        """
        while self.i < len(self.source):
            if self.source[self.i] in stop_chars:
                return self.source[self.i]
            else:
                self.i += 1
        return None

    # ---------- Parse CSS components ----------
    # ------------------------------------------

    def __parse_prop_val(self) -> tuple[str, str]:
        """
        Parse a property-value pair. Example: 'color: red'.
        Return the (property, value) tuple.
        """
        prop = self.__read_word()
        self.__skip_whitespace()
        self.__consume(":")
        self.__skip_whitespace()
        val = self.__read_word()
        return prop.casefold(), val

    def parse_body(self) -> dict[str, str]:
        """
        Parse the body of a rule (or the inline style value).
        Example: 'color: red; font-size: 16px'.
        Return a dictionary of property-value pairs.
        """
        prop_val_pairs: dict[str, str] = {}

        while self.i < len(self.source) and self.source[self.i] != "}":
            try:
                prop, val = self.__parse_prop_val()
                prop_val_pairs[prop] = val
                self.__skip_whitespace()
                self.__consume(";")
                self.__skip_whitespace()
            except Exception:
                # If parsing a pair fail,
                # skip to the next pair or to the end of the body.
                stop_char = self.__ignore_util([";", "}"])
                if stop_char == ";":
                    self.__consume(";")
                    self.__skip_whitespace()
                else:
                    break

        return prop_val_pairs

    def parse_selector(self) -> TagSelector | DescendantSelector:
        """Parse a selector
        - Single tag: 'p'
        - Descendant: 'div p'
        """
        tag = self.__read_word().casefold()
        selector = TagSelector(tag)
        self.__skip_whitespace()

        while self.i < len(self.source) and self.source[self.i] != "{":
            tag = self.__read_word().casefold()
            descendant = TagSelector(tag)
            selector = DescendantSelector(ancestor=selector, descendant=descendant)
            self.__skip_whitespace()

        return selector

    # ---------- Entry point ----------
    # ---------------------------------
    def parse(self) -> list[CSSRule]:
        """Parse the entire CSS string into a list of rules."""
        rules: list[CSSRule] = []

        while self.i < len(self.source):
            try:
                self.__skip_whitespace()
                selector = self.parse_selector()
                self.__consume("{")
                self.__skip_whitespace()
                body = self.parse_body()
                self.__consume("}")
                rules.append((selector, body))
            except Exception:
                # Skip the whole rule if parsing fail
                stop_char = self.__ignore_util(["}"])
                if stop_char == "}":
                    self.__consume("}")
                    self.__skip_whitespace()
                else:
                    break

        return rules
