项目管理命令
----------------------

项目管理命令包含项目的创建、查询、更新和删除等操作。

项目创建
***************

创建项目的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 创建项目
   usage: qcos-cli create-project [-h] project_name

   Create project.

   positional arguments:
     project_name  Project name

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 创建一个基础项目
   qcos-cli create-project my-project

   # 创建一个带描述的项目
   qcos-cli create-project quantum-proj --description "Quantum Computing Project"

项目列表查询
***************

查询项目列表的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询项目列表
   usage: qcos-cli list-projects [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN] [--quote {all,minimal,none,nonnumeric}] [--noindent]
                                 [--max-width <integer>] [--fit-width] [--print-empty] [--sort-column SORT_COLUMN] [--sort-ascending | --sort-descending]
                                 [--name NAME]

   Get projects with optional filtering. Examples: list-projects # List all projects list-projects --name default # Filter by project name

   options:
     -h, --help            show this help message and exit
     --name NAME   Filter projects by name

   output formatters:
     output formatter options

     -f {csv,json,table,value,yaml}, --format {csv,json,table,value,yaml}
                           the output format, defaults to table
     -c COLUMN, --column COLUMN
                           specify the column(s) to include, can be repeated to show multiple columns
     --sort-column SORT_COLUMN
                           specify the column(s) to sort the data (columns specified first have a priority, non-existing columns are ignored), can be repeated
     --sort-ascending      sort the column(s) in ascending order
     --sort-descending     sort the column(s) in descending order

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询所有项目列表
   qcos-cli list-projects

项目详情查询
***************

查询项目详情的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询项目详情
   usage: qcos-cli get-project [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent] [--prefix PREFIX] [--max-width <integer>]
                               [--fit-width] [--print-empty]
                               project_id

   Get project by ID.

   positional arguments:
     project_id    Project ID (UUID)

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询项目 my-project 的详情
   qcos-cli get-project 00000000-0000-4000-8000-000000000001

项目信息更新
***************

更新项目的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 更新项目
   usage: qcos-cli update-project [-h] [--name NAME] [--description DESCRIPTION] project_id

   Update project by ID.

   positional arguments:
     project_id    Project ID (UUID)

   options:
     -h, --help            show this help message and exit
     --name NAME   New project name
     --description DESCRIPTION New project description

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 使用UUID更新项目
   qcos-cli update-project 00000000-0000-4000-8000-000000000001 --description "New description"

项目删除
***************

删除项目的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 删除项目
   usage: qcos-cli delete-project [-h] project_id

   Delete project by ID.

   positional arguments:
     project_id  Project ID (UUID)

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 删除项目 my-project
   qcos-cli delete-project 00000000-0000-4000-8000-000000000001


