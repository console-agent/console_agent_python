"""
Code Execution tool wrapper.
Uses Gemini's built-in code execution capability.

In Agno/Gemini, code execution is enabled via request_params:
    Gemini(
        id="...",
        request_params={"tools": [{"code_execution": {}}]}
    )

This allows the model to write and execute Python code server-side
to perform calculations, data processing, and analysis.
"""

CODE_EXECUTION_TOOL = "code_execution"
