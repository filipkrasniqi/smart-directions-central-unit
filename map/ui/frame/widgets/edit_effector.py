from map.ui.frame.widgets.edit_node import EditNode

'''
UI associated with the update of an effector.
It entirely resembles the anchor one.
'''
class EditEffector(EditNode):
    def __init__(self, master, node):
        EditNode.__init__(self, master, node)