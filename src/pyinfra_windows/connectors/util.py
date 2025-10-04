# import shlex


def make_win_command(command):
    """
    Builds a windows command with various kwargs.
    """

    # TODO(ricky) I'm not sure why the following quote/format
    # was here
    # but it causes powershell commands
    # to echo as literal strings instead
    # of running as commands.
    # Just leaving incase, I run
    # odd behavior later.

    # Quote the command as a string
    # command = mslex.quote(str(command))
    # command = "{0}".format(command)
    return str(command)
