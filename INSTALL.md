# <center>量子计算操作系统QCOS安装部署及使用说明</center>

## 1. 编译
### 1.1 前提条件
* 保证操作系统已安装了docker、docker-compose组件
```shell
BCLinux/CentOS/OpenEuler环境下示例:
yum install -y docker docker-compose
```

### 1.2 编辑.env配置文件
```shell
cd build-scripts
cp ./env.template .env
vim .env
```

### 1.3 编译qcos容器镜像
```shell
./build-docker.sh
```

## 2. 安装和运行
### 2.1 修改配置文件
### 2.1.1 创建和修改全局配置文件
参照/etc/qcos/qcos.conf, 创建和修改全局配置文件/etc/qcos/qcos.conf
<b>注意:</b> 如果不创建该文件, 容器模式下会自动创建

### 2.1.2 创建和修改驱动配置文件
参照/etc/qcos/conf.d/dummy.conf, 创建和修改驱动配置文件/etc/qcos/conf.d/dummy.conf
<b>注意:</b> 驱动配置文件必须位于/etc/qcos/conf.d下, 文件名可以自己命名, 文件中每个驱动的配置必须对应的section中, 比如dummy驱动的配置需要放在[DriverDummy]下, DriverDummy为dummy驱动的类名

### 2.2 安装和部署
```shell
cd build-scripts
./run-docker.sh
```

## 3. 测试 (单元测试, 覆盖率测试, 代码格式检查)
### 3.1 通过容器环境运行测试
### 3.1.1 单元测试
```shell
./run-tests.sh -u
```

### 3.1.2 覆盖率测试
```shell
./run-tests.sh -c
```

### 3.1.3 覆盖率报告查看
```shell
# 命令行查看覆盖率报告
coverage3 report -m
# 生成覆盖率HTML报告
coverage3 html --title="QCOS Coverage Report" --include='src/*' -d coverage_html
# 查看覆盖率HTML报告
links ./coverage_html/index.html
```

### 3.1.4 代码格式检查 (flake8)
```shell
./run-tests.sh -p
```

## 4. 命令行
```shell
[作业命令]
* 提交作业
1. 测试用dummy驱动
qcos-cli submit-job --code-type qasm2 --shots 10 --backend DriverDummy '"OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncreg c[2];\nx q[0];\nx q[1];\nmeasure q -> c;\n"'
2. 中科酷原-汉原1 中性原子驱动, 模拟运行(dry-run)
qcos-cli submit-job --code-type qasm2 --shots 10 --dry-run --backend DriverHanyuan1 '"OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncreg c[2];\nx q[0];\nx q[1];\nmeasure q -> c;\n"'
3. 中科酷原-汉原1 中性原子驱动, 真实运行
qcos-cli submit-job --code-type qasm2 --shots 10 --backend DriverHanyuan1 '"OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncreg c[2];\nx q[0];\nx q[1];\nmeasure q -> c;\n"'
4. 玻色量子-光量子伊辛机, 真实运行
qcos-cli submit-job --code-type qubo --backend DriverTiangong100 '"[[-12,8,0,0,0,0,0,0,0,0,8,0,0,0,0,0,0,0,0,8],[0,-12,8,0,0,0,0,0,0,0,0,8,0,0,0,0,0,0,0,0],[0,0,-12,8,0,0,0,0,0,0,0,0,8,0,0,0,0,0,0,0],[0,0,0,-12,8,0,0,0,0,0,0,0,0,8,0,0,0,0,0,0],[0,0,0,0,-12,8,0,0,0,0,0,0,0,0,8,0,0,0,0,0],[0,0,0,0,0,-12,8,0,0,0,0,0,0,0,0,8,0,0,0,0],[0,0,0,0,0,0,-12,8,0,0,0,0,0,0,0,0,8,0,0,0],[0,0,0,0,0,0,0,-12,8,0,0,0,0,0,0,0,0,8,0,0],[0,0,0,0,0,0,0,0,-12,8,0,0,0,0,0,0,0,0,8,0],[0,0,0,0,0,0,0,0,0,-12,8,0,0,0,0,0,0,0,0,8],[0,0,0,0,0,0,0,0,0,0,-12,8,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0,0,-12,8,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0,0,0,-12,8,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0,0,0,0,-12,8,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0,0,0,0,0,-12,8,0,0,0,0],[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-12,8,0,0,0],[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-12,8,0,0],[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-12,8,0],[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-12,8],[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-12]]"'

* 获取作业状态
qcos-cli get-job-status 00000000-0000-4000-8000-000000000001

* 获取作业结果
qcos-cli get-job-results 00000000-0000-4000-8000-000000000001

* 获取所有作业列表
qcos-cli get-jobs

* 取消作业
qcos-cli cancel-jobs 00000000-0000-4000-8000-000000000001
qcos-cli cancel-jobs all

* 删除作业
qcos-cli delete-jobs 00000000-0000-4000-8000-000000000001
qcos-cli delete-jobs all
```
