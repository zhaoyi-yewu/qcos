驱动管理和厂商驱动
==================

驱动管理器会在软件初始化时，搜索源代码的qcos/drivers目录，找到所有继承自DriverBase的厂商驱动类，并进行初始化。

驱动管理器初始化
-------------------------

.. code-block:: python

   # init plugin and drivers
   driver_manager = DriverManager()
   driver_manager.load_drivers()  # 加载驱动
   driver_manager.init_drivers()  # 初始化驱动

驱动类关系
--------------------

操作系统内置多个驱动，比如：空载测试驱动（DriverDummy）、中科酷原-汉原1驱动（DriverHanyuan1）、
量旋科技双子座核磁驱动（DriverSpinQGemini）、等等。
这些驱动和驱动基类（DriverBase）关系如下：

.. plantuml:: ../../_static/design/module-design/driver-class-er.puml
   :caption: 驱动类关系图
   :alt: 驱动类关系图
   :width: 800
   :align: center

驱动初始化
-------------------------

.. code-block:: python

   class DriverManager(object):
       """Driver manager."""

       def load_drivers(self):
           """Scan and load drivers."""
           logger.info("Loading drivers ...")
           base_module_name = "qcos.drivers"
           ...

       def init_drivers(self):
           """初始化驱动."""
           for driver_name, driver in self.drivers.items():
               # 验证驱动内部配置的合法性
               success, err_msg = driver.validate_driver()
               if success:
                   # 初始化驱动
                   driver.init_driver()
               if not success:
                   logger.error(
                       f"Driver: {driver_name} is disabled. "
                       f"Error message: {err_msg}"
                   )
                   driver.enable = False
                   driver.set_device_status(Device.DEVICE_STATUS_OFFLINE)

量子计算机/测控驱动示例
-------------------------

.. code-block:: python

   class DriverDummy(DriverBase):
       """空载测试驱动.

       Dummy neutral-atom driver for test purpose
       """

       def __init__(self):
           super().__init__()
           self.version = "0.0.1"
           self.alias_name = "空载测试驱动(中性原子)"
           self.description = "空载测试驱动(中性原子)"
           self.enable_transpiler = True
           self.transpiler = Constant.TRANSPILER_CMSS
           self.tech_type = Constant.TECH_TYPE_NEUTRAL_ATOM
           self.supported_basis_gates = [
               Constant.SINGLE_QUBIT_GATE_X,
               Constant.SINGLE_QUBIT_GATE_Y,
           ]
           self.supported_transpilers = [Constant.TRANSPILER_CMSS]
           self.enable_circuit_aggregation = True
           self.default_results_type = self.DATA_TYPE_GATE_SEQUENCE
           self.results_fetch_mode = Constant.RESULTS_FETCH_MODE_SYNC
           self.max_qubits = 10
           # pylint: disable=duplicate-code
           self.extra_configs = {}
           self.driver_options_schema = {Optional("sleep"): int}

       def init_driver(self):
           """Init driver."""
           # pylint: disable=duplicate-code
           self.set_device_status(Device.DEVICE_STATUS_ONLINE)

       def validate_driver_configs(self, configs):
           """Validate driver configs.

           Args:
               configs: configs dictionary

           Returns:
               success, err_msgs
           """
           success = True
           err_msg = None

           # check and load driver configs
           driver_config_schema = {
               Optional("ip_address"): str,
               Optional("port"): int,
               "transpiler": {
                   "qpu_configs": {
                       "qubits": int,
                       "storage_area": [str],
                       "operate_area": [str],
                       "coupler_map": {str: [str]},
                       "readout_error": {str: Or(float, int)},
                       Optional("coupler_error"): {str: Or(float, int)},
                       Optional("closest"): {str: str},
                   },
                   "decomposition_rule": {
                       str: {"gates": [list], Optional("params"): [str]}
                   },
               },
           }
           _success, err_msgs = Library.validate_schema(
               configs, driver_config_schema
           )
           if not _success:
               _err_msg = "\n".join(err_msgs)
               err_msg = f"device config file error: {_err_msg}"
               success = False
           else:
               # copy configs to self.qpu_configs
               self.qpu_configs = copy.deepcopy(configs.get("qpu_configs", {}))
               # copy configs to self.decomposition_rule
               self.decomposition_rule = copy.deepcopy(
                   configs.get("decomposition_rule", {})
               )
           return success, err_msg

       def close_driver(self):
           """Close driver."""

       def fetch_configs(self):
           """Fetch configs.

           Returns:
               remote transpiler configs
           """

       def run(self, job_id, num_qubits, data, data_type, shots=1):
           """Run job.

           Args:
               job_id: job ID
               num_qubits: number of qubits
               data: data
               data_type: data type
               shots: shots (Default value = 1)
           """
           # pylint: disable=duplicate-code
           data_index = data["index"]
           logger.info(
               f"job_id: {job_id}, shots: {shots}, num_qubits: {num_qubits}, "
               f"data_type: {data_type}, data: {data}"
           )

           self.set_progress_by_task(self.TASK_STAGE_START)
           self.set_device_status(Device.DEVICE_STATUS_BUSY)

           # handle extra_configs
           sleep = self.driver_options.get("sleep", None)
           if sleep:
               self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
               sleep_count = 1
               while sleep_count <= sleep:
                   logger.info(f"sleep: {sleep_count} / {sleep}")
                   time.sleep(1)
                   sleep_count += 1

           # dummy driver results
           result = self.get_fake_results(num_qubits, shots, data)
           self.set_results(job_id, data_index, results=result)
           self.set_device_status(Device.DEVICE_STATUS_ONLINE)
           self.set_progress_by_task(self.TASK_STAGE_COMPLETE)

       def cancel(self, job_id):
           """Cancel running job in driver.

           Driver should clean up any resources of the job

           Args:
               job_id: job ID
           """
           logger.info(f"Cancel job: job_id: {job_id}")
