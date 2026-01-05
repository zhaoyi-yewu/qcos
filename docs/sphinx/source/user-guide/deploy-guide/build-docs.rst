文档构建
==============

本章节介绍QCOS项目文档的编译方法，包含Sphinx文档和OpenAPI文档的统一构建流程。

.. contents:: 目录
   :local:
   :depth: 3

编译Sphinx文档和OpenAPI文档
---------------------------------

推荐在qcos-sandbox容器环境中完成文档编译，确保依赖环境一致性，具体步骤如下：

.. code-block:: shell

   # 进入编译脚本目录
   cd build-scripts
   # 执行文档编译脚本，自动生成Sphinx文档和OpenAPI文档
   ./build-docs.sh

构建完成后，说明指导文档会生成到docs/sphinx/dist目录下，而API文档会生成到docs/openapi-docs/dist/目录下:

html文档：docs/sphinx/dist/html/index.html，可通过浏览器打开HTML格式文档查看。

pdf文档：docs/sphix/dist/pdf/qcos-full-doc.pdf，可通过pdf阅读器查看文档。

openapi文档：docs/openapi-docs/dist/qcos-api-docs.html，可通过浏览器打开HTML格式文档查看。
