import os
import sys

pkg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".packages"))
if os.path.exists(pkg_path) and pkg_path not in sys.path:
    sys.path.insert(0, pkg_path)

root_path = os.path.abspath(os.path.dirname(__file__))
if root_path not in sys.path:
    sys.path.insert(0, root_path)
