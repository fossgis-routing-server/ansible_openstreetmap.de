#! /usr/bin/env python3

class FilterModule:
    def filters(self):
        return {'e_php_single_quote': self.e_php_single_quote}

    def e_php_single_quote(self, raw):
        '''Escape a raw string to be inserted in a PHP string literal surrounded by single quotes.

        See https://www.php.net/manual/en/language.types.string.php for details.
        '''
        escaped = ''
        for char in raw:
            if char == "'":
                escaped += '\\\''
            elif char == '\\':
                escaped += '\\\\'
            else:
                escaped += char
        return escaped
