# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from contextlib import redirect_stdout
import io
import subprocess
import sys
import re
from typing import Any

from pydantic import Field
from typing_extensions import override

from ..agents.invocation_context import InvocationContext
from .base_code_executor import BaseCodeExecutor
from .code_execution_utils import CodeExecutionInput
from .code_execution_utils import CodeExecutionResult
from .isolated_code_executor import IsolatedCodeExecutor


def _prepare_globals(code: str, globals_: dict[str, Any]) -> None:
  """Prepare globals for code execution, injecting __name__ if needed."""
  if re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]", code):
    globals_['__name__'] = '__main__'


class UnsafeLocalCodeExecutor(BaseCodeExecutor):
  """A code executor that unsafely execute code in the current local context.

  This executor can be configured to run code in an isolated process.
  """

  # Overrides the BaseCodeExecutor attribute: this executor cannot be stateful.
  stateful: bool = Field(default=False, frozen=True, exclude=True)

  # Overrides the BaseCodeExecutor attribute: this executor cannot
  # optimize_data_file.
  optimize_data_file: bool = Field(default=False, frozen=True, exclude=True)

  use_isolated_process: bool = False

  def __init__(self, use_isolated_process: bool = False, **data):
    """Initializes the UnsafeLocalCodeExecutor."""
    if 'stateful' in data and data['stateful']:
      raise ValueError('Cannot set `stateful=True` in UnsafeLocalCodeExecutor.')
    if 'optimize_data_file' in data and data['optimize_data_file']:
      raise ValueError(
          'Cannot set `optimize_data_file=True` in UnsafeLocalCodeExecutor.'
      )
    super().__init__(use_isolated_process=use_isolated_process, **data)
    self.use_isolated_process = use_isolated_process
    if self.use_isolated_process:
      self._isolated_executor = IsolatedCodeExecutor()

  @override
  def execute_code(
      self,
      invocation_context: InvocationContext,
      code_execution_input: CodeExecutionInput,
  ) -> CodeExecutionResult:
    if self.use_isolated_process:
      return self._isolated_executor.execute_code(
          invocation_context, code_execution_input
      )

    # Execute the code.
    output = ''
    error = ''
    try:
      globals_ = {}
      _prepare_globals(code_execution_input.code, globals_)
      stdout = io.StringIO()
      with redirect_stdout(stdout):
        exec(code_execution_input.code, globals_)
      output = stdout.getvalue()
    except Exception as e:
      error = str(e)

    # Collect the final result.
    return CodeExecutionResult(
        stdout=output,
        stderr=error,
        output_files=[],
    )
