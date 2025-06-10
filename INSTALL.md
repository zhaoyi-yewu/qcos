# <center>量子操作系统QCOS</center>

## 1. 编译
### 1.1 前提条件
#### 1.1.1 手动载入基础容器镜像BCLinux 21.10U4
```shell
docker load -i ./bc-oe-amd64-21.10.tar.xz
```
#### 1.1.2 编辑.env配置文件
```shell
cd build
cp ./env.template .env
vim .env
```

### 1.2 编译qcos容器镜像
```shell
./build-docker.sh
```

## 2. 安装和运行
### 2.1 安装和部署
```shell
cd build
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
```
