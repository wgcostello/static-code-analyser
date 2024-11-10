import ast
import operator
import os
import re
import sys

MAXIMUM_LINE_LENGTH = 79

args = sys.argv
path = args[1]


def indentation_not_multiple_of_four(line):
    if re.match(r'^(\s{4})*\S', line):
        return False
    return True


def unnecessary_semicolon(line):
    in_string = False
    quotes = ''

    for character in line:
        if in_string:
            if character == quotes:
                in_string = False
        else:
            if character in ("'", '"'):
                in_string = True
                quotes = character
            if character == '#':
                break
            if character == ';':
                return True
    else:
        return False


def less_than_two_spaces_before_inline_comments(line):
    if re.match(r'[^#]*[^\s#]+\s?#.*', line):
        return True
    return False


def todo_found(line):
    if re.match(r'.*#.*[Tt][Oo][Dd][Oo].*', line):
        return True
    return False


def too_many_spaces_after_construction_name(line):
    match = re.search(r'(def|class)\s{2,}', line)
    if match:
        return match.group(1)
    return None


def name_not_camel_case(name):
    if re.match(r'(?:[A-Z][a-z_]*)+', name):
        return False
    return True


def name_not_snake_case(name):
    if re.match(r'[a-z_]+', name):
        return False
    return True


class ErrorMessage:
    def __init__(self, filepath, line_number, key, name=None):
        self.filepath = filepath
        self.line_number = line_number
        self.key = key
        self.name = name
        self.message = self.generate_error_message()

    def __repr__(self):
        return (
            f"{self.filepath}: Line {self.line_number}: S{self.key:03d} "
            f"{self.message}"
        )

    def generate_error_message(self):
        if self.key == 1:
            return "Too long"
        elif self.key == 2:
            return "Indentation not a multiple of 4"
        elif self.key == 3:
            return "Unnecessary semicolon"
        elif self.key == 4:
            return "At least two spaces required before inline comments"
        elif self.key == 5:
            return "TODO found"
        elif self.key == 6:
            return "More than two blank lines used before this line"
        elif self.key == 7:
            return f"Too many spaces after {self.name}"
        elif self.key == 8:
            return f"Class name '{self.name}' should use CamelCase"
        elif self.key == 9:
            return f"Function name '{self.name}' should use snake_case"
        elif self.key == 10:
            return f"Argument name '{self.name}' should use snake_case"
        elif self.key == 11:
            return f"S011 Variable name '{self.name}' should use snake_case"
        elif self.key == 12:
            return f"Default argument value is mutable"


class CodeAnalyser(ast.NodeVisitor):
    def __init__(self, filepath):
        self.filepath = filepath
        self.current_line_number = 1
        self.in_function = False
        self.errors = []

    def log_error(self, line_number, key, name=None):
        self.errors.append(ErrorMessage(
            self.filepath, line_number, key, name
        ))

    def generic_visit(self, node):
        if isinstance(node, (ast.expr, ast.stmt)):
            self.current_line_number = node.lineno
        ast.NodeVisitor.generic_visit(self, node)

    def visit_ClassDef(self, node):
        if name_not_camel_case(node.name):
            self.log_error(node.lineno, 8, name=node.name)
        self.generic_visit(node)
        self.outside_class = True

    def visit_FunctionDef(self, node):
        self.in_function = True
        if name_not_snake_case(node.name):
            self.log_error(node.lineno, 9, name=node.name)
        self.generic_visit(node)
        self.in_function = False

    def visit_arg(self, node):
        if name_not_snake_case(node.arg):
            self.log_error(self.current_line_number, 10, name=node.arg)
        self.generic_visit(node)

    def visit_Name(self, node):
        if name_not_snake_case(node.id) and self.in_function:
            self.log_error(self.current_line_number, 11, name=node.id)
        self.generic_visit(node)

    def visit_arguments(self, node):
        for default_arg in node.defaults + node.kw_defaults:
            if isinstance(default_arg, (ast.List, ast.Dict, ast.Set)):
                self.log_error(self.current_line_number, 12)
                break
        self.generic_visit(node)

    def report_errors(self):
        self.errors.sort(key=operator.attrgetter('line_number', 'key'))
        variable_names = []
        for error in self.errors:
            if error.key == 11:
                if error.name in variable_names:
                    continue
                else:
                    variable_names.append(error.name)
            print(error)


filepaths = []

if os.path.isfile(path):
    filepaths.append(path)
elif os.path.isdir(path):
    for root, __, files in os.walk(path):
        for filename in files:
            if filename.endswith('.py'):
                filepaths.append(os.path.join(root, filename))

    filepaths.sort()

for filepath in filepaths:
    code_analyser = CodeAnalyser(filepath)

    with open(filepath, 'r') as file:
        blank_line_counter = 0
        for number, line in enumerate(file, start=1):
            if line.strip():
                if len(line) > MAXIMUM_LINE_LENGTH:
                    code_analyser.log_error(number, 1)
                if indentation_not_multiple_of_four(line):
                    code_analyser.log_error(number, 2)
                if unnecessary_semicolon(line):
                    code_analyser.log_error(number, 3)
                if less_than_two_spaces_before_inline_comments(line):
                    code_analyser.log_error(number, 4)
                if todo_found(line):
                    code_analyser.log_error(number, 5)
                if blank_line_counter > 2:
                    code_analyser.log_error(number, 6)
                construction_name = too_many_spaces_after_construction_name(
                    line
                )
                if construction_name:
                    code_analyser.log_error(
                        number, 7, name=construction_name
                    )

                blank_line_counter = 0
            else:
                blank_line_counter += 1

    with open(filepath, 'r') as file:
        tree = ast.parse(file.read())

    code_analyser.visit(tree)
    code_analyser.report_errors()
