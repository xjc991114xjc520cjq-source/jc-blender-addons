"""""" # start delvewheel patch
def _delvewheel_patch_1_12_1():
    import os
    if os.path.isdir(libs_dir := os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'cadquery_ocp_novtk.libs'))):
        os.add_dll_directory(libs_dir)


_delvewheel_patch_1_12_1()
del _delvewheel_patch_1_12_1
# end delvewheel patch

from OCP.OCP import *

from OCP.OCP import __version__
