class Parser:
    class __Parser:
        def __init__(self, data_dir):
            self.data_dir = data_dir
        def read_nodes(self):
            with open(self.data_dir+"nodes.txt", "r") as nodes_data:
                for i, data in enumerate(nodes_data):
                    if i == 0:
    instance = None

    def __init__(self, data_dir):
        if not Parser.instance:
            Parser.instance = Parser.__Parser()
        else:
            Parser.instance.data_dir = data_dir

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def getInstante(self):
        return Parser.instance