When we build under Meson, there will be two "files" with the same "tumtum" name,
one is the Python source folder, one is entry script generated from "tumtum.in".

To avoid conflict, we put the entry script to this subfolder when being built.
