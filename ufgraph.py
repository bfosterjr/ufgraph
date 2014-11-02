import sys
import os
import tempfile
import uuid
import time
import subprocess

try:
	from graphviz import Digraph
	has_graphviz = True
except ImportError:
	has_graphviz = False

class dotnode:
    def __init__(self, name):
        self.node_name = name
        self.label_text = []
        self.connecting_nodes = []

    def get_nodeName(self):
        return self.node_name

    def get_connections(self):
        return self.connecting_nodes

    def add_label_text(self, text):
        self.label_text += [text]

    def add_connection(self, node_name):
        self.connecting_nodes += [node_name]

    def get_dotformat_node(self):
        dotstr = self.node_name
        dotstr += "[label=\""
        dotstr += self.get_dotformat_label()
        dotstr += "\"]"
        return dotstr

    def get_dotformat_label(self):
        label = ""
        for label_line in self.label_text:
			#force it to be left justified
            label += label_line + "\\l"
        return label

    def get_dotformat_connections(self):
        connections = ""
        for node in self.connecting_nodes:
            connections += self.node_name
            connections += " -> "
            connections += node
            connections += "\n"
        return connections


def build_nodes():
    nodes = []
    last_line_jump = False
    last_line_ret = False
    new_node = None
    last_node = None

    for line in sys.stdin:
        line = line.strip()
        if line.rstrip().endswith(":"):
            #get the new node name
            # graphviz doesn't like "!" or "+".. in node names so strip them
            new_name = line.split(":")[0].replace("!","").replace("+","")

            #make the connection to the new node if necessary
            if None != last_node:
                if not last_line_jump and not last_line_ret:
                    last_node.add_connection(new_name)

            #now create a new node
            new_node = dotnode(new_name)

        elif line.strip() == "":
            #if we have a node, its done, so add it
            if new_node:
                nodes += [new_node]
                last_node = new_node
                new_node = None
            pass
        elif not new_node:
            #.. this shouldn't happen... hmm
            pass
        else:
            labels = line.split(None,3)
            label_addr = labels[0].strip()
            label_opcodes = labels[1].strip()
            label_inst = labels[2].rstrip()
            label_remainder = ""
            if len(labels) > 3:
                label_remainder = labels[3].rstrip()
				# graphviz doesn't like "!" or "+".. in node names so strip them
                jmp_target = label_remainder.split()[0].replace("!","").replace("+","")

            new_node.add_label_text(label_addr + " " + label_inst + " " + label_remainder)

            last_line_ret = False
            last_line_jump = False

            if label_inst.startswith("ret"):
                last_line_ret = True
            elif label_inst.startswith("jmp"):
                last_line_jump = True
                new_node.add_connection(jmp_target)
            #TODO: better branch detection needed?
            elif label_inst.startswith("j"):
                new_node.add_connection(jmp_target)

    if new_node and new_node not in nodes:
        nodes += [new_node]
    return nodes

#custom 'dot' file creation function
def create_dot_file(nodes, filename):
    graph_hdr = "digraph{\nnode [fontname=\"Lucida Console\",shape=\"box\"];\ngraph [fontname=\"Lucida Console\",fontsize=10.0,labeljust=l,nojustify=true,splines=polyline];\n"
    f = open(filename,'w')
    f.write(graph_hdr)
    for node in nodes:
        f.write(node.get_dotformat_node())
    f.write("\n\n")
    for node in nodes:
        f.write(node.get_dotformat_connections())
    f.write("\n}")
    f.close()

#launch 'dot' from graphviz and then use the default png viewer via the shell
def render_dot_file(filename):
    pngfilename = filename + ".png"
    dotproc = subprocess.Popen(['dot','-Tpng','-o',pngfilename,filename])
    dotproc.wait()
    os.unlink(filename)
    imageproc = subprocess.Popen([pngfilename],shell=True)
    
#use graphviz package
def do_graph(nodes, filename):
    dot = Digraph(name='windbg_graph', node_attr={'shape': 'box', 'fontname' : 'Lucida Console'}, graph_attr={'splines':'polyline'})

    for anode in nodes:
        dot.node(anode.get_nodeName(),anode.get_dotformat_label())
    for anode in nodes:
        connections = anode.get_connections()
        for connection in connections:
            dot.edge(anode.get_nodeName(),connection)
    #print(dot.source)
    dot.format = 'png'
    dot.render(filename, view=True)    
    os.unlink(filename)

if __name__ == "__main__":
    filename = tempfile.gettempdir() + os.sep + str(uuid.uuid4())
    nodes = build_nodes()
    if not has_graphviz:
        create_dot_file(nodes, filename)
        render_dot_file(filename)
    else:
        do_graph(nodes, filename)
    exit()