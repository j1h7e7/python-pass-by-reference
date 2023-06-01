import inspect
import ast
import ctypes
import dis
from types import FrameType, CodeType
import textwrap
import re

DECORATOR_NAME_REGEX = re.compile(r"@([^\d\W]\w*)(\s.*)?\n")


def get_name_and_space(
    value, frame: FrameType, fn_name: str, argnum: int = 0
) -> tuple[str, dict]:
    locs = frame.f_locals
    globs = frame.f_globals
    lasti = frame.f_lasti
    codeobj = frame.f_code

    names = [(name, locs) for name, var in locs.items() if var is value]

    if len(names) < 1:
        names.extend((name, globs) for name, var in globs.items() if var is value)
    if len(names) > 1:
        idx = lasti // 2
        varname = None

        instructions = list(dis.get_instructions(codeobj))
        i_call = instructions[idx]

        if i_call.opname == "CALL_FUNCTION":
            l_args = i_call.argval + 1
            i_fn, *vars = instructions[:idx][-l_args:]

            if i_fn.argval == fn_name:
                varname = vars[argnum].argval

        names = [(n, ns) for (n, ns) in names if n == varname]

    assert len(names) >= 1, "Not enough possibilities"
    assert len(names) <= 1, "Too many possibilities"

    return names.pop()


def get_args_and_fixed_func(
    code: ast.Module, fn_name: str
) -> tuple[list[str], CodeType]:
    body = code.body[0]

    # remove this decorator
    body.decorator_list = [x for x in body.decorator_list if x.id != fn_name]
    # change function signature
    argnames = []
    for arg in body.args.args:
        argnames.append(arg.arg)
        arg.arg = "_" + arg.arg
    # add new global
    body.body.insert(0, ast.Global(argnames))
    # add assignment
    for arg in argnames:
        body.body.insert(
            1,
            ast.Assign(
                targets=[ast.Name(id=arg, ctx=ast.Store())],
                value=ast.Name(id=f"_{arg}", ctx=ast.Load()),
            ),
        )
    ast.fix_missing_locations(code)

    return argnames, compile(code, "", "exec")


def pass_by_reference(f):
    current_frame = inspect.currentframe()
    code_context = inspect.getframeinfo(current_frame.f_back).code_context[0]

    thisname = re.match(DECORATOR_NAME_REGEX, code_context).group(1)
    code = ast.parse(textwrap.dedent(inspect.getsource(f)))
    argnames, compiled = get_args_and_fixed_func(code, thisname)

    ns0 = {arg: None for arg in argnames}
    ns1 = {}
    exec(compiled, ns0, ns1)
    f_name, f = ns1.popitem()

    def func(*args, **kwargs):
        output = f(*args, **kwargs)
        frame = inspect.currentframe()

        for i, (val, argname) in enumerate(zip(args, argnames)):
            try:
                name, namespace = get_name_and_space(val, frame.f_back, f_name, i)
                namespace[name] = ns0[argname]
            except AssertionError:
                print("failed!")

        ctypes.pythonapi.PyFrame_LocalsToFast(
            ctypes.py_object(frame.f_back), ctypes.c_int(0)
        )

        return output

    return func
