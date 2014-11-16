
# This code is available under MIT License.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import sys
import os
import tempfile
import uuid
import subprocess
import argparse

outputformat = 'png'
stackwalkhtml = False
frames = []
outputdir = None
noopen = False

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
        self.addcolor = False

    def add_color(self):
        self.addcolor = True

    def has_color(self):
        return self.addcolor

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
        dotstr += "["
        if self.addcolor:
            dotstr += "style=filled fillcolor=gray "
        dotstr += "label=\""
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
    global frames
    nodes = []
    last_line_jump = False
    last_line_ret = False
    new_node = None
    last_node = None
    ipaddr = None
    firstline = True

    for line in sys.stdin:
        line = line.rstrip()

        #break out at the end of a frame
        if line.startswith("_ _ _ _") and not firstline:
            break;
        elif line.startswith("_ _ _ _"):
            continue;
        elif line.endswith(":"):
            #get the new node name
            # graphviz doesn't like "!" or "+".. in node names so strip them
            #new_name = line.split(":")[0].split()[0].replace("!","").replace("+","")
            new_name = line.rsplit(":",1)[0].split()[0].replace("!","").replace("+","")

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
        elif line.startswith("$ip") or line.startswith("$scopeip"):
            ipaddr = line.split("=")[1]
        elif not new_node:
            #.. skip lines that fall outside of a node
            if firstline:
                tokens = line.split()
                #if tokens[len(tokens) - 1] not in frames:
                frames += [ tokens[len(tokens) - 1] ]
        else:
            #private symbols have a space followed by the line number
            if line.startswith(" "):
                labels = line.split(None,4)
                label_addr = labels[1].strip()
                label_opcodes = labels[2].strip()
                label_inst = labels[3].rstrip()
                label_remainder = ""
                if len(labels) > 4:
                    label_remainder = labels[4].rstrip()
                    # graphviz doesn't like "!" or "+".. in node names so strip them
                    jmp_target = label_remainder.split()[0].replace("!","").replace("+","")
            #public symbols don't..
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
            if ipaddr and label_addr.replace("`","").startswith(ipaddr):
                new_node.add_color()

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

        firstline = False

    if new_node and new_node not in nodes:
        nodes += [new_node]
    return nodes

#custom 'dot' file creation function
def create_dot_file(nodes, filename):
    graph_hdr = "digraph{\nnode [fontname=\"Lucida Console\",shape=\"box\"];\ngraph [fontname=\"Lucida Console\"," \
                "fontsize=10.0,labeljust=l,nojustify=true,splines=polyline];\n"
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
    graph_file_path = filename + "." + outputformat
    dotproc = subprocess.Popen(['dot','-T' + outputformat,'-o',graph_file_path,filename])
    dotproc.wait()
    os.unlink(filename)
    return graph_file_path
    
#use graphviz package
def render_graph(nodes, filename):
    dot = Digraph(name='windbg_graph', node_attr={'shape': 'box', 'fontname' : 'Lucida Console'}, graph_attr={'splines':'polyline'})

    for anode in nodes:
        if(anode.has_color()):
            dot.node(anode.get_nodeName(),anode.get_dotformat_label(), _attributes={'style':'filled', 'fillcolor':'gray'})
        else:
            dot.node(anode.get_nodeName(),anode.get_dotformat_label())
        connections = anode.get_connections()
        for connection in connections:
            dot.edge(anode.get_nodeName(),connection)

    #print(dot.source)
    dot.format = outputformat
    graph_file = dot.render(filename, view=False)
    os.unlink(filename)
    return  graph_file

def parseArgs():
    global outputformat
    global stackwalkhtml
    global outputdir
    global noopen

    parser = argparse.ArgumentParser(description="Reads the output of the 'uf' Windbg command from stdin and generates"
                                                 "a graphviz call garph for the funciton")
    parser.add_argument("-of", "--outputformat", help="output format [png, svg, pdf, gif]. Default is png.")
    parser.add_argument("-od", "--outputdir", help="output directory. Default is <TEMP>.")
    parser.add_argument("-no", "--noopen", action="store_true", help="do not open any graph / html once generated")
    parser.add_argument("-sh", "--stackwalkhtml", action="store_true", help="generate a graph for each stack frame "
                                                                            "(input must be a 'uf' for each frame) and"
                                                                            "link them together with a simple html page."
                                                                            " Note:Forces output format to be SVG.")
    args = parser.parse_args()

    if args.outputformat:
        if args.outputformat in ['png','svg', 'gif', 'pdf']:
            outputformat = args.outputformat
        else:
            parser.print_usage()
            quit()

    if args.stackwalkhtml:
        stackwalkhtml = True
        outputformat = 'svg'

    if args.outputdir and os.path.isdir(args.outputdir):
        outputdir = args.outputdir
        if not outputdir.endswith(os.sep):
            outputdir = outputdir + os.sep
    else:
        outputdir = tempfile.gettempdir() + os.sep

    if args.noopen:
        noopen = True

def build_graph_image():
    global outputdir
    nodes = build_nodes()
    filename = outputdir + str(uuid.uuid4())
    graph_image = None
    if len(nodes) > 0:
        if not has_graphviz:
            create_dot_file(nodes, filename)
            graph_image = render_dot_file(filename)
        else:
            graph_image = render_graph(nodes, filename)
    return graph_image


def build_html(graph_images):
    index = 0
    html_page = outputdir + "graph.html"

    #print str(len(graph_images))
    #print str(len(frames))
    #print frames

    htmlfd = open(html_page,"w+")
    htmlfd.write("<HTML>")

    #outer table
    htmlfd.write("<TABLE HEIGHT=100% BORDER=1><TR HEIGHT=100%><TD VALIGN=TOP>")
    #inner table
    htmlfd.write("<TABLE>")
    htmlfd.write("<TR><TD style=\"white-space:nowrap;\">STACK FRAMES:</TD></TR>")
    for graph_image in graph_images:
        htmlfd.write("<TR><TD style=\"white-space:nowrap;\">")

        htmlfd.write("<SPAN style=\"border: 1px solid black\" ONCLICK=\"document.getElementById('GRAPHIMG').src='" +
                     os.path.basename(graph_image) + "'\">")
        htmlfd.write(str(index) + "=" + frames[index])
        htmlfd.write("</SPAN></TD></TR>")

        #htmlfd.write("<A HREF=" + os.path.basename(graph_image) + " TARGET=\"GRAPHFRAME\">")
        #htmlfd.write(str(index) + "=" + frames[index])
        #htmlfd.write("</A></TD></TR>")
        index += 1

    htmlfd.write("</TABLE></TD>")
    #iframe
    htmlfd.write("<TD WIDTH=100% HEIGHT=100%>")
    htmlfd.write("<IMG ID=\"GRAPHIMG\" WIDTH=100% SRC=\"" + os.path.basename(graph_images[0]) + "\">")
    #htmlfd.write("<IFRAME NAME=GRAPHFRAME WIDTH=100% HEIGHT=100% SRC=\"" + os.path.basename(graph_images[0]) + "\"></IFRAME>")
    htmlfd.write("</TD></TR></TABLE>")
    htmlfd.write("</HTML>")
    htmlfd.close()

    return html_page

if __name__ == "__main__":

    parseArgs()
    graph_images = []
    graph_image = build_graph_image()
    while graph_image:
        graph_images += [graph_image]
        graph_image = build_graph_image()

    if stackwalkhtml:
        html_page = build_html(graph_images)
        if not noopen:
            htmlproc = subprocess.Popen([html_page],shell=True)
    elif not noopen:
        for imagefile in graph_images:
            imageproc = subprocess.Popen([imagefile],shell=True)

    exit()
