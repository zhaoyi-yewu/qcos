MCP服务接口规范
======================

本章节提供基于 MCP SDK 反射 API（``mcp.list_tools()``）自动生成的 MCP 工具
参考文档。

文档为自包含 HTML，枚举 ``POST/SSE /v1/ai/mcp`` 端点上暴露的所有 MCP 工具，
展示每个工具的 ``name`` / ``description`` / ``input_schema`` （由 pydantic
根据函数签名和 docstring 自动生成的 JSON Schema）。

.. note::

    以下通过 iframe 嵌入 MCP 工具参考页面。如果无法正常显示，可点击下方链接
    在新窗口中打开完整 MCP API 文档。

.. raw:: html

    <p>
      <a href="_static/qcos-mcp-docs.html"
         target="_blank">
        在新窗口打开完整 MCP API 文档
      </a>
    </p>

    <iframe src="_static/qcos-mcp-docs.html"
            width="100%" height="900px"
            frameborder="0"
            style="border: none; min-height: 80vh;">
    </iframe>
