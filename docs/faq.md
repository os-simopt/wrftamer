# Frequently asked questions

will be added after the release, once questions are being asked.

# Known Bugs
Bug: I get a yaml.parser.ParserError while running wt create.

Solution: This happens if a list of strings is put into the configure.yaml file.
Replace the list, i.e. parameter: 'string1','string2','string3', with parameter: "'string1','string2','string3'"