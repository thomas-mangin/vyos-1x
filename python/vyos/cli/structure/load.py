#!/usr/bin/env python3

import os
import glob

import xmltodict

import vyos.cli.structure.keywords as kw


def safe_update(dict1, dict2):
    if not isinstance(dict2, dict):
        # raise RuntimeError('we messed up')
        breakpoint()
        print()

    if set(dict1).intersection(dict2):
        # raise RuntimeError('we messed up')
        breakpoint()
        print()
    return {**dict1, **dict2}


def merge(dict1, dict2):
    """
    merge dict2 in to dict1
    """
    for k2 in list(dict2):
        if k2 not in dict1:
            dict1[k2] = dict2[k2]
            continue
        if isinstance(dict1[k2], dict) and isinstance(dict2[k2], dict):
            dict1[k2] = merge(dict1[k2], dict2[k2])
        elif isinstance(dict1[k2], dict) and isinstance(dict2[k2], dict):
            dict1[k2].extend(dict2[k2])
        elif dict1[k2] == dict2[k2]:
            # A definition shared between multiple file is not consistent
            # raise RuntimeError('they? messed up')
            pass
        else:
            # raise RuntimeError('we messed up')
            breakpoint()
            print()
    return dict1


def xml_include(definition_folder, fname):
    content = ''
    with open(os.path.join(definition_folder, fname), 'r') as r:
        for line in r.readlines():
            if '#include' in line:
                content += xml_include(definition_folder,line.strip()[10:-1])
                continue
            content += line
    return content


def xml_in(definition_folder):
    configuration = dict()
    for fname in glob.glob(f'{definition_folder}/*.xml.in'):
        parsed = xmltodict.parse(xml_include(definition_folder, fname[len(definition_folder) + 1:]))
        formated = format_nodes(parsed['interfaceDefinition'])
        configuration = merge(configuration, formated)
    return configuration


def format_nodes(conf):
    r = {}
    while conf:
        nodetype = ''
        nodename = ''
        if 'node' in conf.keys():
            nodetype = 'node'
            nodename = kw.node
        elif 'leafNode' in conf.keys():
            nodetype = 'leafNode'
            nodename = kw.leafNode
        elif 'tagNode' in conf.keys():
            nodetype = 'tagNode'
            nodename = kw.tagNode
        elif 'syntaxVersion' in conf.keys():
            r[kw.version] = conf.pop('syntaxVersion')['@version']
            continue
        else:
            breakpoint()
            print(conf.keys())

        nodes = conf.pop(nodetype)
        if isinstance(nodes, list):
            for node in nodes:
                name = node.pop('@name')
                r[name] = format_node(node)
                r[name][kw.node] = nodename
        else:
            node = nodes
            name = node.pop('@name')
            r[name] = format_node(node)
            r[name][kw.node] = nodename
    return r


def set_validator(r, validator):
    v = {}
    while validator:
        if '@name' in validator:
            v[kw.name] = validator.pop('@name')
        elif '@argument' in validator:
            v[kw.argument] = validator.pop('@argument')
        else:
            breakpoint()
            print(validator)
    r[kw.constraint][kw.validator].append(v)


def format_node(conf):
    r = {
        kw.valueless: False,
        kw.multi: False,
        kw.hidden: False,
    }

    if '@owner' in conf:
        r[kw.owner] = conf.pop('@owner', '')

    while conf:
        if 'children' in conf.keys():
            children = conf.pop('children')

            if isinstance(conf, list):
                for child in children:
                    r = safe_update(r, format_nodes(child))
            else:
                child = children
                r = safe_update(r, format_nodes(child))

        elif 'properties' in conf.keys():
            properties = conf.pop('properties')

            while properties:
                if 'help' in properties:
                    helpname = properties.pop('help')
                    r[kw.help] = {}
                    r[kw.help][kw.summary] = helpname

                elif 'valueHelp' in properties:
                    valuehelps = properties.pop('valueHelp')
                    if kw.valuehelp in r[kw.help]:
                        breakpoint()
                        print(valuehelps)
                    r[kw.help][kw.valuehelp] = []
                    if isinstance(valuehelps, list):
                        for valuehelp in valuehelps:
                            r[kw.help][kw.valuehelp].append(dict(valuehelp))
                    else:
                        valuehelp = valuehelps
                        r[kw.help][kw.valuehelp].append(dict(valuehelp))

                elif 'constraint' in properties:
                    constraint = properties.pop('constraint')
                    r[kw.constraint] = {}
                    while constraint:
                        if 'regex' in constraint:
                            regexes = constraint.pop('regex')
                            if kw.regex in kw.constraint:
                                breakpoint()
                                print(regexes)
                            r[kw.constraint][kw.regex] = []
                            if isinstance(regexes, list):
                                r[kw.constraint][kw.regex] = []
                                for regex in regexes:
                                    r[kw.constraint][kw.regex].append(regex)
                            else:
                                regex = regexes
                                r[kw.constraint][kw.regex].append(regex)
                        elif 'validator' in constraint:
                            validators = constraint.pop('validator')
                            if kw.validator in r[kw.constraint]:
                                breakpoint()
                                print(validators)
                            r[kw.constraint][kw.validator] = []
                            if isinstance(validators, list):
                                for validator in validators:
                                    set_validator(r, validator)
                            else:
                                validator = validators
                                set_validator(r, validator)
                        else:
                            breakpoint()
                            print(constraint)

                elif 'constraintErrorMessage' in properties:
                    r[kw.error] = properties.pop('constraintErrorMessage')

                elif 'valueless' in properties:
                    properties.pop('valueless')
                    r[kw.valueless] = True

                elif 'multi' in properties:
                    properties.pop('multi')
                    r[kw.multi] = True

                elif 'hidden' in properties:
                    properties.pop('hidden')
                    r[kw.hidden] = True

                elif 'completionHelp' in properties:
                    completionHelp = properties.pop('completionHelp')
                    r[kw.completion] = {}
                    while completionHelp:
                        if 'list' in completionHelp:
                            r[kw.completion][kw.list] = completionHelp.pop('list')
                        elif 'script' in completionHelp:
                            r[kw.completion][kw.script] = completionHelp.pop('script')
                        elif 'path' in completionHelp:
                            r[kw.completion][kw.path] = completionHelp.pop('path')
                        else:
                            breakpoint()
                            print(completionHelp.keys())

                elif 'priority' in properties:
                    r[kw.priority] = int(properties.pop('priority'))
                else:
                    breakpoint()
                    print(properties.keys())
        else:
            breakpoint()
            print(conf)

    return r
