# <center>量子计算操作系统QCOS安装部署及使用说明</center>

## 1. 编译、安装和运行 (推荐, 基于容器)
### 1.1 前提条件
* 保证操作系统已安装了docker、docker-compose等组件
```shell
# BCLinux/CentOS/OpenEuler环境下示例:
yum install -y docker docker-compose rsync
```

### 1.2 编辑.env配置文件
```shell
cd build-scripts
cp ./env.template .env
vim .env
# .env配置文件说明
# 1. DEV选项为False时表示编译出的镜像是生产环境镜像; True时表示编译出来的是开发环境镜像。开发环境会挂载(mount)宿主机源代码到容器中, 直接使用挂载的源代码运行, 方便开发者在宿主机上修改代码。而生产环境镜像中会集成源代码。
# 2. 需要填写PREFECT_SERVER_API_HOST地址(一般填写为本机IP地址或者127.0.0.1)
# 3. 如果本地可以访问外网, 无需填写YUM_MIRROR, PIP_MIRROR
# 4. 如果本地无法访问外网, 需要保证局域网内有OpenEuler操作系统的YUM镜像源(YUM_MIRROR), 以及Python软件包镜像源(PIP_MIRROR)。
# YUM_MIRROR地址格式示例: http://mirrors.cmecloud.cn
# PIP_MIRROR地址格式示例: http://mirrors.cmecloud.cn/pip/simple
# 5. DEBUG是内部开发使用的调试开关, 可以配成默认的False
# 6. LOCAL_CICD是本地CICD的标记开关, 可以配成默认的False
# 7. REGISTRY为Docker容器私有镜像仓库地址, 如果本机可以访问DockerHub, 则可以留空
```

### 1.3 编译qcos容器镜像
```shell
# 操作系统镜像 (容器内包含命令行)
./build-images.sh

# 独立的命令行镜像 [可选]
./build-sandbox.sh  # 编译qcos-cli wheel包用的容器环境
./run-sandbox.sh  # 运行sandbox容器环境
./build-images.sh --cli
```

### 1.4 修改配置文件
#### 1.4.1 创建和修改全局配置文件
参照代码库中etc/qcos/qcos.toml, 创建和修改全局配置文件/etc/qcos/qcos.toml
修改或添加DEVICE_LIST中的设备列表
<b>注意:</b> 如果不创建该文件, 容器模式下会自动创建

#### 1.4.2 创建和修改设备配置文件
参照代码库中etc/qcos/conf.d/dummy.toml等, 创建和修改设备配置文件/etc/qcos/conf.d/dummy.toml等
<b>注意:</b> 设备配置文件必须位于/etc/qcos/conf.d下, 文件名需要和qcos.toml中DEVICE_LIST列出的设备名一致。 文件中section必须对应相关设备名, 比如dummy设备的配置需要放在section: [dummy]下

### 1.5 运行容器
```shell
cd build-scripts
# 基于docker容器运行
./run-docker.sh

# 或者, 基于K8s pod运行:
./run-k8s-pods.sh
```

## 2. 编译、安装和运行 (可选, 非容器, 编译wheel包)
### 2.1 前提条件
* 保证操作系统已安装了python3-pip组件
```shell
# BCLinux/CentOS/OpenEuler环境下示例:
yum install -y python3 python3-pip python3-sphinx python3-requests
pip3 install -r ./requirements.txt -r ./test-requirements.txt
```

### 2.2 编译
#### 2.2.1 基于poetry编译操作系统wheel包
```shell
# BCLinux/CentOS/OpenEuler环境下示例:
cd build-scripts
./build-wheel.sh
或者
poetry build
```

### 2.3 安装
```shell
pip3 install ./dist/qcos-1.0.0-py3-none-any.whl
```

### 2.4 修改配置文件
#### 2.4.1 创建和修改全局配置文件
参照代码库中etc/qcos/qcos.toml, 创建和修改全局配置文件/etc/qcos/qcos.toml
修改或添加DEVICE_LIST中的设备列表
<b>注意:</b> 如果不创建该文件, 容器模式下会自动创建

#### 1.4.2 创建和修改设备配置文件
参照代码库中etc/qcos/conf.d/dummy.toml等, 创建和修改设备配置文件/etc/qcos/conf.d/dummy.toml等
<b>注意:</b> 设备配置文件必须位于/etc/qcos/conf.d下, 文件名需要和qcos.toml中DEVICE_LIST列出的设备名一致。 文件中section必须对应相关设备名, 比如dummy设备的配置需要放在section: [dummy]下

### 2.5 运行
```shell
# 保证prefect服务已启动
# 服务端:
qcos-api --config-file /etc/qcos/qcos.toml --config-dir /etc/qcos/conf.d/
```

## 3. 测试 (单元测试UT, 覆盖率测试Coverage, 系统测试ST, 代码格式检查)
### 3.1 通过容器环境运行测试
#### 3.1.1 单元测试 (UT)
```shell
cd ./cicd
./run-tests.sh -u
```

#### 3.1.2 覆盖率测试 (Coverage)
```shell
cd ./cicd
./run-tests.sh -c
```

#### 3.1.3 覆盖率报告查看
```shell
cd ./cicd
./run-tests.sh -s
# 使用浏览器打开./coverage_html/index.html查看覆盖率

# 或者, 在命令行模式下, 通过命令方式查看覆盖率报告 [可选]
coverage3 report -m
# 或者, 在命令行模式下, 通过link工具查看覆盖率HTML报告 [可选]
links ./coverage_html/index.html
```

#### 3.1.4 系统测试 (ST)
```shell
# 保证QCOS已经正常启动
# 编辑/etc/qcos/qcos-st.toml, 修改API_SERVER_IP和API_SERVER_PORT为被测服务的IP地址以及端口号
cd ./cicd
./run-tests.sh -s
```

#### 3.1.5 代码格式检查 (ruff format)
```shell
项目根目录下:
  ruff format --check qcos
或者:
  ./cicd/code-formatter.sh

自动修复代码格式:
  ruff format qcos
或者:
  ./cicd/code-formatter.sh -f
```

#### 3.1.6 代码静态分析lint (pylint+ruff+mypy)
```shell
项目根目录下:
  pylint qcos
  ruff check qcos
  mypy qcos
或者:
  ./cicd/code-linter.sh
```

## 4. 文档
### 4.1 编译Sphinx文档和OpenAPI文档
```shell
cd build-scripts
./build-docs.sh
```

## 5. 安全加固
### 5.1 自定义驱动配置文件中的账户密码加密
1. 如果驱动配置文件中需要配置密码, 用于和远程量子设备API进行认证, 可以选择使用加密后的密码 (也可以直接用明文密码)
```shell
进入qcos容器
$ docker exec -it qcos bash
cd bin
./encrypt-password.py -e my_password
Original text : my_password
Encrypted text: ++gAAAAABo9gU4yf6G9lQQoNpH1LkBSYDsRYs1qNBln_Sf2N5OQP2siY65uaLCoz8-NYFWCfHDj8pCyxHSs4ltSKsdv-yz9muSAQ==

把加密后的密码填入配置文件中, 比如:
vim /etc/qcos/conf.d/dummy.toml
[dummy]
alias_name = "空载测试设备"
driver = "DriverDummy"
password = "++gAAAAABo9gU4yf6G9lQQoNpH1LkBSYDsRYs1qNBln_Sf2N5OQP2siY65uaLCoz8-NYFWCfHDj8pCyxHSs4ltSKsdv-yz9muSAQ=="
```
2. QCOS日志中对驱动配置文件中的密码进行屏蔽
只需要定义驱动配置文件中密码字段时, 使用包含password字符串的字段即可, 该密码字段会在日志打印时自动被屏蔽, 替换成********。
比如: password, user_password, my_password, my_password_1等等

### 5.2 使用HTTPS加密的API连接
1. 生成自签名证书 (如果已经有证书可以跳过)
```shell
进入qcos容器
$ docker exec -it qcos bash
cd bin
./make-ssl-cert.py --ip-list 127.0.0.1 --dns-list localhost
```
输出的SSL密钥和证书文件默认位于: /etc/qcos/ssl/

2. 修改QCOS的配置文件, 使能SSL, 并且配置证书
```shell
vim /etc/qcos/qcos.toml
[SSL]
# Enable HTTPS for API server
USE_SSL = true

# SSL CERT_FILE
# eg. CERT_FILE = "/etc/qcos/ssl/ssl.crt"
CERT_FILE = "/etc/qcos/ssl/ssl.crt"

# SSL KEY_FILE
# eg. KEY_FILE = "/etc/qcos/ssl/ssl.key"
KEY_FILE = "/etc/qcos/ssl/ssl.key"

# SSL CA_FILE (Optional)
# eg. CA_FILE = "/etc/qcos/ssl/cacert.pem"
CA_FILE = "/etc/qcos/ssl/cacert.pem"
```

3. 重启QCOS服务
```shell
$ docker restart qcos
```

4. 命令行使用SSL证书
```shell
使用环境变量:
export USE_SSL=true
export SSL_CERTFILE=/etc/qcos/ssl/ssl.crt
export SSL_KEYFILE=/etc/qcos/ssl/ssl.key
export SSL_CAFILE=/etc/qcos/ssl/cacert.pem

qcos-cli version
或者, 使用命令行参数:
qcos-cli --use-ssl --ssl-certfile /etc/qcos/ssl/ssl.crt --ssl-keyfile /etc/qcos/ssl/ssl.key --ssl-cafile /etc/qcos/ssl/cacert.pem version
```

## 6. 命令行示例
```shell
[作业命令]
* 提交作业
1. 测试用dummy驱动
qcos-cli submit-job --code-type qasm --shots 10 --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm
1.1 使用profiling进行模块性能测量
qcos-cli submit-job --code-type qasm --shots 10 --profiling scheduling driver:parse driver:transpile driver:run --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm
1.2 使用callbacks进行回调
qcos-cli submit-job --code-type qasm --shots 10 --callbacks '[{"name":"callback","type":"results","method":"post","timeout":4,"retries":3,"headers":{"Content-Type": "application/json","user_id":"qcos"},"url":"http://127.0.0.1:8088/v1/job/set_job_results"}]' --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm
1.3 指定job-id
qcos-cli submit-job --job-id 00000000-0000-4000-8000-000000000001 --code-type qasm --shots 10 --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm
1.4 指定job名称
qcos-cli submit-job --job-name test-dummy --code-type qasm --shots 10 --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm
1.5 单作业多代码执行 (线路串行模式)
qcos-cli submit-job --code-type qasm --shots 10 --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm ./samples/qasm/2.0/simple-qasm.qasm
1.6 多作业并行执行 (线路聚合模式)
qcos-cli submit-job --code-type qasm --shots 10 --circuit-aggregation internal --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm ./samples/qasm/2.0/simple-qasm.qasm
qcos-cli submit-job --code-type qasm --shots 10 --circuit-aggregation external --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm

2. 中科酷原-汉原1 中性原子驱动, 模拟运行(dry-run)
qcos-cli submit-job --code-type qasm --shots 10 --dry-run --backend hanyuan1 -f ./samples/qasm/2.0/simple-qasm-1-bit.qasm
3. 中科酷原-汉原1 中性原子驱动, 真实运行
qcos-cli submit-job --code-type qasm --shots 10 --backend hanyuan1 -f ./samples/qasm/2.0/simple-qasm-1-bit.qasm
4. 玻色量子-光量子伊辛机, 真实运行
qcos-cli submit-job --code-type qubo --backend tiangong100 -f ./samples/qubo/simple-qubo.json
qcos-cli submit-job --code-type qubo --backend tiangong100 -f ./samples/qubo/simple-qubo.csv
qcos-cli submit-job --code-type qubo --backend tiangong1000 -f ./samples/qubo/simple-qubo.json
qcos-cli submit-job --code-type qubo --backend tiangong1000 -f ./samples/qubo/simple-qubo.csv
5. 量旋科技, 真实运行
qcos-cli submit-job --code-type qasm --shots 10 --backend sping_rpc -f ./samples/qasm/2.0/simple-qasm.qasm

* 获取作业状态
qcos-cli get-job-status 00000000-0000-4000-8000-000000000001

* 获取作业结果
qcos-cli get-job-results 00000000-0000-4000-8000-000000000001

* 获取所有作业列表
qcos-cli list-jobs

* 取消作业
qcos-cli cancel-jobs 00000000-0000-4000-8000-000000000001
qcos-cli cancel-jobs -y all

* 删除作业
qcos-cli delete-jobs 00000000-0000-4000-8000-000000000001
qcos-cli delete-jobs 00000000-0000-4000-8000-000000000001,00000000-0000-4000-8000-000000000002
qcos-cli delete-jobs -y all

* 设置作业结果 (回调或者测试用途)
qcos-cli set-job-results 00000000-0000-4000-8000-000000000001 --results '{"results": {"01":100}, "num_qubits": 2}'
** 设置多作业结果, 针对多源代码的作业
qcos-cli set-job-results 00000000-0000-4000-8000-000000000001 --results '{"results": {"01":100}, "num_qubits": 2}' '{"code": -104, "message": "error test"}'

[版本命令]
* 请求服务端版本请求命令
qcos-cli version

[系统命令]
* ping命令
qcos-cli ping 123

* 获取系统信息
qcos-cli system-info

[驱动命令]
* 获取所有驱动信息列表
qcos-cli list-drivers

* 获取驱动信息详情
qcos-cli get-driver DriverDummy

[设备命令]
* 获取所有设备信息列表
qcos-cli list-devices

* 获取设备信息详情
qcos-cli get-device dummy
```
