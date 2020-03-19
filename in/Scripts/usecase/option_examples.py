# This script provides a template for use case scripts

# The header block describes the script, containing the following information:
#  - Title: this is shown in the scripts view
#  - Description: this is the content of the tooltip
#  - Help: this text is shown in the lower panel of the scripts view when
#          the script is selected
#  - Run: this is the python function called to run the script
#  - Options: this python function returns the configurable options for the script
#  - Validate: this python function checks the users configuration of the script
#
# The script can define multiple functions, each with a header block

# import the package for use case scripts
from arm_ds.usecase_script import UseCaseScript

# import the packages used in the script
from arm_ds.debugger_v1 import Debugger
import sys
import re

"""
USECASE

$Title$ Basic options
$Description$ Demonstrates basic option types
$Run$ main1
$Options$ options1
$Validation$ validate1
$Help$
This script demonstrates some simple options.  The configured options are
printed when the script is run</br>
</br>
The help text can use HTML formatting. For example, a list:
<ul>
<li>Item <b>one</b></li>
<li>Item <i>two</i></li>
<ul>
$Help$
"""

#
# The function should return a list of options - each option can be one of:
#  - booleanOption:
#    A boolean choice, shown by a checkbox on the configuration dialog
#  - enumOption:
#    A selection from a number of values
#    Shown by a drop-down on the configuration dialog
#  - radioEnumOption:
#    A selection from a number of values
#    Shown by radio buttons on the configuration dialog
#  - integerOption:
#    Input box for integer entry
#  - stringOption:
#    Input box for text entry
# Most options require a default value, given by the defaultValue keyword that
# will be used if the user does not specify any other value
#
# The options list can also contain the following elements for information and
# grouping of options:
#  - infoElement:
#    shows a text label
#  - optionGroup:
#    displays several options in a group
#  - tabSet / tabPage
#    displays groups of options on tabs.
#    The tabSet has a number of tabPages, each showing a group of options
#    container for tabPages
# The options within a group are given by the childOptions keyword
#
def options1():
    '''Return the configurable options for the script
    '''
    return [
        # A group of options to show the basic types
        UseCaseScript.optionGroup('group_one', 'Basic options', childOptions=[
            # string
            UseCaseScript.stringOption('text', 'Text',
                description='This is a string option',
                defaultValue="Hello"),
            # integer
            UseCaseScript.integerOption('number', 'Number',
                description='This is an integer option with minimum = 1, maximum = 100',
                defaultValue=49,
                minimum=1, maximum=100),
            # boolean
            UseCaseScript.booleanOption('enable', 'Enable',
                description='This is a boolean option',
                defaultValue=True),
            # enumeration
            UseCaseScript.enumOption('enum', 'Enumeration', values=[
                    ('a', 'Value a'), ('b', 'Value b'), ('c', 'Value c')
                ],
                defaultValue='a'),
        ])
    ]

#
# This method is called to validate the configured values
#
# In this example, the validation function checks that
#  - The text option has at least 5 characters
#  - The number option is a multiple of 7
#
# The option values can be obtained by calling options.getOptionValue() with the
# name of the option to look up.  This returns a value of the appropriate type,
# e.g. for an integerOption it returns an int, so no conversion has to be done
# to use the value
#
# Options within groups are accessed by appending the option name to the group,
# separated by '.', e.g. "group_one.text".
#
def validate1(options):
    textVal = options.getOptionValue("group_one.text")
    if len(textVal) < 5:
        UseCaseScript.error("Option \"Text\" must be at least 5 characters long")
    numVal = options.getOptionValue("group_one.number")
    if numVal % 7 != 0:
        UseCaseScript.error("Option \"Number\" must be a multiple of 7")

#
# This is the main function of the use case
#
# The option values can be obtained by calling options.getOptionValue() with the
# name of the option to look up.  This returns a value of the appropriate type,
# e.g. for an integerOption it returns an int, so no conversion has to be done
# to use the value
#
# Options within groups are accessed by appending the option name to the group,
# separated by '.', e.g. "group_one.text".
#
def main1(options):
    # Print out the configured options
    print "Text is %s" % options.getOptionValue("group_one.text")
    print "Number is %d" % options.getOptionValue("group_one.number")
    print "Enable is %s" % options.getOptionValue("group_one.enable")
    print "Enumeration is %s" % options.getOptionValue("group_one.enum")


"""
USECASE

$Title$ Advanced options
$Description$ Demonstrates using child options, radio enums and tabs in options dailog
$Run$ main2
$Options$ options2
$Help$
This script demonstrates some more advanced options.  The configured options are
printed when the script is run</br>
</br>
The script demonstrates:
<ul>
<li>Using tabs to manage several groups of options</li>
<li>Using a boolean option to enable access to a group of options</li>
<li>Using radio buttons for enumerations</li>
<ul>
$Help$
"""

#
# Options are organised into tabs
#
# This also shows how other functions can be called when generating options
# sets
#
def options2():
    '''Return the configurable options for the script
    '''
    return [
        # Each tabPage must be contained in a tabSet
        UseCaseScript.tabSet('tabs', '', childOptions=[
            # call functions for each tab: this avoids having many levels
            # of indentation
            makeSimpleTab(),
            makeCheckboxTab(),
            makeRadioEnumTab()
            ])
    ]

def makeSimpleTab():
    '''Create a tab page containing some simple options'''
    return UseCaseScript.tabPage('tab_one', "Simple", childOptions=[
        UseCaseScript.infoElement('This tab has some simple options'),
        UseCaseScript.stringOption('text', 'Text',
            description='This is a string option',
            defaultValue="Hello"),
        UseCaseScript.integerOption('number', 'Number',
               description='This is an integer option with minimum = 1, maximum = 100',
               defaultValue=49,
               minimum=1, maximum=100),
    ])

def makeCheckboxTab():
    '''Create a tab page containing some boolean options with children'''
    return UseCaseScript.tabPage('tab_two', "Checkboxes", childOptions=[
        UseCaseScript.infoElement('Enable the checkboxes to configure their sub-options'),
        UseCaseScript.booleanOption('group_one', 'Enable group 1', defaultValue=True,
            childOptions=[
                UseCaseScript.stringOption('name', "Name", defaultValue="A"),
                UseCaseScript.integerOption('value', "Value", defaultValue=0),
                ]),
        UseCaseScript.booleanOption('group_two', 'Enable group 2', defaultValue=False,
            childOptions=[
                UseCaseScript.stringOption('name', "Name", defaultValue="A"),
                UseCaseScript.integerOption('value', "Value", defaultValue=0),
                ]),
    ])

def makeRadioEnumTab():
    '''Create a tab page containing a enum displayed using radio buttons'''
    return UseCaseScript.tabPage('tab_three', "Radio enum", childOptions=[
        UseCaseScript.radioEnumOption('enum', "Enumeration value", values=[
            ('a', 'Value one'),
            # enum values can have a child option that are only enabled
            # when that value is selected
            ('b', 'Value two',
                UseCaseScript.stringOption('name', "Name", defaultValue="Name")),
            ('c', 'Value three')
            ],
            defaultValue='a')
    ])


#
# This is the main function of the use case
#
# The option values can be obtained by calling options.getOptionValue() with the
# name of the option to look up.  This returns a value of the appropriate type,
# e.g. for an integerOption it returns an int, so no conversion has to be done
# to use the value
#
# Options within groups are accessed by appending the option name to the group,
# separated by '.', e.g. "group_one.text".
#
def main2(options):
    # Print out the configured options
    # options from the first tab
    print "Text is %s" % options.getOptionValue("tabs.tab_one.text")
    print "Number is %d" % options.getOptionValue("tabs.tab_one.number")
    # options from the 2nd tab
    if options.getOptionValue("tabs.tab_two.group_one"):
        # first checkbox is enabled
        print "Group one name is %s" % options.getOptionValue("tabs.tab_two.group_one.name")
        print "Group one value is %s" % options.getOptionValue("tabs.tab_two.group_one.value")
    if options.getOptionValue("tabs.tab_two.group_two"):
        # 2nd checkbox is enabled
        print "Group two name is %s" % options.getOptionValue("tabs.tab_two.group_two.name")
        print "Group two value is %s" % options.getOptionValue("tabs.tab_two.group_two.value")
    print "Enumeration is %s" % options.getOptionValue("tabs.tab_three.enum")
