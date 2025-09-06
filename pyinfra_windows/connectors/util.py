import mslex

def make_win_command(command):
    """
    Builds a windows command with various kwargs.
    """
    # TODO I'm unsure why powershell is needed as a prefix here

    # Quote the command as a string
    command = mslex.quote(str(command))

    if "winget" in str(command):
        command = "powershell {0}".format(command)
    command = "powershell {0}".format(command)

    return command
