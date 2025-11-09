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
import os

from unittest.mock import MagicMock

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.code_executors.code_execution_utils import CodeExecutionInput
from google.adk.code_executors.code_execution_utils import CodeExecutionResult
from google.adk.code_executors.unsafe_local_code_executor import UnsafeLocalCodeExecutor
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.session import Session
import pytest


@pytest.fixture
def mock_invocation_context() -> InvocationContext:
  """Provides a mock InvocationContext."""
  mock_agent = MagicMock(spec=BaseAgent)
  mock_session = MagicMock(spec=Session)
  mock_session_service = MagicMock(spec=BaseSessionService)
  return InvocationContext(
      invocation_id="test_invocation",
      agent=mock_agent,
      session=mock_session,
      session_service=mock_session_service,
  )


class TestUnsafeLocalCodeExecutor:

  def test_init_default(self):
    executor = UnsafeLocalCodeExecutor()
    assert not executor.stateful
    assert not executor.optimize_data_file

  def test_init_stateful_raises_error(self):
    with pytest.raises(
        ValueError,
        match="Cannot set `stateful=True` in UnsafeLocalCodeExecutor.",
    ):
      UnsafeLocalCodeExecutor(stateful=True)

  def test_init_optimize_data_file_raises_error(self):
    with pytest.raises(
        ValueError,
        match=(
            "Cannot set `optimize_data_file=True` in UnsafeLocalCodeExecutor."
        ),
    ):
      UnsafeLocalCodeExecutor(optimize_data_file=True)

  def test_execute_code_simple_print(
      self, mock_invocation_context: InvocationContext
  ):
    executor = UnsafeLocalCodeExecutor()
    code_input = CodeExecutionInput(code='print("hello world")')
    result = executor.execute_code(mock_invocation_context, code_input)

    assert isinstance(result, CodeExecutionResult)
    assert result.stdout == "hello world\n"
    assert result.stderr == ""
    assert result.output_files == []

  def test_execute_code_with_error(
      self, mock_invocation_context: InvocationContext
  ):
    executor = UnsafeLocalCodeExecutor()
    code_input = CodeExecutionInput(code='raise ValueError("Test error")')
    result = executor.execute_code(mock_invocation_context, code_input)

    assert isinstance(result, CodeExecutionResult)
    assert result.stdout == ""
    assert "Test error" in result.stderr
    assert result.output_files == []

  def test_execute_code_variable_assignment(
      self, mock_invocation_context: InvocationContext
  ):
    executor = UnsafeLocalCodeExecutor()
    code_input = CodeExecutionInput(code="x = 10\nprint(x * 2)")
    result = executor.execute_code(mock_invocation_context, code_input)

    assert result.stdout == "20\n"
    assert result.stderr == ""

  def test_execute_code_empty(self, mock_invocation_context: InvocationContext):
    executor = UnsafeLocalCodeExecutor()
    code_input = CodeExecutionInput(code="")
    result = executor.execute_code(mock_invocation_context, code_input)
    assert result.stdout == ""
    assert result.stderr == ""

  def test_execute_code_isolated_simple_print(
      self, mock_invocation_context: InvocationContext
  ):
    """Test execution with use_isolated_process=True."""
    executor = UnsafeLocalCodeExecutor(use_isolated_process=True)
    code_input = CodeExecutionInput(code='print("hello isolated world")')
    result = executor.execute_code(mock_invocation_context, code_input)

    assert isinstance(result, CodeExecutionResult)
    assert result.stdout == "hello isolated world\n"
    assert result.stderr == ""
    assert result.output_files == []

  def test_execute_code_isolated_with_error(
      self, mock_invocation_context: InvocationContext
  ):
    """Test error handling with use_isolated_process=True."""
    executor = UnsafeLocalCodeExecutor(use_isolated_process=True)
    code_input = CodeExecutionInput(code='raise ValueError("Isolated error")')
    result = executor.execute_code(mock_invocation_context, code_input)

    assert isinstance(result, CodeExecutionResult)
    assert result.stdout == ""
    assert "Isolated error" in result.stderr
    assert result.output_files == []

  def test_execute_code_isolated_with_import(
      self, mock_invocation_context: InvocationContext
  ):
    """Test imports with use_isolated_process=True."""
    executor = UnsafeLocalCodeExecutor(use_isolated_process=True)
    code = "import os; print(os.linesep)"
    code_input = CodeExecutionInput(code=code)
    result = executor.execute_code(mock_invocation_context, code_input)

    assert result.stdout.strip() == os.linesep.strip()
    assert result.stderr == ""

  def test_execute_code_if_main(
      self, mock_invocation_context: InvocationContext
  ):
    """Test code with `if __name__ == '__main__'`."""
    executor = UnsafeLocalCodeExecutor()
    code = 'if __name__ == "__main__":\n    print("executed as main")'
    code_input = CodeExecutionInput(code=code)
    result = executor.execute_code(mock_invocation_context, code_input)

    assert result.stdout == "executed as main\n"
    assert result.stderr == ""

  def test_execute_code_isolated_memory_isolation_variable(
      self, mock_invocation_context: InvocationContext
  ):
    """Test that variables do not persist between isolated executions."""
    executor = UnsafeLocalCodeExecutor(use_isolated_process=True)

    # First execution defines a variable.
    code_input1 = CodeExecutionInput(code="x = 100")
    executor.execute_code(mock_invocation_context, code_input1)

    # Second execution tries to access the variable.
    code_input2 = CodeExecutionInput(code="print(x)")
    result = executor.execute_code(mock_invocation_context, code_input2)

    assert "name 'x' is not defined" in result.stderr

  def test_execute_code_isolated_memory_isolation_function(
      self, mock_invocation_context: InvocationContext
  ):
    """Test that functions do not persist between isolated executions."""
    executor = UnsafeLocalCodeExecutor(use_isolated_process=True)

    code_input1 = CodeExecutionInput(code="def my_func(): return 'isolated'")
    executor.execute_code(mock_invocation_context, code_input1)

    code_input2 = CodeExecutionInput(code="print(my_func())")
    result = executor.execute_code(mock_invocation_context, code_input2)

    assert "name 'my_func' is not defined" in result.stderr
