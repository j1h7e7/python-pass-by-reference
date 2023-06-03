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
    code: ast.Module, fn_names: list[str]
) -> tuple[list[str], CodeType]:
    body = code.body[0]

    # remove this decorator
    body.decorator_list = [x for x in body.decorator_list if x.id not in fn_names]
    # change function signature
    argnames = []
    for arg in body.args.args:
        argnames.append(arg.arg)
        arg.arg = "_" + arg.arg
    # add new global
    if argnames:
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

    return argnames, compile(code, "<pass_by_reference>", "exec")


def pass_by_reference(f):
    current_frame = inspect.currentframe()
    prev_frame = current_frame.f_back
    prev_frame_variables = prev_frame.f_globals | prev_frame.f_locals

    thisnames = [k for k, v in prev_frame_variables.items() if v is pass_by_reference]
    code = ast.parse(textwrap.dedent(inspect.getsource(f)))
    argnames, compiled = get_args_and_fixed_func(code, thisnames)

    ns_globals = prev_frame.f_globals | {arg: None for arg in argnames}
    ns_locals = prev_frame.f_locals.copy()
    exec(compiled, ns_globals, ns_locals)
    f_name, f = ns_locals.popitem()  # probably not good

    def func(*args, **kwargs):
        output = f(*args, **kwargs)
        frame = inspect.currentframe()

        for i, (val, argname) in enumerate(zip(args, argnames)):
            try:
                name, namespace = get_name_and_space(val, frame.f_back, f_name, i)
                namespace[name] = ns_globals[argname]
            except AssertionError:
                print("failed!")

        ctypes.pythonapi.PyFrame_LocalsToFast(
            ctypes.py_object(frame.f_back), ctypes.c_int(0)
        )

        return output

    return func
