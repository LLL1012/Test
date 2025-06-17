from flask import Flask, request, jsonify
import paramiko
import logging
from flask_cors import CORS  # 导入 CORS 库

app = Flask(__name__)
CORS(app)  # 允许所有来源的跨域请求

# 设置日志
logging.basicConfig(level=logging.INFO)

# SSH 配置信息
HOST = "47.86.8.69"
USER = "root"
PASSWORD = "1234Qwer."
PORT = 22


# 登录验证用的默认用户名和密码
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '123456'

# 登录请求处理
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()  # 获取 JSON 数据
    username = data.get("username")
    password = data.get("password")

    # 验证用户名和密码
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return jsonify({"message": "登录成功"}), 200
    else:
        return jsonify({"message": "用户名或密码错误"}), 401


# 创建 SSH 会话
def create_ssh_session():
    try:
        transport = paramiko.Transport((HOST, PORT))
        transport.connect(username=USER, password=PASSWORD)
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client._transport = transport
        return ssh_client
    except Exception as e:
        logging.error(f"创建 SSH 会话失败: {e}")
        raise


# 执行命令
def execute_command(ssh_client, command):
    try:
        stdin, stdout, stderr = ssh_client.exec_command(command)
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        if error:
            logging.error(f"命令执行失败: {error}")
        return output
    except Exception as e:
        logging.error(f"执行命令失败: {e}")
        raise


# 查询主机列表
@app.route("/api/hosts", methods=["GET"])
def get_host_status():
    logging.info("开始获取主机状态...")
    host_statuses = []

    try:
        ssh_client = create_ssh_session()
        output = execute_command(ssh_client, "ansible ansible-nodes -m ping")

        for line in output.split("\n"):
            if "| SUCCESS" in line:
                parts = line.split(" ")
                host_name = parts[0].strip()
                # 如果主机成功连接，返回 SUCCESS
                host_statuses.append({"name": host_name, "status": "SUCCESS"})
            elif "| UNREACHABLE" in line:
                parts = line.split(" ")
                host_name = parts[0].strip()
                # 如果主机不可达，返回 UNREACHABLE
                host_statuses.append({"name": host_name, "status": "UNREACHABLE"})
    except Exception as e:
        logging.error("获取主机状态失败", exc_info=True)

    logging.info(f"返回的数据为: {host_statuses}")
    return jsonify(host_statuses)


# 添加新主机
@app.route("/api/hosts", methods=["POST"])
def add_host():
    data = request.get_json()
    host_name = data.get("name")
    port = data.get("port")
    logging.info(f"开始添加主机: {host_name}, port: {port}")

    try:
        ssh_client = create_ssh_session()

        # 1. 启动 Docker 容器
        docker_command = f"docker run -d --name {host_name} -p {port}:22 ansible-node"
        execute_command(ssh_client, docker_command)

        # 2. 添加到 ansible hosts 文件
        host_entry = f"echo '{host_name} ansible_ssh_port={port} ansible_ssh_user=ansible ansible_ssh_pass=ansible' >> /etc/ansible/hosts"
        execute_command(ssh_client, host_entry)

        return "success"
    except Exception as e:
        logging.error("添加主机失败", exc_info=True)
        return f"error: {str(e)}", 500


# 删除主机
@app.route("/api/hosts/<string:name>", methods=["DELETE"])
def delete_host(name):
    logging.info(f"开始删除主机: {name}")
    try:
        ssh_client = create_ssh_session()

        # 1. 停止并删除 Docker 容器
        execute_command(ssh_client, f"docker stop {name}")
        execute_command(ssh_client, f"docker rm {name}")

        # 2. 从 ansible hosts 文件中删除
        sed_command = f"sed -i '/{name}/d' /etc/ansible/hosts"
        execute_command(ssh_client, sed_command)

        return "success"
    except Exception as e:
        logging.error("删除主机失败", exc_info=True)
        return f"error: {str(e)}", 500


# 修改主机信息
@app.route("/api/hosts/<string:old_name>", methods=["PUT"])
def update_host(old_name):
    data = request.get_json()
    new_name = data.get("name")
    port = data.get("port")
    logging.info(f"开始更新主机信息: {old_name} -> {new_name}, port: {port}")

    try:
        ssh_client = create_ssh_session()

        # 从 ansible hosts 文件中更新
        sed_command = f"sed -i 's/{old_name} ansible_ssh_port=.*/{new_name} ansible_ssh_port={port} ansible_ssh_user=ansible ansible_ssh_pass=ansible/' /etc/ansible/hosts"
        execute_command(ssh_client, sed_command)

        return "success"
    except Exception as e:
        logging.error("更新主机失败", exc_info=True)
        return f"error: {str(e)}", 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
