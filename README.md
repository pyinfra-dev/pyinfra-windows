# pyinfra_windows

[`pyinfra`](https://github.com/pyinfra-dev/pyinfra) plugin to support windows facts/operations/connectors.

> **_NOTE:_** This repo is NOT ready for production.

## Install
```
uv tool install pyinfra --with https://github.com/pyinfra-dev/pyinfra-windows.git
```

## Ad-hoc pyinfra_windows facts/operations.
pyinfra supports [ad-hoc commands](https://docs.pyinfra.com/en/3.x/getting-started.html#ad-hoc-commands-with-pyinfra). Users can execute them to run a fact/opration on a specific host.

To use `pyinfra_windows` facts/operations, you must prefix the fact/operations
with `pyinfra_windows.facts.<module>.<cls>` or `pyinfra_windows.operations.<module>.<cls>`.

```
# pyinfra INVENTORY fact FACT
pyinfra @winrm/192.168.1.245 fact pyinfra_windows.facts.server.ComputerInfo

# pyinfra INVENTORY OPERATIONS
pyinfra @winrm/192.168.1.245 pyinfra_windows.operations.files.put src=test-file dest=test-file
```



