from langchain_core.tools import tool

@tool
def run_python(code: str) -> dict:
    """
        Tool to run any python code by building a sandbox to execute code. This tool can also be used to plot graphs and maps.
    """
    import io, contextlib, traceback
    ns, out, err = {}, io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            exec(code, {}, ns)
        return {"ok": True, "result": ns.get("result"), "stdout": out.getvalue(), "stderr": err.getvalue()}
    except Exception:
        return {"ok": False, "error": traceback.format_exc(), "stdout": out.getvalue(), "stderr": err.getvalue()}
