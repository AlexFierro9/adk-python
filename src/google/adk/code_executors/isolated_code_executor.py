from __future__ import annotations

from contextlib import redirect_stdout
import io
import re
from typing import Any

from pydantic import Field
from typing_extensions import override

from ..agents.invocation_context import InvocationContext
from .base_code_executor import BaseCodeExecutor
from .code_execution_utils import CodeExecutionInput
from .code_execution_utils import CodeExecutionResult

import sys
import subprocess

#Don't think this is needed anymore but keeping it around just in case.

# def _prepare_globals(code: str, globals_: dict[str, Any]) -> None:
#   """Prepare globals for code execution, injecting __name__ if needed."""
#   if re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]", code):
#     globals_['__name__'] = '__main__'

class IsolatedCodeExecutor(BaseCodeExecutor):
  """A code executor that safely executes code in an isolated environment through 
    the current local context."""

  # Overrides the BaseCodeExecutor attribute: this executor cannot be stateful.
  stateful: bool = Field(default=False, frozen=True, exclude=True)

  # Overrides the BaseCodeExecutor attribute: this executor cannot
  # optimize_data_file.
  optimize_data_file: bool = Field(default=False, frozen=True, exclude=True)

  def __init__(self, **data):
    """Initializes the IsolatedCodeExecutor."""
    if 'stateful' in data and data['stateful']:
      raise ValueError('Cannot set `stateful=True` in IsolatedCodeExecutor.')
    if 'optimize_data_file' in data and data['optimize_data_file']:
      raise ValueError(
          'Cannot set `optimize_data_file=True` in IsolatedCodeExecutor.'
      )
    super().__init__(**data)

  @override
  def execute_code(
      self,
      invocation_context: InvocationContext,
      code_execution_input: CodeExecutionInput,
  ) -> CodeExecutionResult:
    # Executes code by spawning a new python interpreter process.
    code = code_execution_input.code
    process_result = subprocess.run(
    [sys.executable, "-c", code],
    capture_output=True,
    text=True
    )

    # Collect the final result.
    return CodeExecutionResult(
        stdout=process_result.stdout,
        stderr=process_result.stderr,
        output_files=[],
    )
