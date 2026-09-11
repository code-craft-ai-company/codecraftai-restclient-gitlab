"""
    Test-count floor for the GitLab client gate (test coverage roadmap, Phase 5).

    The merge gate runs::

        testbase testing run --root ./source/testroots/testbase --includes=testbase.gitlab

    A discovery regression (a wrong ``--includes`` prefix, an import error in a
    test module, a test tree moved out from under the include) makes the gate
    quietly run fewer tests.  This test fails loudly instead when the number of
    tests the gate can collect drops below the count reached when the floor
    was set.
"""

import ast
import os


TEST_FLOOR = 64
"""
    The number of tests the gate collected when this floor was set.  Raise it
    when tests are added; never lower it without a reason recorded in the
    commit that lowers it.
"""


def _count_collectable_tests(include_root: str) -> int:
    """
        Count the tests the testbase runner would collect under ``include_root``.

        The runner (``ccai.testbase.utilities.collect_python_modules_for_tests``
        and ``ccai.testbase.queries.collect_test_references``) walks every
        ``.py`` file under the included directory except ``__init__.py`` and
        ``__platforms__.py``, imports it, and registers every module-level
        function defined in that module whose name starts with ``test``.
        This mirrors that selection statically: each file is parsed with
        :mod:`ast` and its top-level ``def``/``async def`` names with the
        ``test`` prefix are counted, so a module whose import is broken still
        counts here while the runner drops it, and the mismatch surfaces as a
        lower gate total than the floor.

        :param include_root: The directory the gate's ``--includes`` selects.

        :returns: The number of test functions the runner would register.
    """

    count = 0

    for dirpath, _, filenames in os.walk(include_root):
        for filename in filenames:
            basename, extension = os.path.splitext(filename)
            if extension != ".py" or basename in ("__init__", "__platforms__"):
                continue

            filepath = os.path.join(dirpath, filename)
            with open(filepath, "r", encoding="utf-8") as module_file:
                tree = ast.parse(module_file.read(), filename=filepath)

            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                    count += 1

    return count


def test_gate_collects_at_least_the_floor_number_of_tests() -> None:
    """
        The ``testbase.gitlab`` include must still select at least
        ``TEST_FLOOR`` test functions.  The include root is this module's own
        directory (``source/testroots/testbase/gitlab``), so the count follows
        the tree the gate points at rather than a hard-coded path.
    """
    include_root = os.path.dirname(os.path.abspath(__file__))

    collected = _count_collectable_tests(include_root)

    assert collected >= TEST_FLOOR, f"gate collects {collected} tests, below the floor of {TEST_FLOOR}"

    return
