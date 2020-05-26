# using this file will allow the linter to warn on on typos
# and make it easier to globally change a name if required
# it also separate our dict syntax from the xmldict one
# making it easy to change parser if ever required

# we are redefining a pyhon keyword, and are aware of it

# configuration file


def found(word):
    return word and word[0] == '[' and word[-1] == ']'


version = '[version]'

# nodes

node = '[node]'
leafNode = '[leafNode]'
tagNode = '[tagNode]'

owner = '[owner]'

valueless = '[valueless]'
multi = '[multi]'
hidden = '[hidden]'

# properties

priority = '[priority]'

completion = '[completion]'
list = '[list]'
script = '[script]'
path = '[path]'

# valueHelp keys

valuehelp = '[valuehelp]'
format = 'format'
description = 'description'

# constraint

constraint = '[constraint]'
help = '[help]'
summary = '[summary]'
regex = '[regex]'

validator = '[validator]'
name = '[name]'
argument = '[argument]'

error = '[error]'

# created

node = '[node]'
