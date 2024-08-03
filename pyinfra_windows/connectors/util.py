
import shlex

def make_win_command(command):
    """
    Builds a windows command with various kwargs.
    """

    # Quote the command as a string
    command = shlex.quote(str(command))
    command = "{0}".format(command)

    return command
