# <center>量子计算操作系统QCOS webui安装部署及使用说明</center>

## 1. 编译、安装和运行 (基于容器)
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

### 1.4 修改配置文件
修改后端url:
./webui/src/config.js
const backendBaseUrl = 'http://100.78.61.23:18400'

修改该jest配置:
./webui/jest.config.js
testURL: 'http://100.78.61.23/'

### 1.5 运行容器
```shell
cd build-scripts
./run-docker-webui.sh
```
访问: http://{QCOS_WEBUI_IP}:18401

## 2. 编译、安装和运行 (调试模式)
```shell
npm run dev
```
