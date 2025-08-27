# plugins/sample_plugin.py
def register(names: dict):
    """
    Sample plugin that registers two safe helpers:
      - cube(x) : x**3
      - greet() : returns a greeting string (non-numeric; will not be allowed as variable)
    """
    names["cube"] = lambda x: x ** 3
    # avoid non-numeric values for expressions, but we demonstrate registering a constant string
    names["author"] = "plugin-sample"
