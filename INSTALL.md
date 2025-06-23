# <center>量子操作系统QCOS</center>

## 1. 编译
### 1.1 前提条件
#### 1.1.1 手动载入基础容器镜像BCLinux 21.10U4
```shell
docker load -i ./bc-oe-amd64-21.10.tar.xz
```
#### 1.1.2 编辑.env配置文件
```shell
cd build-scripts
cp ./env.template .env
vim .env
```

### 1.2 编译qcos容器镜像
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
qcos-cli submit-job --shots 10 --qubits 2 '["OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncreg c[2];\nx q[0];\nx q[1];\nmeasure q -> c;\n"]'

* 获取作业状态
qcos-cli get-job-status 00000000-0000-4000-8000-000000000001

* 获取作业结果
qcos-cli get-job-results 00000000-0000-4000-8000-000000000001

* 获取所有作业列表
qcos-cli get-jobs

* 取消作业
qcos-cli cancel-jobs 00000000-0000-4000-8000-000000000001

* 删除作业
qcos-cli delete-jobs 00000000-0000-4000-8000-000000000001
```
