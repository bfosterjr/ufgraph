# ufgraph.py #
----------

ufgraph.py is a simple script which parses the output of the `uf` (un-assemble function) command in windbg and uses graphviz to generate a control flow graph as a PNG (and displays it)

*Please note, that some additional options (eg: `/c`) to the `uf` command are not supported and will likely break the output parsing or graph rendering.*

## Requirements ##
----------

 * Python 2.7
 * Graphviz
   * [http://www.graphviz.org/Download.php ](http://www.graphviz.org/Download.php)
   * make sure the binaries are in your %PATH%
 * graphviz python package (optional, but more stable)
   * [https://pypi.python.org/pypi/graphviz](https://pypi.python.org/pypi/graphviz)
   * `pip install graphviz`


## Usage ##
----------

From within windbg, simply run the script using the `.shell` command as follows:

`.shell -ci "uf ntdll!rtlinsertentryhashtable" c:\python27\python.exe c:\temp\ufgraph.py`


![](https://raw.githubusercontent.com/bfosterjr/ufgraph/master/example.png)

