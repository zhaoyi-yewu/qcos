项目管理接口
================

项目管理接口用于项目管理等。

.. list-table:: 项目管理接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **创建项目**
     - **create_project**

       URI: /v1/project/create_project
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "create_project",
               "params": {
                 "body": {
                   "project_name": "string",
                   "description": "string (optional)"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "id": "uuid",
                 "name": "string",
                 "description": "string",
                 "created_at": "2026-04-08T16:39:15",
                 "updated_at": "2026-04-08T16:39:15"
               },
               "error": null,
               "id": 1
             }

   * - **获取项目详情**
     - **get_project**

       URI: /v1/project/get_project
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_project",
               "params": {
                 "body": {
                   "project_id": "uuid"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "id": "uuid",
                 "name": "string",
                 "description": "string",
                 "created_at": "2026-04-08T16:39:15",
                 "updated_at": "2026-04-08T16:39:15"
               },
               "error": null,
               "id": 1
             }

   * - **获取项目列表**
     - **get_projects**

       URI: /v1/project/get_projects
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_projects",
               "params": {
                 "body": {
                   "filters": {}
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": [
                 {
                   "id": "uuid",
                   "name": "project1",
                   "description": "Description of project1",
                   "created_at": "2026-04-08T16:39:15",
                   "updated_at": "2026-04-08T16:39:15"
                 },
                 {
                   "id": "uuid",
                   "name": "project2",
                   "description": "Description of project2",
                   "created_at": "2026-04-08T16:39:15",
                   "updated_at": "2026-04-08T16:39:15"
                 }
               ],
               "error": null,
               "id": 1
             }

   * - **更新项目信息**
     - **update_project**

       URI: /v1/project/update_project
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "update_project",
               "params": {
                 "body": {
                   "project_id": "uuid",
                   "project_name": "string (optional)",
                   "description": "string (optional)"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "id": "uuid",
                 "name": "string",
                 "description": "string",
                 "created_at": "2026-04-08T16:39:15",
                 "updated_at": "2026-04-08T16:39:15"
               },
               "error": null,
               "id": 1
             }

   * - **删除项目**
     - **delete_project**

       URI: /v1/project/delete_project
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "delete_project",
               "params": {
                 "body": {
                   "project_id": "uuid"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "id": "uuid",
                 "name": "string",
                 "deleted_at": "2026-04-08T16:39:15"
               },
               "error": null,
               "id": 1
             }

项目管理参数详解
~~~~~~~~~~~~~~~~

项目信息字段说明
^^^^^^^^^^^^^^^^

项目对象的关键字段：

- **id** (uuid) - 项目全局唯一标识
- **name** (string) - 项目名称，用于识别
- **description** (string) - 项目描述信息，可为空
- **created_at** (datetime) - 项目创建时间
- **updated_at** (datetime) - 项目最后修改时间

删除状态字段说明
^^^^^^^^^^^^^^^^

删除项目返回的关键字段：

- **id** (uuid) - 被删除项目的唯一标识
- **name** (string) - 被删除项目的名称
- **deleted_at** (datetime) - 删除操作的时间戳
