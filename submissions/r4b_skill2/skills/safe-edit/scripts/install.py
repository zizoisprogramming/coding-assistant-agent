"""Copy safe_edit.py into the task's temp directory (/tmp in the sandbox) so run_command can use it."""
import os
import shutil
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
target = os.path.join(tempfile.gettempdir(), "safe_edit.py")
shutil.copyfile(os.path.join(here, "safe_edit.py"), target)
print("INSTALLED /tmp/safe_edit.py. Edit source files with run_command:\n"
      "python3 /tmp/safe_edit.py path/to/file.py << 'EDIT'\n"
      "<<<<<<< SEARCH\nexact current lines\n=======\nnew lines\n>>>>>>> REPLACE\nEDIT")
