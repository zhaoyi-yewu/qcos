资源规格命令
----------------------

资源规格（Flavor）命令用于创建和管理预设调度策略，支持通过命令行创建、查询、更新和删除Flavor。

资源规格创建
***************

创建资源规格的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 创建资源规格
   usage: qcos-cli create-flavor [-h] [--project-id PROJECT_ID] [--description DESCRIPTION]
                                  [--private] [--min-qubits MIN_QUBITS] [--max-qubits MAX_QUBITS]
                                  [--gate-fidelity-1q-min GATE_FIDELITY_1Q_MIN]
                                  [--gate-fidelity-2q-min GATE_FIDELITY_2Q_MIN]
                                  [--property [PROPERTY ...]]
                                  --device-groups DEVICE_GROUPS [DEVICE_GROUPS ...]
                                  name

   Create flavor (preset scheduling policy).

   positional arguments:
     name                  Flavor name

   options:
     -h, --help            show this help message and exit
     --project-id PROJECT_ID
                           Project ID (UUID, optional)
     --description DESCRIPTION
                           Flavor description
     --private             Create as private flavor
     --min-qubits MIN_QUBITS
                           Minimum qubits
     --max-qubits MAX_QUBITS
                           Maximum qubits
     --gate-fidelity-1q-min GATE_FIDELITY_1Q_MIN
                           Min 1q gate fidelity
     --gate-fidelity-2q-min GATE_FIDELITY_2Q_MIN
                           Min 2q gate fidelity
     --property [PROPERTY ...]
                           Property in namespace:key=value format
     --device-groups DEVICE_GROUPS [DEVICE_GROUPS ...]
                           Device group names or UUIDs (at least one required)

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 创建资源规格
   qcos-cli create-flavor my-flavor --description "quantum computers qubits: 1-32" --min-qubits 1 --max-qubits 32 --device-groups <device-group-uuid>
   qcos-cli create-flavor hf-flavor --description "High-gate-fidelity quantum computers" --min-qubits 1 --gate-fidelity-1q-min 0.99 --gate-fidelity-2q-min 0.99 --device-groups <device-group-uuid>

   # 创建带多个设备分组的资源规格
   qcos-cli create-flavor multi-flavor --min-qubits 1 --device-groups <dg-uuid-1> <dg-uuid-2>

资源规格更新
***************

更新资源规格的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 更新资源规格
   usage: qcos-cli update-flavor [-h] [--name NAME] [--description DESCRIPTION] [--public | --private]
                                  [--project-id PROJECT_ID] [--min-qubits MIN_QUBITS] [--max-qubits MAX_QUBITS]
                                  [--gate-fidelity-1q-min GATE_FIDELITY_1Q_MIN]
                                  [--gate-fidelity-2q-min GATE_FIDELITY_2Q_MIN]
                                  [--property [PROPERTY ...]]
                                  --device-groups DEVICE_GROUPS [DEVICE_GROUPS ...]
                                  flavor_id

   Update flavor (preset scheduling policy).

   positional arguments:
     flavor_id             Flavor ID (UUID) or flavor name

   options:
     -h, --help            show this help message and exit
     --device-groups DEVICE_GROUPS [DEVICE_GROUPS ...]
                            Device group names or UUIDs (required. Replaces
                            existing device group mappings)

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 更新资源规格
   qcos-cli update-flavor my-flavor --description "updated descriptions" --max-qubits 64 --device-groups <device-group-uuid>

资源规格详情查询
*****************

查询资源规格详情的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询资源规格详情
   usage: qcos-cli get-flavor [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent] [--prefix PREFIX]
                              [--max-width <integer>] [--fit-width] [--print-empty]
                              flavor_id

   Get flavor by ID or name.

   positional arguments:
     flavor_id             Flavor ID (UUID) or flavor name

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询资源规格详情
   qcos-cli get-flavor my-flavor

资源规格列表查询
*****************

查询资源规格列表的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询资源规格列表
   usage: qcos-cli list-flavors [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN] [--quote {all,minimal,none,nonnumeric}]
                                 [--noindent] [--max-width <integer>] [--fit-width] [--print-empty]
                                 [--sort-column SORT_COLUMN] [--sort-ascending | --sort-descending]
                                 [--flavor-ids [FLAVOR_IDS ...]]
                                 [--flavor-name FLAVOR_NAME [FLAVOR_NAME ...]]

   Get flavor list.

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询资源规格列表
   qcos-cli list-flavors

   # 按ID列表过滤查询
   qcos-cli list-flavors --flavor-ids <flavor-uuid-1> <flavor-uuid-2>

   # 按名称过滤查询
   qcos-cli list-flavors --flavor-name g1.all

   # 按多个名称过滤查询
   qcos-cli list-flavors --flavor-name g1.all g2.all

资源规格批量删除
****************

批量删除资源规格的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 删除资源规格（批量）
   usage: qcos-cli delete-flavors [-h] [-y] flavor_ids

   Delete flavors by IDs or names (batch).

   positional arguments:
     flavor_ids            Flavor IDs or names to delete. Use comma-separated
                           values for multiple, or 'all' to delete all flavors

   options:
     -h, --help            show this help message and exit
     -y, --yes             Answer yes for all questions

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 删除单个资源规格（可使用UUID或名称）
   qcos-cli delete-flavors my-flavor -y

   # 批量删除多个资源规格
   qcos-cli delete-flavors "flavor1,flavor2,<uuid3>" -y

   # 删除全部资源规格
   qcos-cli delete-flavors all -y
